"""Save actual local suite output and source fingerprints for NEBIUS-004."""

import hashlib
import io
import json
import platform
import sys
import time
import unittest
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUN_ID = "20261003T155145Z-nebius-004"
sys.path.insert(0, str(ROOT))


def main() -> int:
    output = io.StringIO()
    started = time.perf_counter()
    suite = unittest.defaultTestLoader.discover(str(ROOT / "tests"))
    result = unittest.TextTestRunner(stream=output, verbosity=2).run(suite)
    elapsed = time.perf_counter() - started
    evidence = ROOT / "evidence"
    evidence.mkdir(exist_ok=True)
    log = output.getvalue().encode("utf-8")
    (evidence / "nebius_004_tests.log").write_bytes(log)
    files = sorted((ROOT / "labrepair").glob("*.py")) + sorted(
        (ROOT / "tests").glob("*.py")
    )
    receipt = {
        "run_id": RUN_ID,
        "verified_at_utc": datetime.now(timezone.utc).isoformat(),
        "command": ".venv/Scripts/python.exe scripts/verify_review.py",
        "python": platform.python_version(),
        "tests_run": result.testsRun,
        "failures": len(result.failures),
        "errors": len(result.errors),
        "skipped": len(result.skipped),
        "success": result.wasSuccessful(),
        "local_suite_seconds": elapsed,
        "test_log_sha256": hashlib.sha256(log).hexdigest(),
        "source_sha256": {
            path.relative_to(ROOT).as_posix(): hashlib.sha256(
                path.read_bytes()
            ).hexdigest()
            for path in files
        },
        "fixture_label": "Candidate contract tests use in-memory synthetic source only; Q4 source remains unavailable",
        "provider": "NOT_RUN",
        "sandbox": "NOT_RUN",
        "provider_usage": "unknown",
        "historical_upstream_277": "NOT_RERUN_THIS_INCREMENT",
        "historical_shared_45_or_60": "NOT_RERUN_NOT_IMPORTED",
    }
    (evidence / "nebius_004_verification.json").write_text(
        json.dumps(receipt, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(receipt))
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
