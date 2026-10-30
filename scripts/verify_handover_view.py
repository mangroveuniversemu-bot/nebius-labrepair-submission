"""Record one actual read-only reviewer increment without cloud/candidate calls."""

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
from labrepair.handover import ORIGIN_PINS
from labrepair.handover_view import DOMAIN_SHA256, RUN_ID, create_view, failure_page
from labrepair.preflight import inspect_environment
from labrepair.q4_source import verify_import
from labrepair.replay import CASES, replay_case

ARCHIVED_UI_SHA256 = "89ffcc80db8938b8208b541dd3c5ab01e099571f51f9c047a324e02b5ec4b395"
BUNDLE_SHA256 = "2f6690b9b77430ebdd87eb08292241e5ba491f317e92c92616df498b617d30aa"


def save(name, value):
    (ROOT / "evidence" / name).write_text(
        json.dumps(value, indent=2) + "\n", encoding="utf-8"
    )


def main() -> int:
    before = verify_import()
    raw = (ROOT / "evidence/nebius_008_handover.json").read_bytes()
    domain_raw = (ROOT / "evidence/nebius_008_domain_replay.json").read_bytes()
    negative_path = ROOT / "evidence/nebius_008_forged_receipt_bundle.json"
    negative = json.loads(negative_path.read_bytes())
    member = negative["members"]["receipts/normal.json"]
    if (
        json.loads(member)["status"] != "ACCEPTED"
        or digest(member.encode()) != negative["manifest"]["receipts/normal.json"]
    ):
        raise RuntimeError("negative_control_not_a_rehashed_forged_acceptance")
    commands, cli_log = [], b""
    for args, expected in (
        ([], 0),
        (
            [
                "--input",
                "evidence/nebius_008_forged_receipt_bundle.json",
                "--rejected-preview",
            ],
            2,
        ),
    ):
        started = time.perf_counter()
        result = subprocess.run(
            [sys.executable, "-m", "labrepair.handover_view", *args],
            cwd=ROOT,
            capture_output=True,
            check=False,
            timeout=20,
        )
        cli_log += result.stdout + result.stderr
        commands.append(
            {
                "executable": ".venv/Scripts/python.exe",
                "module": "labrepair.handover_view",
                "arguments": args,
                "expected_exit": expected,
                "exit_code": result.returncode,
                "elapsed_seconds": time.perf_counter() - started,
            }
        )
    files, view = create_view(raw, domain_raw)
    output_ok = all(
        (ROOT / "handover-workbench" / name).read_bytes() == data
        for name, data in files.items()
    )
    failure_ok = (
        ROOT / "handover-workbench/qa/rejected.html"
    ).read_bytes() == failure_page()
    log = io.StringIO()
    started = time.perf_counter()
    result = unittest.TextTestRunner(stream=log, verbosity=2).run(
        unittest.defaultTestLoader.discover(str(ROOT / "tests"))
    )
    elapsed = time.perf_counter() - started
    own_log = log.getvalue().encode()
    started = time.perf_counter()
    upstream = subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"],
        cwd=ROOT / "vendor/q4-coding",
        capture_output=True,
        check=False,
        timeout=20,
    )
    upstream_elapsed = time.perf_counter() - started
    upstream_log = upstream.stdout + upstream.stderr
    count = re.search(rb"Ran (\d+) tests?", upstream_log)
    upstream_count = int(count.group(1)) if count else None
    preflight = inspect_environment()
    domain = {
        "run_id": RUN_ID,
        "mode": "ACTUAL_LOCAL_SYNTHETIC_REPLAY; separate Bell/CHSH domain",
        "cases": [replay_case(case) for case in CASES],
        "scientific_repair": "NOT_RUN",
    }
    source_ok = verify_import() == before
    origin_hashes = {
        name: digest((ROOT / "evidence" / name).read_bytes()) for name in ORIGIN_PINS
    }
    source_ok = source_ok and origin_hashes == ORIGIN_PINS
    old_ui_ok = (
        digest((ROOT / "workbench/index.html").read_bytes()) == ARCHIVED_UI_SHA256
    )
    domain_ok = all(case["matches_expected"] for case in domain["cases"])
    pinned_ok = digest(raw) == BUNDLE_SHA256 and digest(domain_raw) == DOMAIN_SHA256
    cli_ok = all(
        command["exit_code"] == command["expected_exit"] for command in commands
    )
    ok = all(
        (
            cli_ok,
            output_ok,
            failure_ok,
            pinned_ok,
            source_ok,
            old_ui_ok,
            result.wasSuccessful(),
            upstream.returncode == 0,
            upstream_count == 17,
            domain_ok,
            not preflight["live_configuration_enabled"],
        )
    )
    for name, data in (
        ("nebius_009_tests.log", own_log),
        ("nebius_009_upstream_tests.log", upstream_log),
        ("nebius_009_cli.log", cli_log),
    ):
        (ROOT / "evidence" / name).write_bytes(data)
    save("nebius_009_domain_replay.json", domain)
    save("nebius_009_preflight.json", preflight)
    source_files = [
        path
        for folder in ("labrepair", "scripts", "tests")
        for path in sorted((ROOT / folder).glob("*.py"))
    ]
    verification = {
        "run_id": RUN_ID,
        "checkpoint": "NEBIUS-009",
        "verified_at_utc": datetime.now(timezone.utc).isoformat(),
        "command": ".venv/Scripts/python.exe scripts/verify_handover_view.py",
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "new_packages_installed": False,
        },
        "increment": "Read-only handover reviewer generated by fresh independent replay, with separate unchanged historical science context and fail-closed QA page",
        "tests": {
            "actual_count": result.testsRun,
            "view_tests": 8,
            "failures": len(result.failures),
            "errors": len(result.errors),
            "success": result.wasSuccessful(),
            "elapsed_seconds": elapsed,
            "log_sha256": digest(own_log),
        },
        "upstream_fixture_tests": {
            "actual_count": upstream_count,
            "exit_code": upstream.returncode,
            "elapsed_seconds": upstream_elapsed,
            "log_sha256": digest(upstream_log),
            "real_provider": "NOT_RUN; injected fake clients and recovery fixtures only",
        },
        "actual_cli": {
            "commands": commands,
            "success": cli_ok,
            "log_sha256": digest(cli_log),
        },
        "view": {
            **view,
            "all_static_bytes_readback": output_ok,
            "rehashed_forged_acceptance_rejected": failure_ok,
            "negative_page_has_no_success_or_download_links": True,
            "negative_input_sha256": digest(negative_path.read_bytes()),
        },
        "origin_inputs_unchanged": source_ok,
        "origin_input_sha256": origin_hashes,
        "archived_workbench_unchanged": old_ui_ok,
        "archived_workbench_sha256": ARCHIVED_UI_SHA256,
        "historical_bundle_and_science_pins_unchanged": pinned_ok,
        "source_sha256": {
            path.relative_to(ROOT).as_posix(): digest(path.read_bytes())
            for path in source_files
        },
        "domain_replay": {
            "actual_cases": len(domain["cases"]),
            "all_expected_match": domain_ok,
            "scientific_repair": "NOT_RUN",
        },
        "latest_shared_source": "Listing remains 107 KB, modified 2026-10-04 02:54 Taipei; latest raw bytes UNVERIFIED. Pinned older source unchanged.",
        "historical_totals": "277/45/60/72 NOT_RERUN_NOT_INCLUDED; earlier same-run 69 tests not summed",
        "live_provider": "NOT_RUN",
        "isolated_runtime": "NOT_RUN",
        "candidate_execution": "NOT_RUN",
        "provider_usage": "unknown",
        "browser_verification": "PENDING_SEPARATE_RECEIPT",
        "success": ok,
    }
    save("nebius_009_verification.json", verification)
    print(json.dumps(verification))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
