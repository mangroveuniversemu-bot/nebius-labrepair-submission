"""Portable offline handover adversarial checks; candidate execution stays absent."""

import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from labrepair.candidate_review import digest
from labrepair.handover import (
    MAX_BUNDLE_BYTES,
    MAX_MEMBER_BYTES,
    HandoverInvalid,
    build_bundle,
    replay_bundle,
)
from labrepair.provider_envelope import encoded
from labrepair.q4_pins import PINNED_FILES
from labrepair.q4_source import SOURCE_ROOT, SourceUnavailable, verify_import


class HandoverTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = build_bundle()

    def changed(self, name, text, rehash=True):
        value = json.loads(self.raw)
        value["members"][name] = text
        if rehash:
            value["manifest"][name] = digest(text.encode())
        return encoded(value)

    def test_roundtrip_is_stable_and_never_executes_or_approves(self):
        before = verify_import()
        self.assertEqual(build_bundle(), self.raw)
        result = replay_bundle(self.raw)
        self.assertEqual(
            result["verification"], "MATCHED_OFFLINE_REPLAY; NOT_REPAIR_APPROVAL"
        )
        self.assertEqual(result["cases"]["normal"]["status"], "BLOCKED")
        self.assertEqual(
            result["cases"]["protected-change"]["reasons"], ["PROTECTED_FILE_CHANGE"]
        )
        self.assertEqual(result["member_count"], 10)
        self.assertEqual(result["actual_provider_usage"], "unknown")
        self.assertEqual(result["candidate_execution"], "NOT_RUN")
        self.assertFalse(result["data_extracted_to_source_paths"])
        self.assertEqual(verify_import(), before)

    def test_false_approval_live_usage_and_boolean_zero_rejected_after_rehash(self):
        value = json.loads(self.raw)
        normal = json.loads(value["members"]["receipts/normal.json"])
        for key, field in (
            ("status", "ACCEPTED"),
            ("model", "LIVE"),
            ("actual_provider_usage", 0),
            ("network_requests", False),
        ):
            forged = dict(normal, **{key: field})
            raw = self.changed("receipts/normal.json", encoded(forged).decode())
            with (
                self.subTest(key=key),
                self.assertRaisesRegex(
                    HandoverInvalid, "SAVED_RECEIPT_REPLAY_MISMATCH"
                ),
            ):
                replay_bundle(raw)

    def test_protected_inputs_and_request_cannot_be_rehashed_into_trust(self):
        value = json.loads(self.raw)
        for name, reason in (
            ("frozen/runner.py.txt", "FROZEN_SOURCE_MISMATCH"),
            ("request.json", "REQUEST_BINDING_MISMATCH"),
            ("responses/normal.json.txt", "PINNED_RESPONSE_MISMATCH"),
            ("origin.json", "ORIGIN_OR_INSTRUCTIONS_CHANGED"),
        ):
            raw = self.changed(name, value["members"][name] + " ")
            with (
                self.subTest(name=name),
                self.assertRaisesRegex(HandoverInvalid, reason),
            ):
                replay_bundle(raw)

    def test_digest_failure_and_extra_path_never_extract(self):
        with self.assertRaisesRegex(HandoverInvalid, "MEMBER_DIGEST_MISMATCH"):
            replay_bundle(
                self.changed(
                    "frozen/ledger.py.txt", "raise RuntimeError('MUST_NOT_RUN')", False
                )
            )
        for name in ("../ledger.py", "C:/secret", "new.py", "frozen/LEDGER.py.txt"):
            value = json.loads(self.raw)
            value["members"][name] = "raise RuntimeError('MUST_NOT_RUN')"
            value["manifest"][name] = digest(value["members"][name].encode())
            with (
                self.subTest(name=name),
                self.assertRaisesRegex(HandoverInvalid, "UNEXPECTED_OR_MISSING_MEMBER"),
            ):
                replay_bundle(encoded(value))

    def test_limits_missing_malformed_duplicate_and_surrogates_fail_closed(self):
        for raw in (
            b"{" * 2000,
            b'{"schema_version":1,"schema_version":1}',
            b"NaN",
            b"\xff",
        ):
            with self.assertRaises(HandoverInvalid):
                replay_bundle(raw)
        with self.assertRaisesRegex(HandoverInvalid, "BUNDLE_TOO_LARGE"):
            replay_bundle(b"x" * (MAX_BUNDLE_BYTES + 1))
        with self.assertRaisesRegex(HandoverInvalid, "MEMBER_TOO_LARGE"):
            replay_bundle(self.changed("README.txt", "x" * (MAX_MEMBER_BYTES + 1)))
        value = json.loads(self.raw)
        del value["members"]["origin.json"]
        with self.assertRaisesRegex(HandoverInvalid, "UNEXPECTED_OR_MISSING_MEMBER"):
            replay_bundle(encoded(value))
        for text, reason in (
            (None, "INVALID_MEMBER_TEXT"),
            ("\ud800", "INVALID_MEMBER_ENCODING"),
        ):
            value = json.loads(self.raw)
            value["members"]["README.txt"] = text
            with self.assertRaisesRegex(HandoverInvalid, reason):
                replay_bundle(encoded(value))

    def test_changed_operator_source_fails_even_with_a_valid_bundle(self):
        with tempfile.TemporaryDirectory(prefix="nebius-handover-negative-") as tmp:
            root = Path(tmp)
            for name in PINNED_FILES:
                target = root / name
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(SOURCE_ROOT / name, target)
            (root / "tests/test_workspace_contract.py").write_bytes(
                b"raise RuntimeError('MUST_NOT_RUN')"
            )
            with self.assertRaisesRegex(
                SourceUnavailable, "SOURCE_FILE_DIGEST_MISMATCH"
            ):
                replay_bundle(self.raw, root)

    def test_changed_historical_input_cannot_be_exported(self):
        with tempfile.TemporaryDirectory(prefix="nebius-handover-origin-") as tmp:
            root = Path(tmp)
            (root / "nebius_007_request_preview.json").write_bytes(
                b'{"status":"READY"}'
            )
            with self.assertRaisesRegex(HandoverInvalid, "ORIGIN_FILE_DIGEST_MISMATCH"):
                build_bundle(root)

    def test_no_secret_read_or_absolute_path_in_portable_bundle(self):
        with patch.dict("os.environ", {
            "NEBIUS_API_KEY": "synthetic-DO-NOT-READ",
            "PRIVATE_CONTACT_EMAIL": "private-contact@example.invalid",
        }):
            raw = build_bundle()
            self.assertNotIn(b"synthetic-DO-NOT-READ", raw)
            self.assertNotIn(b"C:\\", raw)
            self.assertNotIn(b"private-contact@example.invalid", raw)
            self.assertEqual(replay_bundle(raw)["network_requests"], 0)


if __name__ == "__main__":
    unittest.main()
