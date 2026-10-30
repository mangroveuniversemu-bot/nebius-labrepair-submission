"""Record one real local verification of synthetic HTTP-contract rehearsals."""

import io
import json
import platform
import re
import subprocess
import sys
import time
import unittest
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from labrepair.candidate_review import digest
from labrepair.offline_exchange import FixtureSession, HTTPFixture
from labrepair.preflight import inspect_environment
from labrepair.provider_envelope import MAX_RESPONSE_BYTES, encoded, prepare_request
from labrepair.q4_source import load_source, verify_import
from labrepair.replay import CASES, replay_case

RUN_ID = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-labrepair-offline-" + uuid.uuid4().hex[:8]
OUTPUT = ROOT / "evidence" / "cloud-runs" / RUN_ID
PRESERVED = (
    "labrepair/provider_envelope.py",
    "labrepair/q4_source.py",
    "handover-workbench/index.html",
    "handover-workbench/offline-handover.json",
    "handover-workbench/fresh-replay.json",
    "handover-workbench/historical-domain.json",
    "docs/DEMO_SCRIPT_165S.md",
    "docs/nebius_demo_010.srt",
    "docs/nebius_demo_010.json",
)


def save(name, value):
    OUTPUT.mkdir(parents=True, exist_ok=True)
    path = OUTPUT / name
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    return path


