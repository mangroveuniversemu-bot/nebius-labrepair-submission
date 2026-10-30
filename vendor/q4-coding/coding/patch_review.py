"""Closed-fixture repair demonstration. Not an untrusted-code sandbox.

Only three reviewed, literal source fixtures can execute. A live model adapter
must use a separately verified OpenShell/Token Factory sandbox before removing
that restriction. No source is deployed and no existing repository is edited.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time

BASELINE = '''def total_cents(rows):
    return sum(amount for _, amount in rows)
'''
CORRECT = '''def total_cents(rows):
    seen = {}
    for invoice, amount in rows:
        if type(amount) is not int or amount < 0:
            raise ValueError("invalid amount")
        if invoice in seen and seen[invoice] != amount:
            raise ValueError("conflicting duplicate")
        seen[invoice] = amount
    return sum(seen.values())
'''
REGRESSION = '''def total_cents(rows):
    return sum(set(amount for _, amount in rows))
'''
CASES = [
    {"id": "duplicate_invoice", "rows": [["A", 1000], ["B", 2000], ["A", 1000]], "value": 3000},
    {"id": "distinct_equal_amounts", "rows": [["A", 1000], ["B", 1000]], "value": 2000},
    {"id": "empty", "rows": [], "value": 0},
    {"id": "zero", "rows": [["A", 0]], "value": 0},
    {"id": "conflicting_duplicate", "rows": [["A", 1000], ["A", 2000]], "error": "ValueError"},
    {"id": "negative", "rows": [["A", -1]], "error": "ValueError"},
    {"id": "fractional_cent", "rows": [["A", 1.5]], "error": "ValueError"},
    {"id": "large_integer", "rows": [["A", 10**18], ["A", 10**18]], "value": 10**18},
]
RUNNER = '''import json, sys
from ledger import total_cents
results = []
for case in json.load(open(sys.argv[1])):
    try:
        value = total_cents(case["rows"])
        ok = "value" in case and value == case["value"]
        actual = {"value": value}
    except Exception as exc:
        actual = {"error": type(exc).__name__}
        ok = case.get("error") == type(exc).__name__
    results.append({"id": case["id"], "pass": ok, "actual": actual})
print(json.dumps(results))
'''


def digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


SUITE_DIGEST = digest(json.dumps(CASES, sort_keys=True) + RUNNER)
TRUSTED_FIXTURES = {digest(x) for x in (BASELINE, CORRECT, REGRESSION)}


def run_fixture(source: str) -> dict:
    if digest(source) not in TRUSTED_FIXTURES:
        raise ValueError("UNTRUSTED_SOURCE_REQUIRES_REAL_SANDBOX")
    start = time.perf_counter()
    with tempfile.TemporaryDirectory(prefix="hackathon-fixture-") as name:
        root = Path(name)
        (root / "ledger.py").write_text(source)
        (root / "cases.json").write_text(json.dumps(CASES))
        (root / "runner.py").write_text(RUNNER)
        proc = subprocess.run(
            [sys.executable, "-E", "-s", str(root / "runner.py"), str(root / "cases.json")],
            cwd=root, env={"PATH": os.defpath}, capture_output=True, text=True, timeout=5,
        )
        if proc.returncode:
            return {"status": "EXECUTION_FAILED", "returncode": proc.returncode,
                    "stderr": proc.stderr, "elapsed_ms": (time.perf_counter() - start) * 1000}
        results = json.loads(proc.stdout)
    return {"status": "EXECUTED", "source_sha256": digest(source),
            "suite_sha256": SUITE_DIGEST, "passed": sum(x["pass"] for x in results),
            "total": len(results), "cases": results,
            "elapsed_ms": (time.perf_counter() - start) * 1000}


def review_patch(patch: dict, *, expected_base: str, expected_suite: str) -> dict:
    def blocked(reason):
        return {"verdict": "BLOCK", "reason": reason, "applied": False,
                "current_source_sha256": digest(BASELINE)}
    if expected_base != digest(BASELINE):
        return blocked("STALE_BASE")
    if expected_suite != SUITE_DIGEST:
        return blocked("TEST_CONTRACT_CHANGED")
    if set(patch) != {"ledger.py"}:
        return blocked("PROTECTED_OR_UNEXPECTED_PATH")
    candidate = patch["ledger.py"]
    if not isinstance(candidate, str) or digest(candidate) not in TRUSTED_FIXTURES:
        return blocked("UNTRUSTED_SOURCE_REQUIRES_REAL_SANDBOX")
    before, after = run_fixture(BASELINE), run_fixture(candidate)
    if after.get("passed") != len(CASES) or before.get("passed") == len(CASES):
        result = blocked("REGRESSION_OR_NO_REPRODUCED_FAILURE")
        result.update(before=before, after=after, candidate_discarded=True)
        return result
    return {"verdict": "VERIFIED_FOR_HUMAN_REVIEW", "reason": "RED_TO_GREEN",
            "applied": False, "before": before, "after": after,
            "current_source_sha256": digest(BASELINE),
            "candidate_source_sha256": digest(candidate),
            "deployment_status": "NOT_DEPLOYED", "model_status": "NOT_RUN",
            "openshell_status": "NOT_RUN", "token_factory_status": "NOT_RUN"}
