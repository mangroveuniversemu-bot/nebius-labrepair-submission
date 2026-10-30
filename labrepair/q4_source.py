"""Load exact reviewed fixture bytes without importing or executing source code.

AST extraction is limited to pinned constants. This is not a Python evaluator,
model-code runner, sandbox, authenticated attestation or latest-version claim.
"""

import ast
import json
from dataclasses import dataclass
from pathlib import Path

from labrepair.candidate_review import FrozenContract, canonical_digest, digest
from labrepair.paths import ROOT
from labrepair.q4_pins import (
    ARCHIVE_SHA256,
    PINNED_FILES,
    POLICY_SHA256,
    WORKSPACE_MANIFEST_SHA256,
)

SOURCE_ROOT = ROOT / "vendor/q4-coding"
ALLOWED_PATHS = ("cases.json", "ledger.py", "runner.py")


class SourceUnavailable(ValueError):
    """No trusted contract may be returned after a source integrity failure."""


def verify_import(source_root: Path = SOURCE_ROOT) -> dict[str, bytes]:
    data = {}
    root = source_root.resolve()
    for name, expected in PINNED_FILES.items():
        path = source_root / name
        if any(parent.is_symlink() for parent in (path, *path.parents)):
            raise SourceUnavailable("SOURCE_SYMLINK_FORBIDDEN")
        if not path.resolve().is_relative_to(root):
            raise SourceUnavailable("SOURCE_PATH_OUTSIDE_IMPORT")
        try:
            if path.stat().st_size > 64 * 1024:
                raise SourceUnavailable("SOURCE_FILE_TOO_LARGE")
            value = path.read_bytes()
        except OSError as exc:
            raise SourceUnavailable("SOURCE_FILE_UNAVAILABLE") from exc
        if digest(value) != expected:
            raise SourceUnavailable("SOURCE_FILE_DIGEST_MISMATCH")
        data[name] = value
    return data


def _constant(node: ast.AST, names: dict):
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, (ast.List, ast.Tuple)):
        values = [_constant(item, names) for item in node.elts]
        return tuple(values) if isinstance(node, ast.Tuple) else values
    if isinstance(node, ast.Dict):
        return {
            _constant(key, names): _constant(value, names)
            for key, value in zip(node.keys, node.values)
        }
    if isinstance(node, ast.Name) and node.id in names:
        return names[node.id]
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        value = _constant(node.operand, names)
        if type(value) in (int, float):
            return -value
    if (
        isinstance(node, ast.BinOp)
        and isinstance(node.op, ast.Pow)
        and isinstance(node.left, ast.Constant)
        and isinstance(node.right, ast.Constant)
        and node.left.value == 10
        and node.right.value == 18
    ):
        return 10**18  # The one reviewed large-integer fixture literal.
    if (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "list"
        and len(node.args) == 1
        and not node.keywords
        and isinstance(node.args[0], ast.Name)
        and node.args[0].id in ("ALLOWED_PATHS", "REQUIRED_COMMAND")
    ):
        return list(names[node.args[0].id])
    raise SourceUnavailable("NON_LITERAL_SOURCE_CONSTANT")


def extract_constants(
    data: bytes, wanted: tuple[str, ...], known: dict | None = None
) -> dict:
    names = dict(known or {})
    found = set()
    for node in ast.parse(data).body:
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        target = node.targets[0]
        if isinstance(target, ast.Name) and target.id in wanted:
            if target.id in found:
                raise SourceUnavailable("DUPLICATE_SOURCE_CONSTANT")
            names[target.id] = _constant(node.value, names)
            found.add(target.id)
    if found != set(wanted):
        raise SourceUnavailable("MISSING_SOURCE_CONSTANT")
    return {name: names[name] for name in wanted}


@dataclass(frozen=True)
class LoadedSource:
    contract: FrozenContract
    workspace_manifest: dict
    suite_sha256: str
    correct_literal_fixture: str

    def provenance(self) -> dict:
        return {
            "source_import": "VERIFIED_PINNED_Q4_CODING_SNAPSHOT",
            "source_archive_sha256": ARCHIVE_SHA256,
            "latest_remote_match": "UNVERIFIED",
            "source_identity_authentication": "NOT_CLAIMED",
            "workspace_paths": list(ALLOWED_PATHS),
            "editable_paths": list(self.contract.editable_paths),
            "snapshot_sha256": self.contract.snapshot_sha256,
            "policy_sha256": self.contract.policy_sha256,
            "workspace_manifest_sha256": self.workspace_manifest["manifest_sha256"],
            "suite_sha256": self.suite_sha256,
            "loader_method": "AST_CONSTANTS_ONLY; no import, exec, source staging or network",
            "fixture_domain": "Q4_SYNTHETIC_INVOICE_ARITHMETIC; separate from Bell/CHSH",
        }


def load_source(source_root: Path = SOURCE_ROOT) -> LoadedSource:
    files = verify_import(source_root)
    patch = extract_constants(
        files["coding/patch_review.py"], ("BASELINE", "CORRECT", "CASES", "RUNNER")
    )
    sandbox = extract_constants(
        files["coding/sandbox_adapter.py"], ("REQUIRED_COMMAND", "CONTRACT_VERSION")
    )
    workspace = extract_constants(
        files["coding/workspace_contract.py"],
        ("MANIFEST_VERSION", "POLICY_VERSION", "ALLOWED_PATHS", "FROZEN_POLICY"),
        sandbox,
    )
    originals = (
        ("cases.json", json.dumps(patch["CASES"], sort_keys=True).encode()),
        ("ledger.py", patch["BASELINE"].encode()),
        ("runner.py", patch["RUNNER"].encode()),
    )
    policy_hash = canonical_digest(workspace["FROZEN_POLICY"])
    if workspace["ALLOWED_PATHS"] != ALLOWED_PATHS or policy_hash != POLICY_SHA256:
        raise SourceUnavailable("FROZEN_POLICY_CHANGED")
    unsigned = {
        "manifest_version": workspace["MANIFEST_VERSION"],
        "sandbox_contract_version": sandbox["CONTRACT_VERSION"],
        "policy_version": workspace["POLICY_VERSION"],
        "policy_sha256": policy_hash,
        "command": list(sandbox["REQUIRED_COMMAND"]),
        "files": [
            {
                "path": path,
                "size_bytes": len(value),
                "sha256": digest(value),
                "mode": "read_only",
            }
            for path, value in originals
        ],
        "staging_status": "PRE_STAGED_FIXTURE_ONLY",
        "live_validation": "NOT_RUN",
    }
    manifest_hash = canonical_digest(unsigned)
    if manifest_hash != WORKSPACE_MANIFEST_SHA256:
        raise SourceUnavailable("WORKSPACE_MANIFEST_CHANGED")
    contract = FrozenContract(originals, ("ledger.py",), policy_hash)
    return LoadedSource(
        contract,
        {**unsigned, "manifest_sha256": manifest_hash},
        digest((json.dumps(patch["CASES"], sort_keys=True) + patch["RUNNER"]).encode()),
        patch["CORRECT"],
    )
