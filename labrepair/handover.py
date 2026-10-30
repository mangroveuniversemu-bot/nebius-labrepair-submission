"""Portable offline replay data, never an executor or a provider transport.

The bundle contains text, not imported Python modules. Checksums detect changes,
not identity. Independent operator pins and fresh review decide every replay.
"""

import argparse
import json
from pathlib import Path

from labrepair.candidate_review import digest, unique_object
from labrepair.paths import ROOT
from labrepair.historical_bytes import pinned_historical_bytes
from labrepair.provider_envelope import (
    encoded,
    prepare_request,
    review_offline_response,
)
from labrepair.q4_source import SOURCE_ROOT, SourceUnavailable, load_source

MAX_BUNDLE_BYTES = 131072
MAX_MEMBER_BYTES = 32768
MAX_TOTAL_MEMBER_BYTES = 65536
ORIGIN_RUN = "20261003T185948Z-nebius-007"
ORIGIN_PINS = {
    "nebius_007_request_preview.json": "b62ca1ba11160e2b2aeedce424b2279ff6823fa998796279d5f1a6a1c37e08ff",
    "nebius_007_response_fixture.json": "5cf55644cb500df92582b20bfd28b3ffbca29d2f0c46e36bd12cb7b9cc01b5a7",
    "nebius_007_response_intake.json": "e963a8a609e086c79993c034f122a43a500eb92641bb15b816bd7cf0cc53bca5",
    "nebius_007_negative_fixture.json": "ca1a0b59a5d8e1f3c537b7693bd934d86337eee362f68fbfb1b899cc99382572",
    "nebius_007_negative_intake.json": "9390835927474a4550dc961e5d5484cdf616152bdb803dc6ee542f2560cb9e3c",
}
NEGATIVE_REVIEWED_BYTES_SHA256 = (
    "586f2554a2df20bbc3382afb99e675e27330eb4e1ed45a133e5f86f15cce2a64"
)
MEMBERS = frozenset(
    {
        "README.txt",
        "origin.json",
        "frozen/cases.json.txt",
        "frozen/ledger.py.txt",
        "frozen/runner.py.txt",
        "request.json",
        "responses/normal.json.txt",
        "responses/protected-change.json.txt",
        "receipts/normal.json",
        "receipts/protected-change.json",
    }
)
README = """NEBIUS-008 portable offline handover
All inputs are synthetic. This is data, not an executable repair package.

Use the reviewed Nebius workspace's Python environment, from its root:
python -m labrepair.handover --replay evidence/nebius_008_handover.json --output evidence/nebius_008_replay.json

Expected CLI exit: 0 means the offline replay matches, NOT repair approval.
Normal proposal: BLOCKED on missing verified isolation and spending limit.
Protected runner edit: REJECTED, PROTECTED_FILE_CHANGE.
NVIDIA/Nebius model, candidate execution, sandbox and actual usage: NOT_RUN/unknown.
No module in frozen/ or proposal text is executed or extracted to source paths.
No keys, account IDs, absolute user paths or scientific certificate are included.

The verifier uses its operator-reviewed Q4 source pins, never this manifest as
authorization. Rehashed forged verdicts, request changes and source edits fail.
Manifest SHA-256 detects changes, but is not an authenticated signature.
Use the full private Coding ZIP for the reviewed code, license and source pins.
This invoice fixture does not approve/repair the separate Bell/CHSH original.

NEBIUS-007's negative check reviewed canonical JSON bytes (838 bytes), whereas
its saved readable fixture was 925 bytes. Both hashes are disclosed in origin.
This bundle carries the actual canonical reviewed bytes; history is not edited.
"""


class HandoverInvalid(ValueError):
    """A fixed, non-sensitive failure code; never echo untrusted input text."""


def _constant(_value):
    raise HandoverInvalid("NON_JSON_NUMBER")


def parse(raw: bytes):
    try:
        return json.loads(
            raw, object_pairs_hook=unique_object, parse_constant=_constant
        )
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise HandoverInvalid("INVALID_BUNDLE_JSON") from exc


