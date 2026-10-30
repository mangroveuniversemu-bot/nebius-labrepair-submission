"""V3 policy and crash-conservative consumption; entirely synthetic/offline."""
import copy
import json
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

from labrepair.provider_envelope import prepare_request
from labrepair.provider_admission import evaluate_admission, bounded_config_valid
from labrepair.offline_exchange import FixtureSession, HTTPFixture
from test_provider_admission import NOW, synthetic_evidence


class V3BoundedGateTests(unittest.TestCase):
    def setUp(self):
        self.draft = prepare_request()
        self.claims = synthetic_evidence(self.draft)

    def evaluate(self, claims=None, **kwargs):
        return evaluate_admission(self.draft, json.dumps(
            self.claims if claims is None else claims).encode(), now=NOW, **kwargs)

    def test_positive_synthetic_policy_never_grants_runtime(self):
        with patch('socket.socket', side_effect=AssertionError('NO_NETWORK')):
            result = self.evaluate()
        self.assertEqual(result['policy_evaluation'], 'CLAIMS_SATISFY_POLICY')
        self.assertEqual(result['claimed_request_cost_upper_bound_usd'], '0.000128')
        self.assertEqual(result['runtime_admission'], 'BLOCKED')
        self.assertEqual(result['model'], 'NOT_RUN')
        self.assertEqual(result['actual_network_requests'], 0)
        body = json.loads(self.draft.body)
        self.assertEqual(body['max_completion_tokens'], 256)
        self.assertNotIn('max_tokens', body)
        self.assertTrue(bounded_config_valid())

    def test_input_reasoning_and_cost_caps_fail_closed(self):
        cases = [
            ('max_input_tokens', 513, 'VERIFIED_PRICING_OR_REQUEST_BOUND_MISSING'),
            ('max_output_tokens', 257, 'VERIFIED_PRICING_OR_REQUEST_BOUND_MISSING'),
            ('max_requests', 2, 'VERIFIED_PRICING_OR_REQUEST_BOUND_MISSING'),
            ('entire_request_token_bound_verified', False, 'VERIFIED_PRICING_OR_REQUEST_BOUND_MISSING'),
            ('completion_includes_reasoning_verified', False, 'VERIFIED_PRICING_OR_REQUEST_BOUND_MISSING'),
            ('input_usd_per_million_tokens', '20', 'CREDIT_COST_EXCEEDS_ONE_CENT'),
        ]
        for field, value, reason in cases:
            with self.subTest(field=field):
                claims = copy.deepcopy(self.claims)
                claims['pricing'][field] = value
                result = self.evaluate(claims)
                self.assertIn(reason, result['policy_reasons'])
                self.assertEqual(result['actual_network_requests'], 0)

    def test_exact_one_cent_boundary(self):
        self.claims['pricing']['input_usd_per_million_tokens'] = '0'
        for rate, expected in [('39.0625', 'CLAIMS_SATISFY_POLICY'),
                               ('39.062500000001', 'BLOCKED')]:
            self.claims['pricing']['output_usd_per_million_tokens'] = rate
            self.assertEqual(self.evaluate()['policy_evaluation'], expected)

    def test_config_cannot_relax_any_limit_or_enable_live(self):
        config_path = Path('config/providers.json')
        original = json.loads(config_path.read_text())
        for key, value in [('max_requests', 2), ('max_input_tokens', 513),
                           ('max_completion_tokens', 257), ('sdk_max_retries', 1),
                           ('timeout_seconds', None), ('max_credit_cost_usd', '0.02'),
                           ('dispatch_enabled', True), ('max_requests', True)]:
            with self.subTest(key=key):
                data = copy.deepcopy(original)
                data['bounded_test_policy'][key] = value
                with patch('pathlib.Path.read_text', return_value=json.dumps(data)):
                    self.assertEqual(self.evaluate()['policy_reasons'],
                                     ['BOUNDED_RUNTIME_CONFIG_INVALID'])

    def test_missing_fee_permission_and_unknown_dispatch_do_not_send(self):
        with patch('socket.socket', side_effect=AssertionError('NO_NETWORK')):
            self.assertIn('ADMISSION_EVIDENCE_MISSING',
                          evaluate_admission(self.draft)['policy_reasons'])
            for section, key in [('cash_controls', 'provider_hard_stop'),
                                 ('permissions', 'credential_use_approved')]:
                claims = copy.deepcopy(self.claims)
                claims[section][key] = False
                self.assertEqual(self.evaluate(claims)['policy_evaluation'], 'BLOCKED')
            for state in ['RESERVED', 'SENT', 'DISPATCH_UNKNOWN', 'COMPLETE', None]:
                result = self.evaluate(dispatch_state=state)
                self.assertEqual(result['policy_reasons'],
                                 ['DISPATCH_ALREADY_RESERVED_SENT_OR_UNKNOWN'])
                self.assertEqual(result['actual_network_requests'], 0)

    def test_durable_fixture_prevents_new_session_retry_after_timeout(self):
        with tempfile.TemporaryDirectory() as root:
            journal = Path(root) / 'single-experiment'
            first = FixtureSession(journal).rehearse(self.draft, HTTPFixture(failure='TIMEOUT'))
            self.assertEqual(first['fixture_exchanges_this_call'], 1)
            self.assertEqual(json.loads((journal / 'intent.json').read_text())['state'],
                             'DISPATCH_UNKNOWN')
            again = FixtureSession(journal).rehearse(self.draft, HTTPFixture(status_code=200))
            self.assertEqual(again['fixture_exchanges_this_call'], 0)
            self.assertEqual(again['reasons'], ['DURABLE_FIXTURE_RESERVATION_UNAVAILABLE'])
            self.assertEqual(again['actual_network_requests'], 0)

    def test_empty_corrupt_and_symlink_journal_never_reuse(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            prior = root / 'prior'
            prior.mkdir()
            for content in [None, '{bad json', '{"state":"DISPATCH_UNKNOWN"}']:
                if content is not None:
                    (prior / 'intent.json').write_text(content)
                result = FixtureSession(prior).rehearse(self.draft, HTTPFixture(failure='TIMEOUT'))
                self.assertEqual(result['fixture_exchanges_this_call'], 0)
            link = root / 'alias'
            link.symlink_to(prior, target_is_directory=True)
            result = FixtureSession(link).rehearse(self.draft, HTTPFixture(failure='TIMEOUT'))
            self.assertEqual(result['fixture_exchanges_this_call'], 0)

    def test_two_sessions_compete_for_one_durable_reservation(self):
        with tempfile.TemporaryDirectory() as root:
            journal = Path(root) / 'experiment'
            def consume(_):
                return FixtureSession(journal).rehearse(
                    self.draft, HTTPFixture(failure='TIMEOUT'))
            with ThreadPoolExecutor(max_workers=2) as pool:
                results = list(pool.map(consume, range(2)))
            self.assertEqual(sum(r['fixture_exchanges_this_call'] for r in results), 1)
            self.assertTrue(all(r['actual_network_requests'] == 0 for r in results))

    def test_archive_format_cannot_enter_new_admission(self):
        archived = prepare_request(_archived_replay=True)
        self.assertIn('max_tokens', json.loads(archived.body))
        result = evaluate_admission(archived, json.dumps(self.claims).encode(), now=NOW)
        self.assertEqual(result['policy_reasons'], ['REQUEST_BINDING_MISMATCH'])


if __name__ == '__main__':
    unittest.main()
