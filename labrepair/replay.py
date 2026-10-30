"""Run the real deterministic baseline without model or candidate execution."""

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from labrepair.paths import ROOT, enable_reviewed_source

CASES = {
    "maya": "maya_case",
    "clean": "adversarial/case_e_clean_pass",
    "missing_evidence": "adversarial/case_c_missing_evidence",
    "human_decision": "adversarial/case_d_human_decision",
    "stale": "adversarial/case_a_stale_artifact",
    "injection": "adversarial/case_g_prompt_injection",
}
EXPECTED = {
    "maya": "BLOCK",
    "clean": "ALLOW",
    "missing_evidence": "REVIEW",
    "human_decision": "HUMAN_DECISION",
    "stale": "BLOCK",
    "injection": "BLOCK",
}


def digest_tree(root: Path) -> dict[str, str]:
    return {
        item.relative_to(root).as_posix(): hashlib.sha256(item.read_bytes()).hexdigest()
        for item in sorted(root.rglob("*"))
        if item.is_file()
    }


def replay_case(case: str) -> dict:
    if case not in CASES:
        raise ValueError("unknown_bundled_case")
    source = enable_reviewed_source()
    from agent.researchops_agent import verify_package
    from evidence.certificate import verify_signature

    inputs = source / "examples" / CASES[case] / "inputs"
    before = digest_tree(inputs)
    run = verify_package(inputs)
    after = digest_tree(inputs)
    if before != after:
        raise RuntimeError("bundled_input_changed")
    assessment = run.assessment
    replay = assessment.replay
    root_cause = assessment.root_cause
    return {
        "case": case,
        "data_origin": "bundled_synthetic_fixture",
        "verdict": run.card.verdict.value,
        "expected_verdict": EXPECTED[case],
        "matches_expected": run.card.verdict.value == EXPECTED[case],
        "rule": run.card.fired_rule,
        "claim_state": run.card.claim_state.value,
        "physical_interpretation": run.card.physical_interpretation.value,
        "claimed_s": assessment.package.claim.value,
        "replayed_s": replay.registered.s_value if replay else None,
        "sigma_s": replay.registered.sigma_s if replay else None,
        "root_cause_full_matches": list(root_cause.full_matches) if root_cause else [],
        "human_recommendation": (
            run.card.escalation.recommended_option_id if run.card.escalation else None
        ),
        "certificate_checksum_valid": verify_signature(run.certificate),
        "checksum_is_authenticated_signature": False,
        "inputs_unchanged": True,
        "input_sha256": before,
        "limitations": list(run.certificate.limitations),
        "model": "NOT_RUN",
        "code_repair": "NOT_RUN",
        "sandbox": "NOT_RUN",
    }


def main() -> int:
    cases = [replay_case(case) for case in CASES]
    report = {
        "run_utc": datetime.now(timezone.utc).isoformat(),
        "mode": "actual_local_deterministic_execution",
        "source_commit": "c9595a6e0d7cb15d28755624eb9baa7695038ef5",
        "cases": cases,
        "all_expected_verdicts_match": all(case["matches_expected"] for case in cases),
        "live_inference": "NOT_RUN",
        "usage": "UNKNOWN_NOT_ZERO",
    }
    destination = ROOT / "evidence" / "domain_baseline.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "mode": report["mode"],
                "cases": [
                    {
                        "case": case["case"],
                        "verdict": case["verdict"],
                        "replayed_s": case["replayed_s"],
                    }
                    for case in cases
                ],
                "all_match": report["all_expected_verdicts_match"],
                "live": "NOT_RUN",
                "output": "evidence/domain_baseline.json",
            },
            ensure_ascii=False,
        )
    )
    return 0 if report["all_expected_verdicts_match"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
