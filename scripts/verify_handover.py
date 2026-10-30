"""Record an actual offline handover round; do not rerun model/source execution."""

import io
import json
import platform
import re
import subprocess
import sys
import time
import unittest
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from labrepair.candidate_review import digest
from labrepair.handover import ORIGIN_PINS, build_bundle, replay_bundle
from labrepair.preflight import inspect_environment
from labrepair.provider_envelope import encoded
from labrepair.q4_source import verify_import
from labrepair.replay import CASES, replay_case

RUN_ID = "20261003T194518Z-nebius-008"


def save(name, value):
    path = ROOT / "evidence" / name
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    return path


def main() -> int:
    before = verify_import()
    origin_before = {
        name: digest((ROOT / "evidence" / name).read_bytes()) for name in ORIGIN_PINS
    }
    bundle_path = ROOT / "evidence/nebius_008_handover.json"
    receipt_path = ROOT / "evidence/nebius_008_replay.json"
    negative_path = ROOT / "evidence/nebius_008_forged_receipt_bundle.json"
    negative_out = ROOT / "evidence/nebius_008_forged_replay.json"
    # A same-run retry preserves successful historical receipts; only fill gaps.
    commands = []
    cli_log = b""

    def call(arguments, expected, output_path=None):
        nonlocal cli_log
        cmd = [sys.executable, "-m", "labrepair.handover", *arguments]
        if output_path and output_path.exists():
            commands.append(
                {
                    "arguments": arguments,
                    "same_run_retry": "SKIPPED_EXISTING; bytes verified below",
                }
            )
            return True
        started = time.perf_counter()
        result = subprocess.run(
            cmd, cwd=ROOT, capture_output=True, check=False, timeout=20
        )
        cli_log += result.stdout + result.stderr
        commands.append(
            {
                "executable": ".venv/Scripts/python.exe",
                "arguments": arguments,
                "exit_code": result.returncode,
                "elapsed_seconds": time.perf_counter() - started,
            }
        )
        return result.returncode == expected

    exported = call(["--export", "evidence/nebius_008_handover.json"], 0, bundle_path)
    replayed = call(
        [
            "--replay",
            "evidence/nebius_008_handover.json",
            "--output",
            "evidence/nebius_008_replay.json",
        ],
        0,
        receipt_path,
    )
    raw = bundle_path.read_bytes()
    replay = replay_bundle(raw)
    expected_bundle = build_bundle()
    stored = json.loads(receipt_path.read_bytes())
    value = json.loads(raw)
    forged = json.loads(value["members"]["receipts/normal.json"])
    forged["status"] = "ACCEPTED"
    value["members"]["receipts/normal.json"] = encoded(forged).decode()
    value["manifest"]["receipts/normal.json"] = digest(encoded(forged))
    negative = encoded(value)
    if not negative_path.exists():
        negative_path.write_bytes(negative)
    if negative_path.read_bytes() != negative:
        raise RuntimeError("same_run_negative_input_changed")
    refused = call(
        [
            "--replay",
            "evidence/nebius_008_forged_receipt_bundle.json",
            "--output",
            "evidence/nebius_008_forged_replay.json",
        ],
        2,
    )
    no_false_receipt = not negative_out.exists()
    overwrite_refused = call(["--export", "evidence/nebius_008_handover.json"], 2)
    log = io.StringIO()
    started = time.perf_counter()
    result = unittest.TextTestRunner(stream=log, verbosity=2).run(
        unittest.defaultTestLoader.discover(str(ROOT / "tests"))
    )
    elapsed = time.perf_counter() - started
    raw_log = log.getvalue().encode()
    upstream_command = [
        sys.executable,
        "-m",
        "unittest",
        "discover",
        "-s",
        "tests",
        "-v",
    ]
    started = time.perf_counter()
    upstream = subprocess.run(
        upstream_command,
        cwd=ROOT / "vendor/q4-coding",
        capture_output=True,
        check=False,
        timeout=20,
    )
    upstream_elapsed = time.perf_counter() - started
    upstream_log = upstream.stdout + upstream.stderr
    match = re.search(rb"Ran (\d+) tests?", upstream_log)
    upstream_count = int(match.group(1)) if match else None
    preflight = inspect_environment()
    domain = {
        "run_id": RUN_ID,
        "mode": "ACTUAL_LOCAL_SYNTHETIC_REPLAY; separate Bell/CHSH domain",
        "cases": [replay_case(case) for case in CASES],
        "scientific_repair": "NOT_RUN",
    }
    source_ok = verify_import() == before and origin_before == ORIGIN_PINS
    source_ok = source_ok and origin_before == {
        name: digest((ROOT / "evidence" / name).read_bytes()) for name in ORIGIN_PINS
    }
    replay_ok = (
        raw == expected_bundle
        and encoded(stored) == encoded(replay)
        and replay["cases"]["normal"]["status"] == "BLOCKED"
        and replay["cases"]["protected-change"]["reasons"] == ["PROTECTED_FILE_CHANGE"]
    )
    domain_ok = all(case["matches_expected"] for case in domain["cases"])
    ok = all(
        (
            exported,
            replayed,
            refused,
            no_false_receipt,
            overwrite_refused,
            result.wasSuccessful(),
            upstream.returncode == 0,
            upstream_count == 17,
            source_ok,
            replay_ok,
            domain_ok,
            not preflight["live_configuration_enabled"],
        )
    )
    for name, content in (
        ("nebius_008_tests.log", raw_log),
        ("nebius_008_upstream_tests.log", upstream_log),
        ("nebius_008_cli.log", cli_log),
    ):
        (ROOT / "evidence" / name).write_bytes(content)
    save("nebius_008_preflight.json", preflight)
    save("nebius_008_domain_replay.json", domain)
    files = [
        path
        for folder in ("labrepair", "scripts", "tests")
        for path in sorted((ROOT / folder).glob("*.py"))
    ]
    verification = {
        "run_id": RUN_ID,
        "checkpoint": "NEBIUS-008",
        "verified_at_utc": datetime.now(timezone.utc).isoformat(),
        "command": ".venv/Scripts/python.exe scripts/verify_handover.py",
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "new_packages_installed": False,
        },
        "increment": "Portable offline data handover with exact two-case replay, rehashed-verdict rejection and serialization provenance",
        "tests": {
            "actual_count": result.testsRun,
            "handover_tests": 8,
            "failures": len(result.failures),
            "errors": len(result.errors),
            "success": result.wasSuccessful(),
            "elapsed_seconds": elapsed,
            "log_sha256": digest(raw_log),
        },
        "upstream_fixture_tests": {
            "actual_count": upstream_count,
            "command": ".venv/Scripts/python.exe -m unittest discover -s tests -v",
            "cwd": "vendor/q4-coding",
            "exit_code": upstream.returncode,
            "elapsed_seconds": upstream_elapsed,
            "log_sha256": digest(upstream_log),
            "real_provider": "NOT_RUN; injected fake clients and recovery fixtures only",
        },
        "actual_cli": {
            "commands": commands,
            "success": exported and replayed and refused and overwrite_refused,
            "log_sha256": digest(cli_log),
            "false_receipt_not_created": no_false_receipt,
        },
        "handover": {
            "bundle_bytes": len(raw),
            "bundle_sha256": digest(raw),
            "members": replay["member_count"],
            "exact_fresh_replay_match": replay_ok,
            "normal": "BLOCKED; isolation/spend gates unverified",
            "protected_change": "REJECTED PROTECTED_FILE_CHANGE",
            "negative_control": "Rehashed ACCEPTED receipt rejected; no output created",
            "data_extracted_to_source_paths": False,
        },
        "origin_inputs_unchanged": source_ok,
        "origin_input_sha256": origin_before,
        "source_sha256": {
            path.relative_to(ROOT).as_posix(): digest(path.read_bytes())
            for path in files
        },
        "domain_replay": {
            "actual_cases": len(domain["cases"]),
            "all_expected_match": domain_ok,
            "scientific_repair": "NOT_RUN",
        },
        "account_observation": "Token Factory browser session displayed Log in around 2026-10-03T19:51Z; authenticated credits/model/cap UNVERIFIED, no login or API attempted",
        "latest_shared_source": "Unchanged listing: 107 KB modified 2026-10-04 02:54 Taipei; prior standard download HTTP error. Latest byte match UNVERIFIED; no repeated download this round",
        "historical_totals": "277/45/60/72 NOT_RERUN_NOT_INCLUDED",
        "live_provider": "NOT_RUN",
        "isolated_runtime": "NOT_RUN",
        "candidate_execution": "NOT_RUN",
        "provider_usage": "unknown",
        "success": ok,
    }
    save("nebius_008_verification.json", verification)
    print(json.dumps(verification))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
