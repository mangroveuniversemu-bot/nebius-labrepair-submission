"""Archived actual receipts are checked without re-running a provider or code."""
import unittest
from unittest.mock import patch

from labrepair.candidate_review import canonical_digest
from labrepair.recorded_validation import PINS, load_recorded_validation


class RecordedValidationTests(unittest.TestCase):
    def test_actual_records_preserve_expected_control_failures_and_model_pass(self):
        with patch('subprocess.run',side_effect=AssertionError('replay must not execute')):
            result=load_recorded_validation()
        self.assertEqual(result['expected_case_outcomes_observed'],3)
        self.assertEqual(result['executed_checks'],12)
        self.assertEqual([c['checks_passed'] for c in result['cases']],[2,4,3])
        self.assertTrue(result['protected_files_unchanged'])
        self.assertEqual(result['original_claim']['claim_state'],'NOT_REPRODUCED')
        self.assertEqual(result['actual_billed_currency'],'unknown')
        self.assertEqual(result['automatic_cloud_dispatch'],'DISABLED')
        checksum=result.pop('receipt_sha256')
        self.assertEqual(checksum,canonical_digest(result))

    def test_changed_evidence_is_refused_instead_of_relabeling_the_run(self):
        with patch('labrepair.recorded_validation.PINS',{name:'0'*64 for name in PINS}):
            with self.assertRaisesRegex(ValueError,'RECORDED_PROVIDER_EVIDENCE_CHANGED'):
                load_recorded_validation()
