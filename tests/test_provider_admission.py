"""Synthetic provider/cost admission cases. No billing/account evidence is real."""

import copy
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from labrepair.candidate_review import canonical_digest, digest
from labrepair.offline_exchange import live_blocked_preview, main
from labrepair.provider_admission import (
    MAX_EVIDENCE_BYTES, PROVIDER, SCHEMA, SECTION_FIELDS, evaluate_admission,
)
from labrepair.provider_envelope import ENDPOINT, RequestDraft, encoded, prepare_request

NOW = datetime(2026, 10, 11, 18, 0, tzinfo=timezone.utc)


def synthetic_evidence(draft):
    """Fixed synthetic values; never current provider prices or verified access."""
    scope = {
        "provider": PROVIDER,
        "endpoint": ENDPOINT,
        "model_id": draft.model_id,
        "request_body_sha256": digest(draft.body),
        "account_scope_sha256": digest(b"SYNTHETIC_ACCOUNT_NOT_REAL"),
    }
    result = {
        "schema": SCHEMA,
        "evidence_kind": "SYNTHETIC_FIXTURE",
        "scope": scope,
        "checked_at_utc": "2026-10-11T17:59:00Z",
        "expires_at_utc": "2026-10-11T18:09:00Z",
        "pricing": {
            "verified": True,
            "currency": "USD",
            "input_usd_per_million_tokens": "0.10",
            "output_usd_per_million_tokens": "0.30",
            "input_token_bound_verified": True,
            "max_input_tokens": 512,
            "max_output_tokens": 256,
            "max_requests": 1,
            "all_fees_included": True,
            "entire_request_token_bound_verified": True,
            "completion_includes_reasoning_verified": True,
        },
        "credits": {
            "verified": True, "currency": "USD", "remaining_usd": "25",
            "covers_this_request": True,
        },
        "cash_controls": {
            "verified": True, "currency": "USD", "max_actual_cash_usd": "0",
            "provider_hard_stop": True, "fail_closed_on_credit_exhaustion": True,
            "automatic_top_up": False, "overage_charging": False,
            "pay_as_you_go": False,
        },
        "permissions": {
            "credential_use_approved": True, "model_access_verified": True,
            "schema_support_verified": True, "isolated_backend_verified": True,
        },
    }
    for name in SECTION_FIELDS:
        result[name]["scope_sha256"] = canonical_digest(scope)
        result[name]["source_sha256"] = digest(("SYNTHETIC_" + name).encode())
    return result