def origin() -> dict:
    return {
        "origin_run_id": ORIGIN_RUN,
        "origin_files_sha256": ORIGIN_PINS,
        "fixture_label": "ORIGINAL_REVIEWED_LITERAL; NOT_MODEL_GENERATED",
        "negative_serialization": {
            "saved_pretty_fixture_sha256": ORIGIN_PINS[
                "nebius_007_negative_fixture.json"
            ],
            "actual_reviewed_canonical_sha256": NEGATIVE_REVIEWED_BYTES_SHA256,
            "actual_reviewed_bytes": 838,
            "normalization": "json.loads then provider_envelope.encoded; receipt matches actual reviewed bytes",
        },
        "scientific_claim": "UNCHANGED_NOT_EVALUATED; separate Bell/CHSH original",
    }


def _read_bounded(path: Path, limit: int) -> bytes:
    if any(item.is_symlink() for item in (path, *path.parents)):
        raise HandoverInvalid("INPUT_SYMLINK_FORBIDDEN")
    with path.open("rb") as handle:
        data = handle.read(limit + 1)
    if len(data) > limit:
        raise HandoverInvalid("INPUT_TOO_LARGE")
    return data


def build_bundle(evidence_root: Path = ROOT / "evidence") -> bytes:
    """Export only pinned historical inputs; rerun review, not candidate code."""
    source = load_source()
    draft = prepare_request(_archived_replay=True)
    saved = {}
    for name, expected in ORIGIN_PINS.items():
        raw = _read_bounded(evidence_root / name, MAX_MEMBER_BYTES)
        try:
            raw = pinned_historical_bytes(raw, expected)
        except ValueError as exc:
            raise HandoverInvalid("ORIGIN_FILE_DIGEST_MISMATCH") from exc
        saved[name] = raw
    preview = parse(saved["nebius_007_request_preview.json"])
    expected_preview = {**draft.receipt(_archived_replay=True), "request_body": parse(draft.body)}
    if encoded(preview) != encoded(expected_preview):
        raise HandoverInvalid("ORIGIN_REQUEST_MISMATCH")
    negative_raw = encoded(parse(saved["nebius_007_negative_fixture.json"]))
    if digest(negative_raw) != NEGATIVE_REVIEWED_BYTES_SHA256:
        raise HandoverInvalid("ORIGIN_NEGATIVE_SERIALIZATION_MISMATCH")
    members = {
        "README.txt": README.encode(),
        "origin.json": encoded(origin()),
        "request.json": draft.body,
        "responses/normal.json.txt": saved["nebius_007_response_fixture.json"],
        "responses/protected-change.json.txt": negative_raw,
    }
    for case, raw, receipt_name in (
        (
            "normal",
            members["responses/normal.json.txt"],
            "nebius_007_response_intake.json",
        ),
        (
            "protected-change",
            negative_raw,
            "nebius_007_negative_intake.json",
        ),
    ):
        result = review_offline_response(raw, draft, _archived_replay=True)
        if encoded(result) != encoded(parse(saved[receipt_name])):
            raise HandoverInvalid("ORIGIN_RECEIPT_REPLAY_MISMATCH")
        members[f"receipts/{case}.json"] = encoded(result)
    members.update(
        {f"frozen/{name}.txt": data for name, data in source.contract.originals}
    )
    value = {
        "schema_version": 1,
        "kind": "PORTABLE_OFFLINE_HANDOVER_DATA",
        "manifest": {name: digest(data) for name, data in sorted(members.items())},
        "members": {
            name: data.decode("utf-8") for name, data in sorted(members.items())
        },
    }
    bundle = encoded(value)
    # Same verifier runs at export time. No manifest can invent authorization.
    replay_bundle(bundle)
    return bundle


