"""Inspect the archived demo draft without inventing missing source evidence.

Reads only fixed repository artifacts and the optional historical archive. No
candidate execution, provider access, browser, packaging or submission occurs.
A matched draft is not a recorded video, a manual review, or contest readiness.
"""

import argparse
import errno
import hashlib
import json
import os
import re
import stat
import sys
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from labrepair.historical_bytes import pinned_historical_bytes

RUN_ID = "20261003T224642Z-nebius-010"
SOURCE_PACKAGE_SHA256 = (
    "e230e9ae7956abbc91446d43ad759ce14c689ae9ad4f8fffe2dd7e50a463c887"
)
PINS = {
    "ops/nebius_009_checkpoint_final.json": "4100b9fae7f6b5abef463f8c99f2f3de3aff49b1d205187b98c697d1df587d5b",
    "handover-workbench/index.html": "b8559425a7fd60516f4818aa5e7e966847e8d3331bcc778e2a3605c1f79cd319",
    "handover-workbench/qa/rejected.html": "f0dddc684ae1d7da06075d655bde856e0ce7fd6a0e01b5ac92c73b731b04adda",
    "handover-workbench/offline-handover.json": "2f6690b9b77430ebdd87eb08292241e5ba491f317e92c92616df498b617d30aa",
    "handover-workbench/fresh-replay.json": "3d294cb0b3b8b10b609ae96895797b402787f3a049398bcb3ec83c76d0469ce4",
    "handover-workbench/historical-domain.json": "3622d17249b54dc75f9dfaec0fe75c4e1c8d4c07e682ba1cbbddb36c75e97df1",
}
FACTS = {
    "normal": "BLOCKED",
    "protected_change": "REJECTED",
    "original_claim": "BLOCK",
    "claimed_s": 2.61,
    "replayed_s": 1.9625,
    "model": "NOT_RUN",
    "candidate_execution": "NOT_RUN",
    "sandbox": "NOT_RUN",
    "actual_provider_usage": "unknown",
}


class DemoInvalid(ValueError):
    """Fixed non-sensitive diagnostic; no untrusted prose echoed."""


def sha(data):
    return hashlib.sha256(data).hexdigest()


SCHEMA = "LABREPAIR_DEMO_EVIDENCE_GAP_V1"
MAX_FILE_BYTES = 131072
DRAFT_FILES = (
    "docs/nebius_demo_010.json",
    "docs/nebius_demo_010.srt",
    "docs/DEMO_SCRIPT_165S.md",
)


@contextmanager
def _directory(path):
    """Open every directory without following symlinks, including ancestors."""
    if not all(hasattr(os, name) for name in ("O_DIRECTORY", "O_NOFOLLOW", "O_NONBLOCK")):
        raise DemoInvalid("SAFE_FILE_ACCESS_UNAVAILABLE")
    if os.open not in os.supports_dir_fd:
        raise DemoInvalid("SAFE_FILE_ACCESS_UNAVAILABLE")
    absolute = path if path.is_absolute() else Path.cwd() / path
    if absolute.anchor != "/" or ".." in absolute.parts:
        raise DemoInvalid("UNSAFE_PATH")
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    descriptor = os.open("/", flags)
    try:
        for part in absolute.parts[1:]:
            child = os.open(part, flags, dir_fd=descriptor)
            os.close(descriptor)
            descriptor = child
        yield descriptor
    finally:
        os.close(descriptor)


def _read_fixed(path, limit):
    with _directory(path.parent) as parent:
        descriptor = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
                             dir_fd=parent)
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            os.close(descriptor)
            raise DemoInvalid("REGULAR_FILE_REQUIRED")
        with os.fdopen(descriptor, "rb") as stream:
            raw = stream.read(limit + 1)
    if len(raw) > limit:
        raise DemoInvalid("FILE_TOO_LARGE")
    return raw


def _strict_json(raw):
    def unique(pairs):
        value = {}
        for key, item in pairs:
            if key in value:
                raise DemoInvalid("INVALID_JSON")
            value[key] = item
        return value

    def constant(_value):
        raise DemoInvalid("INVALID_JSON")

    try:
        return json.loads(raw.decode("utf-8"), object_pairs_hook=unique, parse_constant=constant)
    except (ValueError, UnicodeError, RecursionError):
        raise DemoInvalid("INVALID_JSON") from None


