"""Replay six intake cases; synthetic contracts/gates, no candidate execution."""

import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from labrepair.candidate_review import (
    FrozenContract,
    OperatorGates,
    canonical_digest,
    digest,
    review_candidate,
)


def main() -> int:
    originals = (
        ("solution.py", b"def add(a, b):\n    return a - b\n"),
        ("tests/test_solution.py", b"# Synthetic protected tests\n"),
        ("policy.json", b'{"network": "deny"}\n'),
    )
    contract = FrozenContract(
        originals, ("solution.py",), canonical_digest({"network": "deny"})
    )
    proposal = {
        "snapshot_sha256": contract.snapshot_sha256,
        "policy_sha256": contract.policy_sha256,
        "replacements": [
            {
                "path": "solution.py",
                "before_sha256": digest(originals[0][1]),
                "after_utf8": "def add(a, b):\n    return a + b\n",
            }
        ],
    }
    full_fixture_gates = OperatorGates(True, True, True)
    cases = []
    for name in (
        "reviewable_diff",
        "protected_test_change",
        "stale_snapshot",
        "wrong_policy",
        "missing_external_gates",
        "source_unavailable",
    ):
        item = copy.deepcopy(proposal)
        gates = full_fixture_gates
        trusted = contract
        if name == "protected_test_change":
            item["replacements"][0].update(
                path=originals[1][0], before_sha256=digest(originals[1][1])
            )
        elif name == "stale_snapshot":
            item["snapshot_sha256"] = "0" * 64
        elif name == "wrong_policy":
            item["policy_sha256"] = "0" * 64
        elif name == "missing_external_gates":
            gates = OperatorGates(True, False, False)
        elif name == "source_unavailable":
            trusted = None
        cases.append(
            {
                "case": name,
                "contract_and_operator_gates": "LABELED_SYNTHETIC_FIXTURES_NOT_REAL_ENTITLEMENTS",
                "result": review_candidate(json.dumps(item).encode(), trusted, gates),
            }
        )
    report = {
        "run_id": "20261003T155145Z-nebius-004",
        "demo": "Independent offline candidate intake, not the historical Q4 3-of-8 repair demo",
        "source_sha256": {path: digest(data) for path, data in originals},
        "cases": cases,
        "expected_statuses": [
            "READY_FOR_ISOLATED_TEST",
            "REJECTED",
            "REJECTED",
            "REJECTED",
            "BLOCKED",
            "BLOCKED",
        ],
        "provider": "NOT_RUN",
        "sandbox": "NOT_RUN",
        "patch_applied_or_executed": False,
        "usage": "unknown",
    }
    report["expected_statuses_match"] = [
        item["result"]["status"] for item in cases
    ] == report["expected_statuses"]
    (ROOT / "evidence" / "nebius_004_intake_demo.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "cases": len(cases),
                "expected_statuses_match": report["expected_statuses_match"],
                "provider": "NOT_RUN",
                "sandbox": "NOT_RUN",
            }
        )
    )
    return 0 if report["expected_statuses_match"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