def main() -> int:
    source_before = verify_import()
    legacy = "evidence/nebius_010_verification.json"
    preserved = (*PRESERVED, legacy) if (ROOT / legacy).is_file() else PRESERVED
    old_hashes = {name: digest((ROOT / name).read_bytes()) for name in preserved}
    draft = prepare_request()
    source = load_source()
    proposal = {
        "snapshot_sha256": source.contract.snapshot_sha256,
        "policy_sha256": source.contract.policy_sha256,
        "replacements": [
            {
                "path": "ledger.py",
                "before_sha256": digest(dict(source.contract.originals)["ledger.py"]),
                "after_utf8": source.correct_literal_fixture,
            }
        ],
    }
    response = {
        "model": draft.model_id,
        "choices": [
            {
                "index": 0,
                "finish_reason": "stop",
                "message": {"role": "assistant", "content": json.dumps(proposal)},
            }
        ],
        "usage": {"prompt_tokens": 5, "completion_tokens": 7, "total_tokens": 12},
        "fixture_label": "SYNTHETIC; reviewed literal, NOT model-generated",
    }
    normal = {
        "status_code": 200,
        "content_type": "application/json; charset=utf-8",
        "body_utf8": json.dumps(response),
    }
    error = {
        "status_code": 429,
        "content_type": "application/json",
        "body_utf8": "SYNTHETIC_PRIVATE_ERROR_MARKER; not a real credential",
    }
    normal_path = save("nebius_011_normal_wire_fixture.json", normal)
    error_path = save("nebius_011_error_wire_fixture.json", error)
    base = [sys.executable, "-m", "labrepair.offline_exchange"]
    commands = []
    log_bytes = b""
    cli_data = {}
    for name, fixture in (
        ("disabled", None),
        ("normal", normal_path),
        ("error", error_path),
    ):
        output = OUTPUT / f"nebius_011_{name}_cli_receipt.json"
        if output.exists():
            output = OUTPUT / (
                f"nebius_011_{name}_cli_receipt_replay_{time.time_ns()}.json"
            )
        absent_before = not output.exists()
        command = [*base, "--output", str(output)]
        if fixture is not None:
            command += ["--fixture", str(fixture)]
        started = time.perf_counter()
        child = subprocess.run(
            command, cwd=ROOT, capture_output=True, timeout=20, check=False
        )
        commands.append(
            {
                "command": command,
                "exit_code": child.returncode,
                "elapsed_seconds": time.perf_counter() - started,
                "receipt_absent_before": absent_before,
                "stdout_matches_new_receipt": json.loads(child.stdout)
                == json.loads(output.read_text(encoding="utf-8")),
            }
        )
        log_bytes += child.stdout + child.stderr
        cli_data[name] = json.loads(output.read_text(encoding="utf-8"))
    normal_output = Path(commands[1]["command"][4])
    existing_hash = digest(normal_output.read_bytes())
    overwrite = subprocess.run(
        commands[1]["command"], cwd=ROOT, capture_output=True, timeout=20, check=False
    )
    overwrite_ok = (
        overwrite.returncode == 2
        and digest(normal_output.read_bytes()) == existing_hash
    )
    log_bytes += overwrite.stdout + overwrite.stderr

    controls = {}
    for name, fixture in (
        ("redirect", HTTPFixture(307, body=b"SYNTHETIC_LOCATION_NOT_FOLLOWED")),
        ("tls_failure", HTTPFixture(failure="TLS")),
        ("oversized_reply", HTTPFixture(200, body=b"x" * (MAX_RESPONSE_BYTES + 20))),
        (
            "authentication_failure",
            HTTPFixture(401, body=b"SYNTHETIC_PRIVATE_ERROR_MARKER"),
        ),
    ):
        controls[name] = FixtureSession().rehearse(draft, fixture)
    session = FixtureSession()
    session.rehearse(draft, HTTPFixture(failure="TIMEOUT"))
    controls["retry_after_timeout"] = session.rehearse(
        draft, HTTPFixture(200, body=encoded(response))
    )
    protected = json.loads(json.dumps(response))
    edit = json.loads(protected["choices"][0]["message"]["content"])
    edit["replacements"][0]["path"] = "runner.py"
    protected["choices"][0]["message"]["content"] = json.dumps(edit)
    controls["protected_edit_with_usage"] = FixtureSession().rehearse(
        draft, HTTPFixture(200, body=encoded(protected))
    )
    save("nebius_011_negative_controls.json", controls)

    own_log = io.StringIO()
    started = time.perf_counter()
    suite = unittest.defaultTestLoader.discover(str(ROOT / "tests"))
    tested = unittest.TextTestRunner(stream=own_log, verbosity=2).run(suite)
    own_seconds = time.perf_counter() - started
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
    count = int(match.group(1)) if match else None
    preflight = inspect_environment()
    domain = {
        "run_id": RUN_ID,
        "mode": "ACTUAL_LOCAL_SYNTHETIC_REPLAY; separate from invoice Coding",
        "cases": [replay_case(case) for case in CASES],
        "scientific_repair": "NOT_RUN",
    }
    save("nebius_011_preflight.json", preflight)
    save("nebius_011_domain_replay.json", domain)
    own_bytes = own_log.getvalue().encode()
    (OUTPUT / "nebius_011_tests.log").write_bytes(own_bytes)
    (OUTPUT / "nebius_011_upstream_tests.log").write_bytes(upstream_log)
    (OUTPUT / "nebius_011_cli.log").write_bytes(log_bytes)
    unchanged = verify_import() == source_before and all(
        digest((ROOT / name).read_bytes()) == expected
        for name, expected in old_hashes.items()
    )
    normal_ok = (
        cli_data["normal"]["status"] == "BLOCKED"
        and cli_data["normal"]["fixture_reported_usage"]["total_tokens"] == 12
    )
    error_ok = (
        cli_data["error"]["reasons"] == ["RATE_LIMITED_NO_RETRY"]
        and b"SYNTHETIC_PRIVATE_ERROR_MARKER" not in log_bytes
    )
    negative_ok = (
        controls["redirect"]["reasons"] == ["REDIRECT_REFUSED_NO_FOLLOW"]
        and controls["tls_failure"]["status"] == "FAILED"
        and controls["oversized_reply"]["response_sha256"] == "unknown"
        and controls["authentication_failure"]["status"] == "FAILED"
        and controls["retry_after_timeout"]["fixture_exchanges_this_call"] == 0
        and controls["protected_edit_with_usage"]["reasons"]
        == ["PROTECTED_FILE_CHANGE"]
        and controls["protected_edit_with_usage"]["fixture_reported_usage"][
            "total_tokens"
        ]
        == 12
    )
    domain_ok = all(item["matches_expected"] for item in domain["cases"])
    ok = (
        tested.wasSuccessful()
        and upstream.returncode == 0
        and count == 17
        and all(item["exit_code"] == 2 for item in commands)
        and all(
            item["receipt_absent_before"] and item["stdout_matches_new_receipt"]
            for item in commands
        )
        and cli_data["disabled"]["status"] == "BLOCKED"
        and overwrite_ok
        and normal_ok
        and error_ok
        and negative_ok
        and unchanged
        and domain_ok
        and not preflight["live_configuration_enabled"]
    )
    verification = {
        "run_id": RUN_ID,
        "checkpoint": "CLOUD_OFFLINE_PORTABILITY",
        "historical_nebius_010_receipt": "PRESERVED_NOT_REVALIDATED" if legacy in old_hashes else "ABSENT_NOT_REQUIRED_FOR_CURRENT_REPLAY",
        "success": ok,
        "verified_at_utc": datetime.now(timezone.utc).isoformat(),
        "command": [sys.executable, "scripts/verify_offline_exchange.py"],
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "new_packages_installed": "unknown; see environment provisioning receipt",
        },
        "product_increment": "Single-use offline HTTP-contract session, bounded response reads, sanitized failures, no automatic retry and usage independent of proposal acceptance",
        "tests": {
            "actual_count": tested.testsRun,
            "success": tested.wasSuccessful(),
            "failures": len(tested.failures),
            "errors": len(tested.errors),
            "elapsed_seconds": own_seconds,
            "log_sha256": digest(own_bytes),
        },
        "q4_fixture_regression": {
            "actual_count": count,
            "exit_code": upstream.returncode,
            "command": upstream_command,
            "cwd": "vendor/q4-coding",
            "elapsed_seconds": upstream_seconds,
            "log_sha256": digest(upstream_log),
            "real_provider": "NOT_RUN; fake-client/recovery fixtures only",
        },
        "actual_cli": {
            "commands": commands,
            "success": normal_ok and error_ok and overwrite_ok,
            "existing_receipt_overwrite_refused": overwrite_ok,
            "log_sha256": digest(log_bytes),
            "all_expected_exits": 2,
        },
        "negative_controls": {
            "count": 6,
            "success": negative_ok,
            "receipt": str((OUTPUT / "nebius_011_negative_controls.json").relative_to(ROOT)),
        },
        "domain_replay": {
            "actual_synthetic_cases": 6,
            "all_expected_match": domain_ok,
            "scientific_repair": "NOT_RUN",
        },
        "source_and_archived_artifacts_unchanged": unchanged,
        "preserved_inputs_sha256": old_hashes,
        "source_bindings": source.provenance(),
        "new_code_sha256": {
            name: digest((ROOT / name).read_bytes())
            for name in (
                "labrepair/offline_exchange.py",
                "tests/test_offline_exchange.py",
                "scripts/verify_offline_exchange.py",
                "labrepair/historical_bytes.py",
                "labrepair/handover.py",
                "labrepair/handover_view.py",
                "tests/test_historical_bytes.py",
                "tests/test_handover_view.py",
            )
        },
        "input_hashes": {
            path.name: digest(path.read_bytes()) for path in (normal_path, error_path)
        },
        "real_http_transport": "NOT_IMPLEMENTED",
        "live_provider": "NOT_RUN",
        "candidate_execution": "NOT_RUN",
        "provider_usage": "unknown",
        "provider_elapsed_seconds": "unknown",
        "credits_and_monetary_cap": "UNVERIFIED",
        "coverage_note": "Focused initial 12-test check and duplicate full runs are not summed. Historical 277/45/60/72/NEBIUS-010 demo checks not rerun or included.",
    }
    save("nebius_011_verification.json", verification)
    print(json.dumps(verification))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
