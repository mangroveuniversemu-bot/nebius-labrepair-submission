"""Verify the real-run preparation boundary without executing a candidate."""
import base64
import hashlib
import json
import unittest
from pathlib import Path
from unittest.mock import patch

from labrepair.sandbox_experiment import RESPONSE_SHA256, prepare_experiment, prepare_request
from labrepair.scientific_workflow import SOURCE_PINS


class SandboxExperimentTests(unittest.TestCase):
    def test_preparation_is_data_only_and_preserves_tests_across_cases(self):
        with patch('subprocess.run',side_effect=AssertionError('host execution forbidden')):
            pack,raw,script=prepare_experiment()
        self.assertEqual(json.loads(raw),pack)
        self.assertEqual(pack['model_response_sha256'],RESPONSE_SHA256)
        self.assertEqual([c['expected_exit_code'] for c in pack['cases']],[1,0,1])
        for case in pack['cases']:
            for name in ('counts.json','test_analysis.py'):
                self.assertEqual(case['sha256'][name],SOURCE_PINS[name])
        self.assertNotEqual(pack['cases'][0]['sha256']['analysis.py'],pack['cases'][1]['sha256']['analysis.py'])
        self.assertIn(b"GUEST_NETWORK_NOT_DISABLED",script)

    def test_changed_model_receipt_cannot_become_a_runtime_input(self):
        with patch.object(Path,'read_bytes',return_value=b'{"forged":true}'):
            with self.assertRaisesRegex(ValueError,'OBSERVED_MODEL_RESPONSE_CHANGED'):
                prepare_experiment()

    def test_only_an_immutable_image_and_bounded_disposable_run_are_prepared(self):
        request,manifest=prepare_request('12345678-9abc-baba-deda-0123456789ab')
        self.assertTrue(request['disposable'])
        self.assertFalse(request['networking']['enabled'])
        self.assertFalse(request['preserve_env'])
        self.assertEqual(request['timeout'],30)
        self.assertEqual(set(request['env']),{'PATH'})
        self.assertEqual(request['resources_limits'],{'max_layer_bytes':16777216})
        script=base64.b64decode(request['stdin']['value'],validate=True)
        self.assertEqual(hashlib.sha256(script).hexdigest(),manifest['script_sha256'])
        self.assertEqual(manifest['host_candidate_execution'],'NOT_RUN')
        with self.assertRaises(ValueError):
            prepare_request('tag:python:latest')


if __name__=='__main__':unittest.main()
