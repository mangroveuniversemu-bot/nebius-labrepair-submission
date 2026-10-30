"""Actual local HTTP-contract rehearsal tests; never real provider traffic."""

import json
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

from test_provider_envelope import response_fixture

from labrepair.offline_exchange import (
    FixtureSession,
    HTTPFixture,
    live_blocked_preview,
    parse_fixture,
)
from labrepair.provider_envelope import (
    MAX_RESPONSE_BYTES,
    RequestDraft,
    encoded,
    prepare_request,
)


class OfflineExchangeTests(unittest.TestCase):
    def setUp(self):
        self.draft = prepare_request()

    def normal(self):
        body = response_fixture()
        body["usage"] = {
            "prompt_tokens": 10,
            "completion_tokens": 20,
            "total_tokens": 30,
        }
        return body

    def review(self, body):
        return FixtureSession().rehearse(
            self.draft, HTTPFixture(200, body=encoded(body))
        )

    def test_default_live_gate_does_not_touch_network_or_credentials(self):
        with (
            patch("socket.create_connection", side_effect=AssertionError("NO_NETWORK")),
            patch.dict("os.environ", {"NEBIUS_API_KEY": "SYNTHETIC_DO_NOT_ECHO"}),
        ):
            info = live_blocked_preview(self.draft)
            receipt = self.review(self.normal())
        self.assertEqual(info["status"], "BLOCKED")
        self.assertEqual(receipt["model"], "NOT_RUN")
        self.assertEqual(receipt["actual_network_requests"], 0)
        self.assertNotIn("SYNTHETIC_DO_NOT_ECHO", json.dumps(receipt))

    def test_usage_is_fixture_only_and_normal_candidate_remains_blocked(self):
        receipt = self.review(self.normal())
        self.assertEqual(receipt["status"], "BLOCKED")
        self.assertEqual(receipt["fixture_reported_usage"]["total_tokens"], 30)
        self.assertEqual(receipt["actual_provider_usage"], "unknown")
        self.assertFalse(receipt["proposal_text_recorded"])
        self.assertFalse(receipt["source_written"])

    def test_rejected_candidate_still_retains_separate_fixture_usage(self):
        body = self.normal()
        proposal = json.loads(body["choices"][0]["message"]["content"])
        proposal["replacements"][0]["path"] = "runner.py"
        body["choices"][0]["message"]["content"] = json.dumps(proposal)
        result = self.review(body)
        self.assertEqual(result["reasons"], ["PROTECTED_FILE_CHANGE"])
        self.assertEqual(result["fixture_reported_usage"]["total_tokens"], 30)
        self.assertEqual(result["actual_provider_usage"], "unknown")

    def test_error_statuses_are_sanitized_no_retry_and_no_zero_cost_claim(self):
        for code in (301, 307, 400, 401, 403, 429, 500, 503):
            with self.subTest(code=code):
                result = FixtureSession().rehearse(
                    self.draft,
                    HTTPFixture(code, body=b"SYNTHETIC_PRIVATE_ERROR_MARKER"),
                )
                self.assertEqual(result["status"], "FAILED")
                self.assertEqual(result["automatic_retries"], 0)
                self.assertEqual(result["actual_provider_usage"], "unknown")
                self.assertNotIn("SYNTHETIC_PRIVATE_ERROR_MARKER", json.dumps(result))

    def test_failures_consume_single_session_and_cannot_retry(self):
        for failure in ("TIMEOUT", "CONNECTION", "TLS"):
            session = FixtureSession()
            first = session.rehearse(self.draft, HTTPFixture(failure=failure))
            second = session.rehearse(
                self.draft, HTTPFixture(200, body=encoded(self.normal()))
            )
            self.assertEqual(first["fixture_exchanges_this_call"], 1)
            self.assertEqual(second["fixture_exchanges_this_call"], 0)
            self.assertEqual(second["reasons"], ["FIXTURE_SESSION_ALREADY_CONSUMED"])

    def test_concurrent_calls_cannot_consume_session_twice(self):
        session = FixtureSession()
        with ThreadPoolExecutor(max_workers=4) as pool:
            results = list(
                pool.map(
                    lambda _: session.rehearse(
                        self.draft, HTTPFixture(failure="TIMEOUT")
                    ),
                    range(4),
                )
            )
        self.assertEqual(
            sum(item["fixture_exchanges_this_call"] for item in results), 1
        )

    def test_oversize_records_prefix_hash_not_a_full_response_digest(self):
        result = FixtureSession().rehearse(
            self.draft, HTTPFixture(200, body=b"x" * (MAX_RESPONSE_BYTES + 100))
        )
        self.assertEqual(result["response_read_bytes_fixture"], MAX_RESPONSE_BYTES + 1)
        self.assertEqual(result["response_sha256"], "unknown")
        self.assertIn("bounded_prefix_sha256", result)
        self.assertEqual(result["status"], "REJECTED")

    def test_content_type_malformed_and_duplicate_json_fail_closed(self):
        for fixture in (
            HTTPFixture(200, "text/html", b"<html>private</html>"),
            HTTPFixture(200, body=b'{"model":1,"model":2}'),
            HTTPFixture(200, body=b"NaN"),
            HTTPFixture(200, body=b"\xff"),
        ):
            result = FixtureSession().rehearse(self.draft, fixture)
            self.assertEqual(result["status"], "REJECTED")
            self.assertEqual(result["fixture_reported_usage"], "unknown")

    def test_protocol_refusal_usage_is_not_lost_or_promoted(self):
        body = self.normal()
        body["choices"][0]["finish_reason"] = "length"
        body["live"] = True
        body["private_extension"] = "SYNTHETIC_PRIVATE_EXTENSION"
        result = self.review(body)
        self.assertEqual(result["status"], "REJECTED")
        self.assertEqual(result["fixture_reported_usage"]["total_tokens"], 30)
        self.assertNotIn("SYNTHETIC_PRIVATE_EXTENSION", json.dumps(result))
        self.assertEqual(result["model"], "NOT_RUN")

    def test_invalid_missing_boolean_or_inconsistent_usage_remains_unknown(self):
        for usage in (
            None,
            {},
            {"prompt_tokens": True},
            {"prompt_tokens": 1, "completion_tokens": 2, "total_tokens": 4},
        ):
            body = self.normal()
            body["usage"] = usage
            self.assertEqual(self.review(body)["fixture_reported_usage"], "unknown")

    def test_tampered_request_rejected_before_fixture_consumption(self):
        session = FixtureSession()
        draft = RequestDraft(self.draft.model_id, self.draft.body + b" ")
        result = session.rehearse(draft, HTTPFixture(failure="TIMEOUT"))
        self.assertEqual(result["reasons"], ["REQUEST_BINDING_MISMATCH"])
        self.assertEqual(result["fixture_exchanges_this_call"], 0)
        good = session.rehearse(self.draft, HTTPFixture(failure="TIMEOUT"))
        self.assertEqual(good["fixture_exchanges_this_call"], 1)

    def test_fixture_format_cannot_supply_endpoint_key_or_live_permissions(self):
        normal = {
            "status_code": 200,
            "content_type": "application/json",
            "body_utf8": json.dumps(self.normal()),
        }
        self.assertTrue(parse_fixture(encoded(normal)).valid())
        for extra in ("api_key", "endpoint", "live", "spending_limit_verified"):
            invalid = {**normal, extra: "SYNTHETIC_FORGED_GRANT"}
            with self.assertRaisesRegex(ValueError, "INVALID_OFFLINE_FIXTURE"):
                parse_fixture(encoded(invalid))
        for fixture in (
            HTTPFixture(True),
            HTTPFixture(200, body="not-bytes"),
            HTTPFixture(200, failure="TIMEOUT"),
        ):
            self.assertFalse(fixture.valid())


if __name__ == "__main__":
    unittest.main()
