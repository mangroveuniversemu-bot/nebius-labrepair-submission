"""Verify the scientific handover without pretending to repair code."""

import unittest

from labrepair.paths import enable_reviewed_source
from labrepair.preflight import inspect_environment
from labrepair.replay import CASES, EXPECTED, replay_case


class DomainBridgeTests(unittest.TestCase):
    def test_six_registered_verdicts(self):
        for case in CASES:
            with self.subTest(case=case):
                result = replay_case(case)
                self.assertEqual(result["verdict"], EXPECTED[case])
                self.assertTrue(result["certificate_checksum_valid"])
                self.assertTrue(result["inputs_unchanged"])

    def test_maya_preserves_disputed_claim(self):
        result = replay_case("maya")
        self.assertEqual(result["claimed_s"], 2.61)
        self.assertAlmostEqual(result["replayed_s"], 1.9625, places=9)
        self.assertEqual(result["verdict"], "BLOCK")
        self.assertEqual(
            result["root_cause_full_matches"], ["no_channel_correction:BLK-02"]
        )

    def test_human_boundary_does_not_recommend(self):
        result = replay_case("human_decision")
        self.assertEqual(result["verdict"], "HUMAN_DECISION")
        self.assertIsNone(result["human_recommendation"])

    def test_unknown_or_traversing_case_rejected(self):
        for case in ("../../private", "C:/Users/user", "maya/../clean", ""):
            with self.subTest(case=case), self.assertRaises(ValueError):
                replay_case(case)

    def test_no_fake_live_or_repair_claim(self):
        result = replay_case("maya")
        for key in ("model", "code_repair", "sandbox"):
            self.assertEqual(result[key], "NOT_RUN")
        self.assertFalse(result["checksum_is_authenticated_signature"])
        self.assertTrue(result["limitations"])

    def test_preflight_has_no_secret_or_network(self):
        result = inspect_environment()
        self.assertEqual(result["network_requests"], 0)
        self.assertFalse(result["credentials_read_from_files"])
        self.assertFalse(result["live_configuration_enabled"])
        self.assertNotIn("NEBIUS_API_KEY", result)

    def test_same_total_can_hide_wrong_per_pair_evidence(self):
        source = enable_reviewed_source()
        from tools.artifact_reader import read_package
        from tools.root_cause import find_root_cause

        package = read_package(source / "examples" / "maya_case" / "inputs")
        report = find_root_cause(package.counts, package.convention, package.claim)
        self.assertGreater(len(report.value_matches), 1)
        self.assertEqual(report.full_matches, ("no_channel_correction:BLK-02",))
        wrong = next(
            candidate
            for candidate in report.candidates
            if candidate.deviation.deviation_id == "flip_term_sign:a_bp"
        )
        self.assertTrue(wrong.matches_value)
        self.assertFalse(wrong.matches_per_pair)

    def test_missing_pair_evidence_preserves_ambiguity(self):
        source = enable_reviewed_source()
        from tools.artifact_reader import read_package
        from tools.root_cause import find_root_cause

        package = read_package(source / "examples" / "maya_case" / "inputs")
        claim = package.claim.model_copy(update={"per_pair_correlation": None})
        report = find_root_cause(package.counts, package.convention, claim)
        self.assertGreater(len(report.full_matches), 1)
        self.assertIsNone(report.identified)

    def test_analysis_program_is_missing_not_invented(self):
        source = enable_reviewed_source()
        from tools.artifact_reader import read_package

        package = read_package(source / "examples" / "maya_case" / "inputs")
        self.assertIsNone(package.claim.analysis_script_sha256)
        self.assertFalse(
            (
                source
                / "examples"
                / "maya_case"
                / "inputs"
                / package.claim.analysis_script
            ).exists()
        )


if __name__ == "__main__":
    unittest.main()
