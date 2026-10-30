"""The UI is data-only, source-bound, escaped and cannot invent approval."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from labrepair.candidate_review import digest
from labrepair.handover import HandoverInvalid, replay_bundle
from labrepair.handover_view import (
    DOMAIN_PATH,
    DOMAIN_SHA256,
    DOWNLOADS,
    _output_root,
    create_view,
    escaped,
    failure_page,
)
from labrepair.paths import ROOT
from labrepair.provider_envelope import encoded


class HandoverViewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = (ROOT / "evidence/nebius_008_handover.json").read_bytes()
        cls.domain = DOMAIN_PATH.read_bytes()

    def test_fresh_replay_exact_downloads_and_gates(self):
        files, receipt = create_view(self.raw, self.domain)
        self.assertEqual(set(files), {*DOWNLOADS, "index.html"})
        self.assertEqual(files["offline-handover.json"], self.raw)
        self.assertEqual(files["historical-domain.json"], self.domain)
        self.assertEqual(
            files["fresh-replay.json"], encoded(replay_bundle(self.raw)) + b"\n"
        )
        self.assertEqual(receipt["normal"], "BLOCKED")
        self.assertEqual(receipt["protected_change"], "REJECTED PROTECTED_FILE_CHANGE")
        self.assertEqual(receipt["actual_provider_usage"], "unknown")
        self.assertTrue(receipt["source_pins_reloaded"])
        self.assertEqual(
            receipt["download_sha256"]["historical-domain.json"], digest(self.domain)
        )
        self.assertEqual(receipt["historical_domain_original_crlf_sha256"], DOMAIN_SHA256)
        self.assertTrue(receipt["historical_domain_bytes_restoration_verified"])

    def test_page_has_no_dispatch_scripts_or_external_assets(self):
        files, _ = create_view(self.raw, self.domain)
        page = files["index.html"].decode()
        for forbidden in (
            "<script",
            "<button",
            "<form",
            "<input",
            "<iframe",
            "<img",
            "onclick=",
            "src=",
            "href='http",
            'href="http',
        ):
            self.assertNotIn(forbidden, page)
        self.assertIn("script-src &#x27;none&#x27;", page)
        self.assertIn("connect-src &#x27;none&#x27;", page)
        self.assertIn("REPLAY MATCHED ≠ REPAIR APPROVED", page)
        self.assertIn("SPENDING_LIMIT_UNVERIFIED", page)
        self.assertIn("ISOLATED_BACKEND_UNVERIFIED", page)
        self.assertIn("PROTECTED_FILE_CHANGE", page)
        self.assertIn("Latest remote match: UNVERIFIED", page)

    def test_scientific_context_separate_and_unchanged(self):
        files, receipt = create_view(self.raw, self.domain)
        page = files["index.html"].decode()
        for expected in (
            "2.61",
            "1.9625",
            "Original claim: BLOCK",
            "NOT_ESTABLISHED",
            "Saved NEBIUS-008 synthetic Maya replay",
            "does not repair or re-evaluate this Bell/CHSH claim",
        ):
            self.assertIn(expected, page)
        self.assertEqual(receipt["scientific_repair"], "NOT_RUN")
        domain = json.loads(self.domain)
        domain["cases"][0]["verdict"] = "ALLOW"
        with self.assertRaisesRegex(
            HandoverInvalid, "HISTORICAL_DOMAIN_DIGEST_MISMATCH"
        ):
            create_view(self.raw, encoded(domain))

    def test_rehashed_forged_approval_cannot_be_rendered(self):
        value = json.loads(self.raw)
        forged = json.loads(value["members"]["receipts/normal.json"])
        forged.update(status="ACCEPTED", execution="SUCCESS", actual_provider_usage=0)
        member = encoded(forged)
        value["members"]["receipts/normal.json"] = member.decode()
        value["manifest"]["receipts/normal.json"] = digest(member)
        with self.assertRaisesRegex(HandoverInvalid, "SAVED_RECEIPT_REPLAY_MISMATCH"):
            create_view(encoded(value), self.domain)

    def test_changed_request_or_source_does_not_gain_ui_authority(self):
        for name in ("request.json", "frozen/runner.py.txt"):
            with self.subTest(name=name):
                value = json.loads(self.raw)
                value["members"][name] += "\n# changed"
                value["manifest"][name] = digest(value["members"][name].encode())
                with self.assertRaises(HandoverInvalid):
                    create_view(encoded(value), self.domain)

    def test_every_text_value_is_escaped(self):
        self.assertEqual(escaped("<script>&\"'"), "&lt;script&gt;&amp;&quot;&#x27;")
        files, _ = create_view(self.raw, self.domain)
        self.assertIn(b"ValueError(&quot;invalid amount&quot;)", files["index.html"])

    def test_rejected_view_has_no_success_or_download_links(self):
        page = failure_page().decode()
        self.assertIn("Handover rejected. No repair authorized.", page)
        self.assertNotIn("href=", page)
        self.assertNotIn("REPLAY MATCHED", page)
        self.assertNotIn("<button", page)
        with self.assertRaises(HandoverInvalid):
            create_view(b'{"schema_version":1,"schema_version":1}', self.domain)

    def test_unexpected_static_file_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = root / "handover-workbench"
            output.mkdir()
            (output / "unexpected.py").write_bytes(b"never imported")
            with (
                patch("labrepair.handover_view.ROOT", root),
                self.assertRaisesRegex(HandoverInvalid, "UNEXPECTED_STATIC_OUTPUT"),
            ):
                _output_root()


if __name__ == "__main__":
    unittest.main()
