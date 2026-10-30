"""Review bounded patch proposals without executing, importing or applying them.

This is an independent intake gate, not the unavailable Q4 OpenShell adapter.
Trusted contracts must be constructed from verified source by the operator.
Provider-supplied test outcomes and readiness claims are never accepted.
"""

import argparse
import difflib
import hashlib
import json
import re
import time
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from labrepair.paths import ROOT

MAX_PROPOSAL_BYTES = 32768
MAX_REPLACEMENT_BYTES = 8192
SHA256 = re.compile(r"[0-9a-f]{64}\Z")


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_digest(value: dict) -> str:
    return digest(json.dumps(value, sort_keys=True, separators=(",", ":")).encode())


def safe_path(value: str) -> bool:
    if not isinstance(value, str) or not value or "\\" in value or ":" in value:
        return False
    path = PurePosixPath(value)
    return (
        not path.is_absolute()
        and path.as_posix() == value
        and all(part not in (".", "..") for part in path.parts)
        and not any(ord(character) < 32 for character in value)
        and all(part.rstrip(" .") == part for part in path.parts)
    )


def unique_object(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("duplicate_json_key")
        value[key] = item
    return value


@dataclass(frozen=True)
class FrozenContract:
    """An operator-owned snapshot; never deserialize it from the model proposal."""

    originals: tuple[tuple[str, bytes], ...]
    editable_paths: tuple[str, ...]
    policy_sha256: str

    def __post_init__(self):
        paths = [path for path, _ in self.originals]
        if (
            len(paths) != 3
            or len(set(paths)) != 3
            or len({path.casefold() for path in paths}) != 3
            or not all(safe_path(path) for path in paths)
            or not set(self.editable_paths).issubset(paths)
            or not SHA256.fullmatch(self.policy_sha256)
        ):
            raise ValueError("invalid_trusted_contract")

    @property
    def snapshot_sha256(self) -> str:
        return canonical_digest({path: digest(data) for path, data in self.originals})


@dataclass(frozen=True)
class OperatorGates:
    source_verified: bool = False
    isolated_backend_verified: bool = False
    spending_limit_verified: bool = False


def review_candidate(
    raw: bytes, contract: FrozenContract | None, gates: OperatorGates
) -> dict:
    """Return only intake status. READY never means tests passed or code accepted."""
    receipt = {
        "schema_version": 1,
        "proposal_sha256": digest(raw),
        "status": "REJECTED",
        "reasons": [],
        "changes": [],
        "execution": "NOT_RUN",
        "model": "NOT_RUN_BY_REVIEWER",
        "usage": "unknown",
        "scientific_claim": "UNCHANGED_NOT_EVALUATED_BY_THIS_GATE",
        "source_written": False,
        "network_requests": 0,
    }

    def reject(reason: str) -> dict:
        receipt["reasons"].append(reason)
        return receipt

    if len(raw) > MAX_PROPOSAL_BYTES:
        return reject("PROPOSAL_TOO_LARGE")
    try:
        proposal = json.loads(raw, object_pairs_hook=unique_object)
    except (UnicodeDecodeError, ValueError, RecursionError):
        return reject("INVALID_JSON")
    expected = {"snapshot_sha256", "policy_sha256", "replacements"}
    if not isinstance(proposal, dict) or set(proposal) != expected:
        return reject("UNEXPECTED_OR_MISSING_FIELDS")
    if contract is None or not gates.source_verified:
        receipt["status"] = "BLOCKED"
        return reject("VERIFIED_SOURCE_UNAVAILABLE")
    receipt["snapshot_sha256"] = contract.snapshot_sha256
    receipt["policy_sha256"] = contract.policy_sha256
    if proposal["snapshot_sha256"] != contract.snapshot_sha256:
        return reject("STALE_OR_WRONG_SOURCE")
    if proposal["policy_sha256"] != contract.policy_sha256:
        return reject("POLICY_BINDING_MISMATCH")
    replacements = proposal["replacements"]
    if not isinstance(replacements, list) or not 1 <= len(replacements) <= 3:
        return reject("INVALID_REPLACEMENT_COUNT")
    originals = dict(contract.originals)
    seen = set()
    staged_changes = []
    for replacement in replacements:
        if not isinstance(replacement, dict) or set(replacement) != {
            "path",
            "before_sha256",
            "after_utf8",
        }:
            return reject("INVALID_REPLACEMENT_FIELDS")
        path = replacement["path"]
        if not safe_path(path):
            return reject("UNSAFE_PATH")
        if path.casefold() in seen:
            return reject("DUPLICATE_PATH")
        seen.add(path.casefold())
        if path not in originals:
            return reject("OUTSIDE_FROZEN_WORKSPACE")
        if path not in contract.editable_paths:
            return reject("PROTECTED_FILE_CHANGE")
        original = originals[path]
        if replacement["before_sha256"] != digest(original):
            return reject("ORIGINAL_FILE_BINDING_MISMATCH")
        after_text = replacement["after_utf8"]
        if not isinstance(after_text, str) or "\x00" in after_text:
            return reject("INVALID_SOURCE_TEXT")
        try:
            after = after_text.encode("utf-8")
            before_text = original.decode("utf-8")
        except UnicodeError:
            return reject("INVALID_SOURCE_ENCODING")
        if len(after) > MAX_REPLACEMENT_BYTES:
            return reject("REPLACEMENT_TOO_LARGE")
        if after == original:
            return reject("NO_SOURCE_CHANGE")
        staged_changes.append(
            {
                "path": path,
                "before_sha256": digest(original),
                "after_sha256": digest(after),
                "diff": "".join(
                    difflib.unified_diff(
                        before_text.splitlines(keepends=True),
                        after_text.splitlines(keepends=True),
                        fromfile=f"original/{path}",
                        tofile=f"candidate/{path}",
                    )
                ),
            }
        )
    # No partial proposal is exposed as a valid review when any change failed.
    receipt["changes"] = staged_changes
    for verified, reason in (
        (gates.isolated_backend_verified, "ISOLATED_BACKEND_UNVERIFIED"),
        (gates.spending_limit_verified, "SPENDING_LIMIT_UNVERIFIED"),
    ):
        if not verified:
            receipt["reasons"].append(reason)
    receipt["status"] = "BLOCKED" if receipt["reasons"] else "READY_FOR_ISOLATED_TEST"
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--proposal", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--source",
        choices=("unavailable", "q4-pinned"),
        default="unavailable",
        help="Use only the operator-pinned Coding snapshot; never accept a model-owned manifest",
    )
    args = parser.parse_args()
    allowed_output = (ROOT / "evidence").resolve()
    proposal_path = args.proposal.resolve()
    output = args.output.resolve()
    if not proposal_path.is_relative_to(allowed_output) or not output.is_relative_to(
        allowed_output
    ):
        parser.error(
            "input and output must remain inside this workspace's evidence folder"
        )
    started = time.perf_counter()
    with proposal_path.open("rb") as source:
        raw = source.read(MAX_PROPOSAL_BYTES + 1)
    contract = None
    provenance = {"source_import": "Q4_NOT_IMPORTED"}
    source_error = None
    if args.source == "q4-pinned":
        from labrepair.q4_source import SourceUnavailable, load_source

        try:
            loaded = load_source()
            contract = loaded.contract
            provenance = loaded.provenance()
        except SourceUnavailable as exc:
            source_error = str(exc)
            provenance = {"source_import": "Q4_IMPORT_INTEGRITY_FAILED"}
    # CLI cannot enable dispatch. No proposal, flag, or provenance file can
    # claim isolation or a verified cost cap. Those integrations remain absent.
    receipt = review_candidate(
        raw, contract, OperatorGates(source_verified=contract is not None)
    )
    if source_error:
        receipt["source_error"] = source_error
    if len(raw) > MAX_PROPOSAL_BYTES:
        receipt["bounded_prefix_sha256"] = receipt["proposal_sha256"]
        receipt["proposal_sha256"] = None
        receipt["input_truncated"] = True
    receipt["local_review_elapsed_seconds"] = time.perf_counter() - started
    receipt.update(provenance)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(receipt))
    return 0 if receipt["status"] == "READY_FOR_ISOLATED_TEST" else 2


if __name__ == "__main__":
    raise SystemExit(main())
