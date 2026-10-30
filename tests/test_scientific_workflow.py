"""Product acceptance and adversarial controls for the new scientific fixture."""

import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from labrepair.scientific_workflow import (
    FIXTURE_ROOT, SOURCE_PINS, ScienceReviewError, decision_record, encode,
    load_fixture, make_proposal, review_proposal, run_scenario, verify_scenarios,
)


class ScientificWorkflowTests(unittest.TestCase):
    def test_channel_repair_matches_every_pair_but_preserves_original_claim(self):
        result = run_scenario("channel-fix")
        self.assertEqual(result["local_result"], "LOCAL_SEMANTIC_MATCH")
        self.assertAlmostEqual(result["baseline_s"], 0.1)
        self.assertEqual(result["registered_s"], 2.6)
        self.assertEqual(result["candidate_s"], 2.6)
        self.assertEqual(result["claimed_s"], 3.4)
        self.assertTrue(result["per_pair_match"])
        self.assertEqual(result["original_claim"]["claim_state"], "NOT_REPRODUCED")
        self.assertEqual(result["original_claim_sha256"], result["original_claim_after_sha256"])
        self.assertEqual(result["candidate_execution"], "NOT_RUN")
        self.assertEqual(result["runtime_admission"], "BLOCKED")

    def test_same_total_does_not_hide_wrong_pair_evidence(self):
        result = run_scenario("same-total")
        self.assertEqual(result["candidate_s"], result["registered_s"])
        self.assertTrue(result["total_only_match"])
        self.assertFalse(result["per_pair_match"])
        self.assertEqual(result["local_result"], "REJECTED")
        self.assertIn("PER_PAIR_EVIDENCE_MISMATCH", result["reasons"])

    def test_protected_test_change_is_refused_before_semantic_evaluation(self):
        result = run_scenario("protected-test")
        self.assertEqual(result["local_result"], "REJECTED")
        self.assertIn("PROTECTED_FILE_CHANGE", result["reasons"])
        self.assertIsNone(result["candidate_pairs"])
        self.assertEqual(result["changes"], [])

    def test_stale_binding_is_refused(self):
        self.assertIn("STALE_OR_WRONG_SOURCE", run_scenario("stale-source")["reasons"])

    def test_injected_code_never_reaches_a_host_executor(self):
        with patch("os.system", side_effect=AssertionError("must not execute")):
            result = run_scenario("injected-code")
        self.assertEqual(result["local_result"], "REJECTED")
        self.assertIn("CANDIDATE_AST_SHAPE_NOT_PERMITTED", result["reasons"])

    def test_missing_pair_requests_evidence_instead_of_guessing(self):
        result = run_scenario("missing-pair")
        self.assertEqual(result["local_result"], "REVIEW")
        self.assertIn("MISSING_PAIR_EVIDENCE", result["reasons"])
        self.assertIsNone(result["candidate_pairs"])

    def test_all_curated_cases_are_replayable_and_do_not_read_provider_secrets(self):
        with patch("os.getenv", side_effect=AssertionError("no secrets")):
            report = verify_scenarios()
        self.assertTrue(report["success"])
        self.assertEqual(report["curated_scenarios"], 6)
        self.assertEqual(report["naive_total_only_false_accepts"], 1)
        self.assertEqual(report["full_pair_checker_false_accepts_in_this_fixed_set"], 0)
        for result in report["receipts"]:
            self.assertFalse(result["source_written"])
            self.assertEqual(result["network_requests"], 0)
            self.assertEqual(result["nebius_generation"], "NOT_RUN")
        self.assertEqual(run_scenario("channel-fix"), run_scenario("channel-fix"))

    def test_review_intent_cannot_execute_pay_or_promote_the_claim(self):
        result = run_scenario("channel-fix")
        for choice in ("hold-for-evidence", "request-isolated-rerun"):
            decision = decision_record(result, choice)
            for key in ("executes_candidate", "authorizes_payment", "changes_scientific_claim"):
                self.assertFalse(decision[key])
        with self.assertRaises(ScienceReviewError):
            decision_record(result, "approve-claim")
        result["receipt_sha256"] = "0" * 64
        with self.assertRaises(ScienceReviewError):
            decision_record(result, "hold-for-evidence")

    def test_changed_source_or_protected_counts_are_not_re_pinned(self):
        files, _, contract = load_fixture()
        raw = encode(make_proposal("channel-fix", files, contract))
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for name in SOURCE_PINS:
                shutil.copyfile(FIXTURE_ROOT / name, root / name)
            (root / "counts.json").write_text("{}")
            with self.assertRaisesRegex(ScienceReviewError, "FIXTURE_SOURCE_CHANGED"):
                review_proposal(raw, root=root)

    def test_function_body_changes_duplicate_keys_and_nan_offsets_fail_closed(self):
        files, _, contract = load_fixture()
        proposal = make_proposal("channel-fix", files, contract)
        replacement = proposal["replacements"][0]
        for source in (
            replacement["after_utf8"].replace("sum(row)", "1"),
            replacement["after_utf8"].replace("(0, 0, 0, 0)", "(1e999, 0, 0, 0)"),
            replacement["after_utf8"] + "\nraise RuntimeError()\n",
        ):
            modified = json.loads(json.dumps(proposal))
            modified["replacements"][0]["after_utf8"] = source
            result = review_proposal(encode(modified))
            self.assertEqual(result["local_result"], "REJECTED")
            self.assertIsNone(result["candidate_pairs"])
        duplicate = encode(proposal).replace(b'{"policy_sha256":', b'{"policy_sha256":"x","policy_sha256":', 1)
        self.assertEqual(review_proposal(duplicate)["local_result"], "REJECTED")


if __name__ == "__main__":
    unittest.main()