def _inspect(path, expected=None, limit=MAX_FILE_BYTES, expected_size=None):
    """Return exact observed-byte metadata and verified representation only."""
    entry = {"expected_sha256": expected} if expected is not None else {}
    try:
        raw = _read_fixed(path, limit)
    except FileNotFoundError:
        return {**entry, "status": "MISSING"}, None
    except DemoInvalid as exc:
        return {**entry, "status": str(exc)}, None
    except OSError as exc:
        status = "UNSAFE_PATH" if exc.errno in (errno.ELOOP, errno.ENOTDIR) else "READ_UNAVAILABLE"
        return {**entry, "status": status}, None
    entry.update(observed_bytes=len(raw), observed_sha256=sha(raw))
    if expected_size is not None and len(raw) != expected_size:
        return {**entry, "status": "SIZE_MISMATCH"}, None
    if expected is None:
        return {**entry, "status": "READ_UNPINNED_METADATA_ONLY"}, raw
    try:
        historical = pinned_historical_bytes(raw, expected)
    except ValueError:
        return {**entry, "status": "DIGEST_MISMATCH"}, None
    entry.update(status="MATCHED", pinned_representation_sha256=sha(historical),
                 pinned_representation_bytes=len(historical),
                 representation="EXACT" if historical == raw else "LF_TO_HISTORICAL_CRLF")
    return entry, historical


def _facts_match(raw):
    """Compare only available, independently pinned static evidence bytes."""
    names = ("handover-workbench/fresh-replay.json", "handover-workbench/historical-domain.json")
    if any(name not in raw for name in names):
        return "BLOCKED_SOURCE_UNAVAILABLE"
    try:
        replay = _strict_json(raw[names[0]])
        science_cases = _strict_json(raw[names[1]])["cases"]
        science = [case for case in science_cases if case["case"] == "maya"]
        if len(science) != 1:
            return "PINNED_EVIDENCE_FACT_MISMATCH"
        science = science[0]
        matched = (
            replay["cases"]["normal"]["status"] == FACTS["normal"]
            and replay["cases"]["protected-change"]["status"] == FACTS["protected_change"]
            and replay["model"] == FACTS["model"]
            and replay["candidate_execution"] == FACTS["candidate_execution"]
            and replay["actual_provider_usage"] == FACTS["actual_provider_usage"]
            and science["verdict"] == FACTS["original_claim"]
            and science["claimed_s"] == FACTS["claimed_s"]
            and science["replayed_s"] == FACTS["replayed_s"]
        )
    except (DemoInvalid, KeyError, TypeError):
        return "PINNED_EVIDENCE_FACT_MISMATCH"
    return "MATCHED_PINNED_STATIC_FACTS" if matched else "PINNED_EVIDENCE_FACT_MISMATCH"


def inspect_sources(root):
    entries, matched, blockers = {}, {}, []
    for name, expected in PINS.items():
        entry, raw = _inspect(root / name, expected)
        entries[name] = entry
        if entry["status"] != "MATCHED":
            blockers.append({"artifact": name, "reason": "REQUIRED_SOURCE_" + entry["status"]})
        else:
            matched[name] = raw
    archive, _ = _inspect(root.parent / "Nebius_Coding_PoC_nebius_009.zip",
                          SOURCE_PACKAGE_SHA256, 1048576, 683857)
    archive["required_for_draft_check"] = False
    if archive["status"] not in ("MATCHED", "MISSING"):
        blockers.append({"artifact": "historical_source_archive", "reason": "ARCHIVE_" + archive["status"]})
    facts = _facts_match(matched)
    if facts != "MATCHED_PINNED_STATIC_FACTS":
        blockers.append({"artifact": "pinned_static_facts", "reason": facts})
    return {
        "required_count": len(PINS), "matched_count": len(matched),
        "all_required_sources_matched": len(matched) == len(PINS),
        "files": entries, "historical_archive": archive,
        "static_facts": facts, "blockers": blockers,
    }


def checked_source():
    """Compatibility check: incomplete historical evidence still raises."""
    result = inspect_sources(ROOT)
    if result["blockers"]:
        raise DemoInvalid("SOURCE_EVIDENCE_INCOMPLETE")
    return dict(PINS)


def milliseconds(value):
    if not re.fullmatch(r"\d\d:\d\d:\d\d,\d\d\d", value):
        raise DemoInvalid("INVALID_CAPTION_TIMESTAMP")
    h, m, s, ms = map(int, re.split("[:,]", value))
    if m >= 60 or s >= 60:
        raise DemoInvalid("INVALID_CAPTION_TIMESTAMP")
    return ((h * 60 + m) * 60 + s) * 1000 + ms


