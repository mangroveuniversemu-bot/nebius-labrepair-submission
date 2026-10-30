"""Record actual NEBIUS-005 local tests without overwriting prior receipts."""

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
sys.path.insert(0, str(ROOT))


def main() -> int:
    log = io.StringIO()
    started = time.perf_counter()
    suite = unittest.defaultTestLoader.discover(str(ROOT / "tests"))
    result = unittest.TextTestRunner(stream=log, verbosity=2).run(suite)
    raw = log.getvalue().encode("utf-8")
    files = sorted((ROOT / "labrepair").glob("*.py")) + sorted(
        (ROOT / "tests").glob("*.py")
    )
    receipt = {
        "run_id": "20261003T164615Z-nebius-005",
        "verified_at_utc": datetime.now(timezone.utc).isoformat(),
        "command": ".venv/Scripts/python.exe scripts/verify_workbench.py",
        "python": platform.python_version(),
        "tests_run": result.testsRun,
        "failures": len(result.failures),
        "errors": len(result.errors),
        "skipped": len(result.skipped),
        "success": result.wasSuccessful(),
        "local_suite_seconds": time.perf_counter() - started,
        "test_log_sha256": hashlib.sha256(raw).hexdigest(),
        "source_sha256": {
            path.relative_to(ROOT).as_posix(): hashlib.sha256(
                path.read_bytes()
            ).hexdigest()
            for path in files
        },
        "test_scope": "7 workbench + 13 intake + 9 domain bridge; no provider or sandbox",
        "previous_receipts_displayed_not_rerun": ["LAB-001", "NEBIUS-004"],
        "upstream_277_and_shared_45_60": "HISTORICAL_NOT_RERUN_NOT_INCLUDED",
        "model": "NOT_RUN",
        "candidate_execution": "NOT_RUN",
        "provider_usage": "unknown",
    }
    (ROOT / "evidence" / "nebius_005_tests.log").write_bytes(raw)
    (ROOT / "evidence" / "nebius_005_verification.json").write_text(
        json.dumps(receipt, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(receipt))
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
