"""Run the new product acceptance without network providers or candidate code.

The full legacy suite uses Linux descriptor guarantees. On Windows this command
reports only the new cross-platform review and loopback HTTP acceptance suite.
It never rewrites historical receipts or enables a live account gate.
"""

import argparse
import hashlib
import io
import json
import os
import platform
import sys
import time
import unittest
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
from labrepair.scientific_workflow import verify_scenarios


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--full", action="store_true", help="Run all repository tests; Linux required")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.full and os.name != "posix":
        parser.error("full legacy security verification requires the reviewed Linux environment")
    log = io.StringIO()
    loader = unittest.TestLoader()
    if args.full:
        suite = loader.discover(str(REPO / "tests"))
    else:
        suite = unittest.TestSuite([
            loader.discover(str(REPO / "tests"), pattern="test_scientific_workflow.py"),
            loader.discover(str(REPO / "tests"), pattern="test_review_server.py"),
            loader.discover(str(REPO / "tests"), pattern="test_model_parameters.py"),
            loader.discover(str(REPO / "tests"), pattern="test_sandbox_experiment.py"),
            loader.discover(str(REPO / "tests"), pattern="test_recorded_validation.py"),
            loader.discover(str(REPO / "tests"), pattern="test_live_repair.py"),
            loader.discover(str(REPO / "tests"), pattern="test_daily_budget.py"),
        ])
    started = time.perf_counter()
    result = unittest.TextTestRunner(stream=log, verbosity=2).run(suite)
    replay = verify_scenarios()
    data = {
        "schema": "LABREPAIR_POC_VALIDATION_V1",
        "observed_at_utc": datetime.now(timezone.utc).isoformat(),
        "platform": platform.system(), "python": platform.python_version(),
        "suite": "FULL_REPOSITORY" if args.full else "PRODUCT_MODEL_INTAKE_RECORDED_REPLAY_AND_LOOPBACK_HTTP",
        "tests_run": result.testsRun, "failures": len(result.failures), "errors": len(result.errors),
        "skipped": len(result.skipped), "tests_success": result.wasSuccessful(),
        "elapsed_seconds": round(time.perf_counter() - started, 4),
        "test_log_sha256": hashlib.sha256(log.getvalue().encode()).hexdigest(),
        "fixed_synthetic_case_count": replay["curated_scenarios"],
        "fixed_cases_match_expected": replay["success"],
        "naive_total_only_false_accepts_in_fixed_set": replay["naive_total_only_false_accepts"],
        "candidate_code_execution": "NOT_RUN",
        "nebius_generation": "NOT_RUN_BY_THIS_VERIFIER", "nebius_sandbox_execution": "NOT_RUN_BY_THIS_VERIFIER",
        "paid_resources_created": False, "submission_ready": False,
        "live_gap": "Direct Token Factory transport is mock-tested; fresh live execution, current credit coverage and provider spending controls remain unverified by this verifier.",
        "scope": "Real local tests, trusted arithmetic, and pinned recorded live result playback; this verifier makes no provider or Sandbox call.",
    }
    if args.output:
        target = args.output.resolve()
        if not target.is_relative_to((REPO / "evidence").resolve()):
            parser.error("output must be inside evidence")
        if any(p.is_symlink() for p in (target, *target.parents)):
            parser.error("symlink output paths are not allowed")
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(data, indent=2) + "\n")
    if not result.wasSuccessful():
        print(log.getvalue(), file=sys.stderr)
    print(json.dumps(data, indent=2))
    return 0 if result.wasSuccessful() and replay["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