def validate(data, captions, markdown):
    if (
        not isinstance(data, dict)
        or type(data.get("schema_version")) is not int
        or data["schema_version"] != 1
        or data.get("source_run_id") != "20261003T204649Z-nebius-009"
        or not isinstance(captions, str)
        or not isinstance(markdown, str)
    ):
        raise DemoInvalid("INVALID_DRAFT_SHAPE")
    if (
        data.get("run_id") != RUN_ID
        or data.get("status") != "RECORDING_DRAFT_NOT_SUBMITTED"
        or data.get("video_recorded") is not False
        or data.get("actual_recorded_duration_seconds") != "unknown"
        or data.get("manual_review_required") is not True
    ):
        raise DemoInvalid("NOT_AN_UNRECORDED_MANUAL_REVIEW_DRAFT")
    if (
        data.get("source_sha256") != PINS
        or data.get("source_package_sha256") != SOURCE_PACKAGE_SHA256
    ):
        raise DemoInvalid("OPERATOR_SOURCE_PIN_MISMATCH")
    if data.get("facts") != FACTS:
        raise DemoInvalid("STRUCTURED_CLAIM_OVERSTATEMENT")
    duration = data.get("timeline_seconds")
    if type(duration) is not int or not 0 < duration < 180:
        raise DemoInvalid("PLANNED_TIMELINE_EXCEEDS_BOUND")
    scenes = data.get("scenes")
    if not isinstance(scenes, list) or len(scenes) != 6:
        raise DemoInvalid("EXPECTED_SIX_SCENES")
    current = 0
    narration = []
    for scene in scenes:
        if not isinstance(scene, dict):
            raise DemoInvalid("INVALID_SCENE_SHAPE")
        start, end = scene.get("start_seconds"), scene.get("end_seconds")
        if (
            type(start) is not int
            or type(end) is not int
            or start != current
            or end <= start
        ):
            raise DemoInvalid("SCENE_TIME_DISCONTINUITY")
        for field in ("narration", "shot", "title"):
            if not isinstance(scene.get(field), str) or not scene[field].strip():
                raise DemoInvalid("SCENE_TEXT_MISSING")
        if scene["narration"] not in markdown:
            raise DemoInvalid("MARKDOWN_NARRATION_MISMATCH")
        narration.append(scene["narration"])
        current = end
    if current != duration:
        raise DemoInvalid("SCENE_DURATION_MISMATCH")
    spoken = " ".join(" ".join(narration).split())
    word_count = len(spoken.split())
    if not 200 <= word_count <= 330:
        raise DemoInvalid("NARRATION_WORD_BOUND")
    current = 0
    caption_text = []
    cues = captions.strip().split("\n\n")
    for number, block in enumerate(cues, 1):
        lines = block.splitlines()
        if len(lines) not in (3, 4) or lines[0] != str(number):
            raise DemoInvalid("CAPTION_INDEX_OR_LINES")
        times = lines[1].split(" --> ")
        if len(times) != 2:
            raise DemoInvalid("CAPTION_TIME_SHAPE")
        start, end = map(milliseconds, times)
        if start != current or not 0 < end - start <= 10000:
            raise DemoInvalid("CAPTION_TIME_DISCONTINUITY")
        if any(len(line) > 46 for line in lines[2:]):
            raise DemoInvalid("CAPTION_LINE_TOO_LONG")
        text = " ".join(lines[2:])
        if len(text.split()) / ((end - start) / 1000) > 3:
            raise DemoInvalid("CAPTION_READING_RATE_TOO_HIGH")
        caption_text.append(text)
        current = end
    if current != duration * 1000:
        raise DemoInvalid("CAPTION_DURATION_MISMATCH")
    if " ".join(" ".join(caption_text).split()) != spoken:
        raise DemoInvalid("CAPTION_NARRATION_MISMATCH")
    return {
        "planned_seconds": duration,
        "scene_count": len(scenes),
        "caption_count": len(cues),
        "narration_words": word_count,
        "planned_words_per_minute": word_count * 60 / duration,
        "actual_recorded_seconds": "unknown",
        "manual_review_required": True,
    }