class ProviderAdmissionTests(unittest.TestCase):
    def setUp(self):
        self.draft = prepare_request()
        self.evidence = synthetic_evidence(self.draft)

    def review(self, evidence=None, now=NOW):
        return evaluate_admission(
            self.draft, encoded(self.evidence if evidence is None else evidence), now=now
        )

    def assert_policy_blocked(self, evidence, reason=None):
        result = self.review(evidence)
        self.assertEqual(result["policy_evaluation"], "BLOCKED")
        self.assertEqual(result["runtime_admission"], "BLOCKED")
        if reason:
            self.assertIn(reason, result["policy_reasons"])
        return result

    def test_complete_synthetic_claims_pass_policy_but_never_enable_runtime(self):
        result = self.review()
        self.assertEqual(result["policy_evaluation"], "CLAIMS_SATISFY_POLICY")
        self.assertEqual(result["policy_reasons"], [])
        self.assertEqual(result["claimed_request_cost_upper_bound_usd"], "0.000128")
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(result["runtime_admission"], "BLOCKED")
        self.assertEqual(result["maximum_authorized_actual_cash_usd"], "0")
        self.assertEqual(result["actual_provider_cost"], "unknown")
        self.assertEqual(result["actual_provider_latency"], "unknown")
        self.assertEqual(result["actual_provider_usage"], "unknown")
        self.assertEqual(result["model"], "NOT_RUN")

    def test_operator_assertions_are_not_authenticated_permissions(self):
        self.evidence["evidence_kind"] = "OPERATOR_ASSERTION"
        result = self.review()
        self.assertEqual(result["policy_evaluation"], "CLAIMS_SATISFY_POLICY")
        self.assertIn("INDEPENDENT_ACCOUNT_EVIDENCE_NOT_AUTHENTICATED", result["runtime_reasons"])
        self.assertEqual(result["runtime_admission"], "BLOCKED")

    def test_missing_and_wrong_type_evidence_fail_closed(self):
        for raw, reason in (
            (None, "ADMISSION_EVIDENCE_MISSING"),
            ("{}", "INVALID_ADMISSION_EVIDENCE_TYPE"),
            (b"x" * (MAX_EVIDENCE_BYTES + 1), "ADMISSION_EVIDENCE_TOO_LARGE"),
        ):
            with self.subTest(reason=reason):
                result = evaluate_admission(self.draft, raw, now=NOW)
                self.assertEqual(result["policy_reasons"], [reason])
                self.assertIsNone(result["evidence_sha256"])

    def test_malformed_duplicate_nonfinite_and_deep_json_are_rejected(self):
        for raw in (b"\xff", b'{"schema":1,"schema":2}', b"NaN", b"Infinity"):
            with self.subTest(raw_prefix=raw[:20]):
                result = evaluate_admission(self.draft, raw, now=NOW)
                self.assertEqual(result["policy_reasons"], ["INVALID_ADMISSION_EVIDENCE_JSON"])
        result = evaluate_admission(self.draft, b"[" * 2000 + b"]" * 2000, now=NOW)
        # A valid deeply nested array may parse depending on Python's recursion
        # limit; either parsing or the strict top-level schema must block it.
        self.assertEqual(result["policy_evaluation"], "BLOCKED")
        self.assertIn(result["policy_reasons"][0],
                      ("INVALID_ADMISSION_EVIDENCE_JSON", "INVALID_ADMISSION_EVIDENCE_SCHEMA"))

    def test_missing_and_unexpected_fields_in_every_section_are_rejected(self):
        for section in (None, "scope", *SECTION_FIELDS):
            for change in ("missing", "extra"):
                with self.subTest(section=section, change=change):
                    data = copy.deepcopy(self.evidence)
                    target = data if section is None else data[section]
                    if change == "missing":
                        target.pop(next(iter(target)))
                    else:
                        target["credential"] = "SYNTHETIC_MUST_NOT_LEAK"
                    result = self.assert_policy_blocked(data, "INVALID_ADMISSION_EVIDENCE_SCHEMA")
                    self.assertNotIn("SYNTHETIC_MUST_NOT_LEAK", json.dumps(result))
        for value in (None, [], {}, "unknown"):
            self.assert_policy_blocked(value if value is not None else {},
                                       "INVALID_ADMISSION_EVIDENCE_SCHEMA")

    def test_non_utf8_json_encodings_cannot_satisfy_policy(self):
        text = json.dumps(self.evidence)
        for encoding in ("utf-16", "utf-16-le", "utf-16-be", "utf-32",
                         "utf-32-le", "utf-32-be"):
            with self.subTest(encoding=encoding):
                result = evaluate_admission(self.draft, text.encode(encoding), now=NOW)
                self.assertEqual(result["policy_reasons"], ["INVALID_ADMISSION_EVIDENCE_JSON"])
                self.assertEqual(result["runtime_admission"], "BLOCKED")

    def test_exact_provider_model_request_and_account_scope_are_required(self):
        for field, value in (
            ("provider", "another_provider"), ("endpoint", "https://other.invalid"),
            ("model_id", "nvidia/another"), ("request_body_sha256", "0" * 64),
            ("account_scope_sha256", "unknown"),
        ):
            with self.subTest(field=field):
                data = copy.deepcopy(self.evidence)
                data["scope"][field] = value
                self.assert_policy_blocked(data, "ADMISSION_SCOPE_MISMATCH")

    def test_each_section_is_bound_to_the_same_account_and_request(self):
        for name in SECTION_FIELDS:
            for field, value in (("scope_sha256", "0" * 64), ("source_sha256", "unknown")):
                with self.subTest(section=name, field=field):
                    data = copy.deepcopy(self.evidence)
                    data[name][field] = value
                    self.assert_policy_blocked(data, "SECTION_EVIDENCE_BINDING_MISMATCH")
        data = copy.deepcopy(self.evidence)
        data["scope"]["account_scope_sha256"] = digest(b"OTHER_SYNTHETIC_ACCOUNT")
        self.assert_policy_blocked(data, "SECTION_EVIDENCE_BINDING_MISMATCH")

    def test_stale_future_expired_and_long_lived_evidence_fail_closed(self):
        for now in (NOW - timedelta(minutes=2), NOW + timedelta(minutes=9)):
            self.assertEqual(self.review(now=now)["policy_reasons"],
                             ["STALE_OR_FUTURE_ADMISSION_EVIDENCE"])
        data = copy.deepcopy(self.evidence)
        data["expires_at_utc"] = "2026-10-11T19:00:00Z"
        self.assert_policy_blocked(data, "STALE_OR_FUTURE_ADMISSION_EVIDENCE")
        for value in (None, "2026-10-11T18:09:00", "2026-02-31T18:09:00Z"):
            data["expires_at_utc"] = value
            self.assert_policy_blocked(data, "INVALID_EVIDENCE_TIME")
        self.assertEqual(self.review(now=NOW.replace(tzinfo=None))["policy_reasons"],
                         ["INVALID_EVIDENCE_TIME"])

    def test_unknown_pricing_unbounded_input_fees_retries_and_output_are_blocked(self):
        cases = {
            "verified": [False, None, 1, "true"], "currency": ["EUR", None],
            "input_token_bound_verified": [False, None, 1],
            "all_fees_included": [False, None, 1],
            "max_input_tokens": [0, -1, True, 1.5, 1_000_001, "2000"],
            "max_output_tokens": [None, True, 1025, 1023],
            "max_requests": [None, True, 0, 2],
        }
        for field, values in cases.items():
            for value in values:
                with self.subTest(field=field, value=value):
                    data = copy.deepcopy(self.evidence)
                    data["pricing"][field] = value
                    self.assert_policy_blocked(data, "VERIFIED_PRICING_OR_REQUEST_BOUND_MISSING")

    def test_money_requires_bounded_nonnegative_decimal_strings(self):
        for section, field, reason in (
            ("pricing", "input_usd_per_million_tokens", "VERIFIED_PRICING_OR_REQUEST_BOUND_MISSING"),
            ("pricing", "output_usd_per_million_tokens", "VERIFIED_PRICING_OR_REQUEST_BOUND_MISSING"),
            ("credits", "remaining_usd", "COVERED_FREE_CREDITS_UNVERIFIED"),
            ("cash_controls", "max_actual_cash_usd", "ENFORCEABLE_ZERO_CASH_CAP_UNVERIFIED"),
        ):
            for value in (None, True, 0, 0.1, "unknown", "-1", "1e-3", "NaN",
                          "Infinity", "+0", "00", "0.0000000000001", "1000000000", {}):
                with self.subTest(section=section, value=value):
                    data = copy.deepcopy(self.evidence)
                    data[section][field] = value
                    self.assert_policy_blocked(data, reason)

    def test_credit_balance_does_not_substitute_for_coverage_or_cash_cap(self):
        for field in ("verified", "covers_this_request"):
            for value in (False, None, 1, "true"):
                data = copy.deepcopy(self.evidence)
                data["credits"][field] = value
                self.assert_policy_blocked(data, "COVERED_FREE_CREDITS_UNVERIFIED")
        data = copy.deepcopy(self.evidence)
        data["credits"]["currency"] = "EUR"
        self.assert_policy_blocked(data, "COVERED_FREE_CREDITS_UNVERIFIED")
        for field, value in (("max_actual_cash_usd", "25"), ("verified", False),
                             ("provider_hard_stop", False), ("fail_closed_on_credit_exhaustion", False),
                             ("currency", "EUR")):
            data = copy.deepcopy(self.evidence)
            data["cash_controls"][field] = value
            self.assert_policy_blocked(data, "ENFORCEABLE_ZERO_CASH_CAP_UNVERIFIED")

    def test_insufficient_credit_fails_exact_decimal_boundary(self):
        for amount, expected in (("0.000127999999", "BLOCKED"),
                                 ("0.000128", "CLAIMS_SATISFY_POLICY")):
            data = copy.deepcopy(self.evidence)
            data["credits"]["remaining_usd"] = amount
            result = self.review(data)
            self.assertEqual(result["policy_evaluation"], expected)
            if expected == "BLOCKED":
                self.assertIn("INSUFFICIENT_COVERED_FREE_CREDITS", result["policy_reasons"])

    def test_zero_rate_does_not_bypass_independent_cash_or_permission_gates(self):
        self.evidence["pricing"]["input_usd_per_million_tokens"] = "0"
        self.evidence["pricing"]["output_usd_per_million_tokens"] = "0"
        self.evidence["credits"]["remaining_usd"] = "0"
        self.assertEqual(self.review()["policy_evaluation"], "CLAIMS_SATISFY_POLICY")
        self.evidence["cash_controls"]["automatic_top_up"] = True
        self.assert_policy_blocked(self.evidence, "AUTOMATIC_CHARGING_NOT_VERIFIED_DISABLED")

    def test_automatic_charging_must_be_explicitly_false(self):
        for field in ("automatic_top_up", "overage_charging", "pay_as_you_go"):
            for value in (True, None, 0, "false", "unknown"):
                with self.subTest(field=field, value=value):
                    data = copy.deepcopy(self.evidence)
                    data["cash_controls"][field] = value
                    self.assert_policy_blocked(data, "AUTOMATIC_CHARGING_NOT_VERIFIED_DISABLED")

    def test_credential_model_schema_and_isolation_permission_must_be_true(self):
        for field in ("credential_use_approved", "model_access_verified",
                      "schema_support_verified", "isolated_backend_verified"):
            for value in (False, None, 1, "true"):
                with self.subTest(field=field, value=value):
                    data = copy.deepcopy(self.evidence)
                    data["permissions"][field] = value
                    self.assert_policy_blocked(data)

    def test_tampered_request_and_unavailable_source_fail_before_evidence(self):
        draft = RequestDraft(self.draft.model_id, self.draft.body + b" ")
        result = evaluate_admission(draft, encoded(self.evidence), now=NOW)
        self.assertEqual(result["policy_reasons"], ["REQUEST_BINDING_MISMATCH"])
        self.assertIsNone(result["evidence_sha256"])
        self.assertEqual(evaluate_admission(None)["policy_reasons"], ["INVALID_REQUEST_DRAFT"])
        with patch("labrepair.provider_admission.prepare_request", side_effect=OSError):
            result = self.review()
        self.assertEqual(result["policy_reasons"], ["REQUEST_OR_SOURCE_UNAVAILABLE"])

    def test_no_credentials_network_provider_calls_or_input_mutation(self):
        original = copy.deepcopy(self.evidence)
        with (
            patch("socket.create_connection", side_effect=AssertionError("NO_NETWORK")),
            patch("socket.socket", side_effect=AssertionError("NO_NETWORK")),
            patch("os.getenv", side_effect=AssertionError("NO_CREDENTIAL_READ")),
            patch("os.environ.get", side_effect=AssertionError("NO_CREDENTIAL_READ")),
        ):
            result = self.review()
        self.assertEqual(self.evidence, original)
        self.assertFalse(result["credentials_accessed"])
        self.assertEqual(result["actual_network_requests"], 0)

    def test_existing_live_preview_includes_gate_and_cannot_open(self):
        result = live_blocked_preview(self.draft)
        self.assertIn("ADMISSION_EVIDENCE_MISSING", result["reasons"])
        self.assertEqual(result["provider_admission"]["runtime_admission"], "BLOCKED")
        with patch("labrepair.offline_exchange.evaluate_admission",
                   wraps=lambda draft, raw: evaluate_admission(draft, raw, now=NOW)):
            result = live_blocked_preview(self.draft, encoded(self.evidence))
        self.assertEqual(result["provider_admission"]["policy_evaluation"], "CLAIMS_SATISFY_POLICY")
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(result["model"], "NOT_RUN")

    def test_cli_evidence_is_bounded_sanitized_and_always_exits_two(self):
        with tempfile.TemporaryDirectory(prefix="labrepair-admission-") as name:
            root = Path(name)
            evidence_dir = root / "evidence"
            evidence_dir.mkdir()
            fixture = evidence_dir / "claims.json"
            output = evidence_dir / "result.json"
            fixture.write_bytes(b"x" * (MAX_EVIDENCE_BYTES + 50))
            with patch("labrepair.offline_exchange.ROOT", root), patch(
                "sys.argv", ["offline_exchange", "--admission-evidence", str(fixture),
                             "--output", str(output)]
            ), patch("builtins.print"):
                self.assertEqual(main(), 2)
                receipt = json.loads(output.read_text())
                self.assertIn("ADMISSION_EVIDENCE_TOO_LARGE", receipt["reasons"])
                with self.assertRaises(SystemExit):
                    main()  # Existing evidence may never be overwritten.

    def test_cli_rejects_symlinked_evidence_root_before_read_or_write(self):
        with tempfile.TemporaryDirectory(prefix="labrepair-admission-symlink-") as name:
            base = Path(name)
            root, outside = base / "workspace", base / "outside"
            root.mkdir()
            outside.mkdir()
            (root / "evidence").symlink_to(outside, target_is_directory=True)
            output = root / "evidence" / "result.json"
            with patch("labrepair.offline_exchange.ROOT", root), patch(
                "sys.argv", ["offline_exchange", "--output", str(output)]
            ), patch("labrepair.offline_exchange.prepare_request",
                     side_effect=AssertionError("MUST_REJECT_BEFORE_REQUEST")):
                with self.assertRaises(SystemExit) as caught:
                    main()
            self.assertEqual(caught.exception.code, 2)
            self.assertEqual(list(outside.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
