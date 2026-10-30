"""Save a reproducible offline request/response round, never provider/candidate execution."""

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
from labrepair.preflight import inspect_environment
from labrepair.provider_envelope import (
    MODEL_CANDIDATE,
    encoded,
    prepare_request,
    review_offline_response,
)
from labrepair.q4_source import load_source, verify_import
from labrepair.replay import CASES, replay_case

RUN_ID = "20261003T185948Z-nebius-007"


def save(name, value):
    path = ROOT / "evidence" / name
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    return path


def main() -> int:
    before = verify_import()
    source = load_source()
    draft = prepare_request()
    fixture = {
        "model": MODEL_CANDIDATE,
        "choices": [
            {
                "index": 0,
                "finish_reason": "stop",
                "message": {
                    "role": "assistant",
                    "content": json.dumps(
                        {
                            "snapshot_sha256": source.contract.snapshot_sha256,
                            "policy_sha256": source.contract.policy_sha256,
                            "replacements": [
                                {
                                    "path": "ledger.py",
                                    "before_sha256": digest(
                                        dict(source.contract.originals)["ledger.py"]
                                    ),
                                    "after_utf8": source.correct_literal_fixture,
                                }
                            ],
                        }
                    ),
                },
            }
        ],
    }
    fixture_path = save("nebius_007_response_fixture.json", fixture)
    preview_path = ROOT / "evidence/nebius_007_request_preview.json"
    intake_path = ROOT / "evidence/nebius_007_response_intake.json"
    base = [sys.executable, "-m", "labrepair.provider_envelope"]
    commands = [
        [*base, "--output", str(preview_path)],
        [*base, "--response-fixture", str(fixture_path), "--output", str(intake_path)],
    ]
    cli_results = []
    cli_log = b""
    for command in commands:
        started = time.perf_counter()
        result = subprocess.run(
            command, cwd=ROOT, capture_output=True, timeout=20, check=False
        )
        cli_results.append(
            {
                "command": command,
                "exit_code": result.returncode,
                "elapsed_seconds": time.perf_counter() - started,
            }
        )
        cli_log += result.stdout + result.stderr
    preview = json.loads(preview_path.read_text(encoding="utf-8"))
    intake = json.loads(intake_path.read_text(encoding="utf-8"))
    negative = json.loads(json.dumps(fixture))
    proposal = json.loads(negative["choices"][0]["message"]["content"])
    proposal["replacements"][0]["path"] = "runner.py"
    negative["choices"][0]["message"]["content"] = json.dumps(proposal)
    negative_receipt = review_offline_response(encoded(negative), draft)
    save("nebius_007_negative_fixture.json", negative)
    save("nebius_007_negative_intake.json", negative_receipt)

    log = io.StringIO()
    started = time.perf_counter()
    suite = unittest.defaultTestLoader.discover(str(ROOT / "tests"))
    result = unittest.TextTestRunner(stream=log, verbosity=2).run(suite)
    seconds = time.perf_counter() - started
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
        timeout=20,
        check=False,
    )
    upstream_seconds = time.perf_counter() - started
    upstream_log = upstream.stdout + upstream.stderr
    match = re.search(rb"Ran (\d+) tests?", upstream_log)
    upstream_count = int(match.group(1)) if match else None

    preflight = inspect_environment()
    domain = {
        "run_id": RUN_ID,
        "mode": "ACTUAL_LOCAL_SYNTHETIC_REPLAY; separate from invoice Coding",
        "cases": [replay_case(case) for case in CASES],
        "scientific_repair": "NOT_RUN",
    }
    domain_ok = all(item["matches_expected"] for item in domain["cases"])
    raw_log = log.getvalue().encode()
    (ROOT / "evidence/nebius_007_tests.log").write_bytes(raw_log)
    (ROOT / "evidence/nebius_007_upstream_tests.log").write_bytes(upstream_log)
    (ROOT / "evidence/nebius_007_cli.log").write_bytes(cli_log)
    save("nebius_007_preflight.json", preflight)
    save("nebius_007_domain_replay.json", domain)
    unchanged = verify_import() == before
    expected_reasons = ["ISOLATED_BACKEND_UNVERIFIED", "SPENDING_LIMIT_UNVERIFIED"]
    cli_ok = (
        all(item["exit_code"] == 2 for item in cli_results)
        and preview["dispatch"] == "NOT_IMPLEMENTED"
        and preview["body_sha256"] == digest(draft.body)
        and intake["request_body_sha256"] == digest(draft.body)
        and intake["status"] == "BLOCKED"
        and intake["reasons"] == expected_reasons
        and len(intake["candidate_review"]["changes"]) == 1
        and intake["execution"] == "NOT_RUN"
        and intake["actual_provider_usage"] == "unknown"
    )
    negative_ok = negative_receipt["status"] == "REJECTED" and negative_receipt[
        "reasons"
    ] == ["PROTECTED_FILE_CHANGE"]
    ok = (
        result.wasSuccessful()
        and upstream.returncode == 0
        and upstream_count == 17
        and cli_ok
        and negative_ok
        and unchanged
        and domain_ok
        and not preflight["live_configuration_enabled"]
    )
    files = [
        path
        for folder in ("labrepair", "tests", "scripts")
        for path in sorted((ROOT / folder).glob("*.py"))
    ]
    verification = {
        "run_id": RUN_ID,
        "checkpoint": "NEBIUS-007",
        "verified_at_utc": datetime.now(timezone.utc).isoformat(),
        "command": ".venv/Scripts/python.exe scripts/verify_provider_envelope.py",
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "new_packages_installed": False,
        },
        "product_increment": "Credential-free source-bound request preview and bounded offline provider-response-to-candidate-review bridge",
        "tests": {
            "actual_count": result.testsRun,
            "failures": len(result.failures),
            "errors": len(result.errors),
            "success": result.wasSuccessful(),
            "elapsed_seconds": seconds,
            "log_sha256": digest(raw_log),
        },
        "upstream_fixture_tests": {
            "actual_count": upstream_count,
            "command": upstream_command,
            "cwd": "vendor/q4-coding",
            "exit_code": upstream.returncode,
            "elapsed_seconds": upstream_seconds,
            "log_sha256": digest(upstream_log),
            "real_provider": "NOT_RUN; fake-client/recovery fixtures only",
        },
        "actual_cli": {
            "commands": cli_results,
            "expected_exits": 2,
            "success": cli_ok,
            "log_sha256": digest(cli_log),
            "result": "Preview only and one reviewed diff BLOCKED; no model/candidate execution",
        },
        "negative_control": {
            "input": "evidence/nebius_007_negative_fixture.json",
            "reason": "PROTECTED_FILE_CHANGE",
            "success": negative_ok,
        },
        "request": draft.receipt(),
        "source_bindings": source.provenance(),
        "input_hashes": {
            name: digest((ROOT / "evidence" / name).read_bytes())
            for name in (
                "nebius_007_response_fixture.json",
                "nebius_007_request_preview.json",
                "nebius_007_response_intake.json",
                "nebius_007_negative_fixture.json",
                "nebius_007_negative_intake.json",
            )
        },
        "source_sha256": {
            path.relative_to(ROOT).as_posix(): digest(path.read_bytes())
            for path in files
        },
        "original_q4_files_unchanged": unchanged,
        "domain_replay": {
            "actual_cases": 6,
            "all_expected_match": domain_ok,
            "scientific_repair": "NOT_RUN",
        },
        "latest_shared_source": "107 KB modified 2026-10-04 02:54 Taipei; standard download HTTP error, latest byte comparison UNVERIFIED",
        "historical_totals": "277/45/60/72 NOT_RERUN_NOT_INCLUDED",
        "live_provider": "NOT_RUN",
        "candidate_execution": "NOT_RUN",
        "provider_usage": "unknown",
        "success": ok,
    }
    save("nebius_007_verification.json", verification)
    print(json.dumps(verification))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