def audit_demo(root=None):
    root = ROOT if root is None else root
    source = inspect_sources(root)
    blockers = list(source["blockers"])
    artifacts, raw = {}, {}
    for name in DRAFT_FILES:
        entry, value = _inspect(root / name)
        artifacts[name] = entry
        if value is None:
            blockers.append({"artifact": name, "reason": "DRAFT_" + entry["status"]})
        else:
            raw[name] = value
    draft = {"status": "BLOCKED_INPUT_UNAVAILABLE", "artifacts": artifacts}
    if len(raw) == len(DRAFT_FILES):
        try:
            data = _strict_json(raw[DRAFT_FILES[0]])
            measured = validate(data, raw[DRAFT_FILES[1]].decode("utf-8"),
                                raw[DRAFT_FILES[2]].decode("utf-8"))
            draft.update(status="MATCHED_DRAFT_STRUCTURE", measurements=measured)
        except (DemoInvalid, UnicodeError) as exc:
            reason = str(exc) if isinstance(exc, DemoInvalid) else "INVALID_DRAFT_ENCODING"
            draft.update(status="BLOCKED_INVALID_DRAFT", reason=reason)
            blockers.append({"artifact": "demo_draft", "reason": reason})
    helper, _ = _inspect(root / "scripts/package_checkpoint.py")
    helper.update(required_for_draft_check=False, authority="HISTORICAL_PACKAGING_NOT_VERIFIED")
    implementation = {}
    for name in ("scripts/verify_demo.py", "labrepair/historical_bytes.py"):
        entry, _ = _inspect(root / name)
        implementation[name] = entry
    return {
        "schema": SCHEMA,
        "audit_kind": "CURRENT_OFFLINE_DEMO_EVIDENCE_CHECK",
        "historical_draft_run_id": RUN_ID,
        "verified_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "BLOCKED_EVIDENCE_GAPS" if blockers else "OFFLINE_DRAFT_CHECKS_MATCHED",
        "success": not blockers,
        "source_evidence": source,
        "draft_validation": draft,
        "historical_packaging_helper": helper,
        "implementation": implementation,
        "blockers": blockers,
        "recording_ready": False,
        "submission_ready": False,
        "manual_content_review": "NOT_RUN",
        "visual_qa": "NOT_RUN",
        "recording": "NOT_RUN",
        "actual_recorded_duration_seconds": "unknown",
        "live_provider": "NOT_RUN",
        "candidate_execution": "NOT_RUN",
        "isolated_runtime": "NOT_RUN",
        "submission": "NOT_RUN",
        "actual_provider_usage": "unknown",
        "actual_provider_cost": "unknown",
        "network_requests": 0,
        "source_inputs_modified": False,
        "validation_limit": "Checks bounded static bytes, source pins and draft structure. Not a fresh replay, authenticated signature, semantic proof, browser review or final-video duration check. Missing historical evidence is never reconstructed or waived.",
    }


def _write_new(path, raw):
    """Publish complete bytes atomically without replacing an existing name."""
    absolute = path if path.is_absolute() else Path.cwd() / path
    reserved = {ROOT / name for name in (*PINS, *DRAFT_FILES,
                                        "scripts/package_checkpoint.py",
                                        "scripts/verify_demo.py", "labrepair/historical_bytes.py")}
    reserved.add(ROOT.parent / "Nebius_Coding_PoC_nebius_009.zip")
    if absolute in reserved:
        raise DemoInvalid("RESERVED_INPUT_OUTPUT_FORBIDDEN")
    if not hasattr(os, "O_TMPFILE") or os.link not in os.supports_dir_fd:
        raise DemoInvalid("SAFE_FILE_ACCESS_UNAVAILABLE")
    with _directory(path.parent) as parent:
        # Linux anonymous staging has no directory entry for another writer to
        # replace. Unsupported filesystems fail closed; there is no named fallback.
        descriptor = os.open(".", os.O_WRONLY | os.O_TMPFILE | os.O_NOFOLLOW, 0o600, dir_fd=parent)
        try:
            with os.fdopen(os.dup(descriptor), "wb") as stream:
                if stream.write(raw) != len(raw):
                    raise OSError("INCOMPLETE_RECEIPT_WRITE")
                stream.flush()
                os.fsync(stream.fileno())
            # This trusted kernel path binds publication to the still-open
            # written inode, never a mutable staging name. A hard link fails
            # atomically if the final name appears concurrently.
            os.link(f"/proc/self/fd/{descriptor}", path.name, dst_dir_fd=parent,
                    follow_symlinks=True)
        finally:
            os.close(descriptor)


class _SafeParser(argparse.ArgumentParser):
    def error(self, message):
        raise DemoInvalid("INVALID_COMMAND_LINE")


def main(argv=None):
    parser = _SafeParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--output", type=Path, help="optional new JSON receipt; parent directory must exist")
    try:
        args = parser.parse_args(argv)
        result = audit_demo()
        raw = (json.dumps(result, indent=2, allow_nan=False) + "\n").encode("utf-8")
        if args.output is not None:
            _write_new(args.output, raw)
    except (DemoInvalid, OSError, ValueError, NotImplementedError):
        print(json.dumps({"schema": SCHEMA, "status": "AUDIT_NOT_SAVED", "success": False,
                          "reason": "INPUT_OR_NEW_OUTPUT_UNAVAILABLE", "live_provider": "NOT_RUN",
                          "recording_ready": False, "submission_ready": False}))
        return 2
    print(raw.decode("utf-8"), end="")
    return 0 if result["success"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
