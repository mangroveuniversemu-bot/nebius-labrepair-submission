"""Review UI safety/semantics. Candidate strings are data, never programs."""

import copy
import json
import unittest
from html.parser import HTMLParser

from labrepair.paths import ROOT
from labrepair.workbench import INPUTS, render_workbench


class Markup(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags = []
        self.attrs = []
        self.visible = []

    def handle_starttag(self, tag, attrs):
        self.tags.append(tag)
        self.attrs.extend(attrs)

    def handle_data(self, data):
        self.visible.append(data)


class WorkbenchTests(unittest.TestCase):
    def setUp(self):
        self.demo = json.loads(
            (ROOT / "evidence" / INPUTS["intake-receipt.json"]).read_bytes()
        )
        self.local = json.loads(
            (ROOT / "evidence" / INPUTS["local-gate-receipt.json"]).read_bytes()
        )
        self.domain = json.loads(
            (ROOT / "evidence" / INPUTS["domain-replay-receipt.json"]).read_bytes()
        )
        self.hashes = {name: "a" * 64 for name in INPUTS}

    def page(self):
        return render_workbench(self.demo, self.local, self.domain, self.hashes)

    def test_normal_page_has_six_cases_actual_block_and_separate_science(self):
        page = self.page()
        parser = Markup()
        parser.feed(page)
        self.assertEqual(parser.tags.count("details"), 6)
        for value in (
            "Actual local gate: BLOCKED",
            "NOT_RUN",
            "unknown",
            "Eligible for isolated test only",
            "Original claim: BLOCK",
            "1.9625",
            "2.61",
            "None of these cases repairs the Bell/CHSH program.",
        ):
            self.assertIn(value, page)

    def test_untrusted_diff_path_reason_and_hash_cannot_become_markup(self):
        attack = '</pre><script>fetch("https://evil.invalid")</script><img src=x onerror=alert(1)>'
        result = self.demo["cases"][0]["result"]
        result["changes"][0].update(path=attack, diff=attack, after_sha256=attack)
        result["reasons"] = [attack]
        self.hashes["intake-receipt.json"] = attack
        page = self.page()
        parser = Markup()
        parser.feed(page)
        self.assertNotIn(attack, page)
        self.assertIn("&lt;script&gt;", page)
        self.assertIn(attack, "".join(parser.visible))
        for tag in ("script", "img", "iframe", "object", "form", "input", "button"):
            self.assertNotIn(tag, parser.tags)
        self.assertFalse(any(key.startswith("on") for key, _ in parser.attrs))

    def test_download_links_are_only_fixed_receipts_and_fragment_navigation(self):
        parser = Markup()
        parser.feed(self.page())
        hrefs = [value for key, value in parser.attrs if key == "href"]
        self.assertEqual(set(hrefs), {*INPUTS, *(f"#case-{n}" for n in range(1, 7))})
        self.assertIn("script-src 'none'", self.page())
        self.assertIn("connect-src 'none'", self.page())
        self.hashes["https://evil.invalid"] = "a" * 64
        with self.assertRaises(ValueError):
            self.page()

    def test_renderer_refuses_forged_execution_or_provider_receipt(self):
        for field, value in (
            ("execution", "PASSED"),
            ("model", "NEBIUS_SUCCESS"),
            ("usage", 0),
            ("source_written", True),
            ("network_requests", 1),
            ("scientific_claim", "ALLOW"),
        ):
            with self.subTest(field=field):
                demo = copy.deepcopy(self.demo)
                demo["cases"][0]["result"][field] = value
                with self.assertRaises(ValueError):
                    render_workbench(demo, self.local, self.domain, self.hashes)

    def test_synthetic_label_and_identity_are_required(self):
        self.demo["cases"][0]["contract_and_operator_gates"] = "REAL"
        with self.assertRaises(ValueError):
            self.page()
        self.setUp()
        self.demo["cases"][0]["case"] = "unknown"
        with self.assertRaises(ValueError):
            self.page()

    def test_scientific_or_actual_gate_change_requires_reviewed_renderer(self):
        self.local["status"] = "READY_FOR_ISOLATED_TEST"
        with self.assertRaises(ValueError):
            self.page()
        self.setUp()
        self.domain["cases"][0]["verdict"] = "ALLOW"
        with self.assertRaises(ValueError):
            self.page()

    def test_stale_policy_and_missing_runtime_reasons_remain_visible(self):
        page = self.page()
        for reason in (
            "STALE_OR_WRONG_SOURCE",
            "POLICY_BINDING_MISMATCH",
            "PROTECTED_FILE_CHANGE",
            "ISOLATED_BACKEND_UNVERIFIED",
            "SPENDING_LIMIT_UNVERIFIED",
        ):
            self.assertIn(reason, page)


if __name__ == "__main__":
    unittest.main()