def replay_bundle(raw: bytes, source_root: Path = SOURCE_ROOT) -> dict:
    """Recompute exactly two offline intakes, without extracting/executing data."""
    if len(raw) > MAX_BUNDLE_BYTES:
        raise HandoverInvalid("BUNDLE_TOO_LARGE")
    value = parse(raw)
    if (
        not isinstance(value, dict)
        or set(value) != {"schema_version", "kind", "manifest", "members"}
        or type(value["schema_version"]) is not int
        or value["schema_version"] != 1
        or value["kind"] != "PORTABLE_OFFLINE_HANDOVER_DATA"
    ):
        raise HandoverInvalid("INVALID_BUNDLE_SHAPE")
    manifest, text = value["manifest"], value["members"]
    if (
        not isinstance(manifest, dict)
        or not isinstance(text, dict)
        or set(manifest) != MEMBERS
        or set(text) != MEMBERS
    ):
        raise HandoverInvalid("UNEXPECTED_OR_MISSING_MEMBER")
    members = {}
    for name in sorted(MEMBERS):
        if not isinstance(text[name], str):
            raise HandoverInvalid("INVALID_MEMBER_TEXT")
        try:
            data = text[name].encode("utf-8")
        except UnicodeError as exc:
            raise HandoverInvalid("INVALID_MEMBER_ENCODING") from exc
        if len(data) > MAX_MEMBER_BYTES:
            raise HandoverInvalid("MEMBER_TOO_LARGE")
        if digest(data) != manifest[name]:
            raise HandoverInvalid("MEMBER_DIGEST_MISMATCH")
        members[name] = data
    if sum(map(len, members.values())) > MAX_TOTAL_MEMBER_BYTES:
        raise HandoverInvalid("TOTAL_MEMBER_BYTES_EXCEEDED")
    source = load_source(source_root)
    draft = prepare_request(source_root=source_root, _archived_replay=True)
    if members["README.txt"] != README.encode() or members["origin.json"] != encoded(
        origin()
    ):
        raise HandoverInvalid("ORIGIN_OR_INSTRUCTIONS_CHANGED")
    if members["request.json"] != draft.body:
        raise HandoverInvalid("REQUEST_BINDING_MISMATCH")
    for name, data in source.contract.originals:
        if members[f"frozen/{name}.txt"] != data:
            raise HandoverInvalid("FROZEN_SOURCE_MISMATCH")
    actual = {}
    for case, input_sha in (
        ("normal", ORIGIN_PINS["nebius_007_response_fixture.json"]),
        ("protected-change", NEGATIVE_REVIEWED_BYTES_SHA256),
    ):
        response = members[f"responses/{case}.json.txt"]
        if digest(response) != input_sha:
            raise HandoverInvalid("PINNED_RESPONSE_MISMATCH")
        result = review_offline_response(response, draft, source_root, _archived_replay=True)
        saved = parse(members[f"receipts/{case}.json"])
        if encoded(saved) != encoded(result):
            raise HandoverInvalid("SAVED_RECEIPT_REPLAY_MISMATCH")
        actual[case] = result
    return {
        "kind": "ACTUAL_LOCAL_OFFLINE_HANDOVER_REPLAY",
        "bundle_sha256": digest(raw),
        "bundle_bytes": len(raw),
        "member_count": len(members),
        "origin_run_id": ORIGIN_RUN,
        "verification": "MATCHED_OFFLINE_REPLAY; NOT_REPAIR_APPROVAL",
        "request_body_sha256": digest(draft.body),
        "source_bindings": source.provenance(),
        "cases": actual,
        "model": "NOT_RUN",
        "candidate_execution": "NOT_RUN",
        "actual_provider_usage": "unknown",
        "source_written": False,
        "network_requests": 0,
        "data_extracted_to_source_paths": False,
        "identity_authentication": "NOT_CLAIMED; checksums are not signatures",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--export", type=Path)
    mode.add_argument("--replay", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    evidence = (ROOT / "evidence").resolve()
    paths = [path for path in (args.export, args.replay, args.output) if path]
    if any(not path.resolve().is_relative_to(evidence) for path in paths):
        parser.error("all paths must remain in the workspace evidence folder")
    if args.replay and (
        not args.output or args.output.resolve() == args.replay.resolve()
    ):
        parser.error("replay requires a separate --output receipt")
    if args.export and args.output:
        parser.error("export writes only --export; use replay separately")
    # Fail rather than overwrite an existing history/receipt, including symlinks.
    target = args.export or args.output
    if target.exists() or target.is_symlink():
        parser.error("output already exists; preserve the original and use a new name")
    try:
        raw = (
            build_bundle()
            if args.export
            else _read_bounded(args.replay, MAX_BUNDLE_BYTES)
        )
        result = replay_bundle(raw)
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("xb") as handle:
            handle.write(raw if args.export else encoded(result) + b"\n")
        print(json.dumps({key: item for key, item in result.items() if key != "cases"}))
        return 0  # Only a matched OFFLINE replay; never provider/test approval.
    except (HandoverInvalid, SourceUnavailable) as exc:
        print(
            json.dumps(
                {"verification": "REJECTED", "reason": str(exc), "model": "NOT_RUN"}
            )
        )
    except OSError:
        print(
            json.dumps(
                {
                    "verification": "BLOCKED",
                    "reason": "FILE_UNAVAILABLE",
                    "model": "NOT_RUN",
                }
            )
        )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
