"""Actual pinned-source integration, with offline negative controls only."""

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from labrepair.candidate_review import OperatorGates, digest, review_candidate
from labrepair.q4_pins import PINNED_FILES, POLICY_SHA256, WORKSPACE_MANIFEST_SHA256
from labrepair.q4_source import (
    SOURCE_ROOT,
    SourceUnavailable,
    extract_constants,
    load_source,
    verify_import,
)


class Q4SourceTests(unittest.TestCase):
    def copied_source(self):
        temporary = tempfile.TemporaryDirectory(prefix="nebius-source-negative-")
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        for name in PINNED_FILES:
            target = root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(SOURCE_ROOT / name, target)
        return root

    def proposal(self, source, **changes):
        item = {
            "snapshot_sha256": source.contract.snapshot_sha256,
            "policy_sha256": source.contract.policy_sha256,
            "replacements": [
                {
                    "path": "ledger.py",
                    "before_sha256": digest(
                        dict(source.contract.originals)["ledger.py"]
                    ),
                    "after_utf8": source.correct_literal_fixture,
                }
            ],
        }
        item.update(changes)
        return item

    def review(self, source, proposal):
        return review_candidate(
            json.dumps(proposal).encode(),
            source.contract,
            OperatorGates(True, False, False),
        )

    def test_exact_three_file_contract_matches_original_digest(self):
        source = load_source()
        self.assertEqual(
            tuple(dict(source.contract.originals)),
            ("cases.json", "ledger.py", "runner.py"),
        )
        self.assertEqual(source.contract.editable_paths, ("ledger.py",))
        self.assertEqual(source.contract.policy_sha256, POLICY_SHA256)
        self.assertEqual(
            source.workspace_manifest["manifest_sha256"], WORKSPACE_MANIFEST_SHA256
        )
        self.assertEqual(
            source.contract.snapshot_sha256,
            "8cf0a003ab54e39d292cfc9371f6c7a54fc308ad981218fef0d305da82ad3d05",
        )
        self.assertEqual(
            len(json.loads(dict(source.contract.originals)["cases.json"])), 8
        )

    def test_source_integrity_is_not_latest_or_authenticated_identity(self):
        self.assertEqual(len(verify_import()), 5)
        info = load_source().provenance()
        self.assertEqual(info["latest_remote_match"], "UNVERIFIED")
        self.assertEqual(info["source_identity_authentication"], "NOT_CLAIMED")
        self.assertIn("separate from Bell/CHSH", info["fixture_domain"])

    def test_changed_implementation_fails_before_constant_extraction(self):
        root = self.copied_source()
        (root / "coding/patch_review.py").write_bytes(
            b"raise RuntimeError('MUST_NOT_RUN')"
        )
        with self.assertRaisesRegex(SourceUnavailable, "DIGEST_MISMATCH"):
            load_source(root)

    def test_changed_protected_upstream_tests_are_refused(self):
        root = self.copied_source()
        (root / "tests/test_workspace_contract.py").write_bytes(b"# weakened tests\n")
        with self.assertRaisesRegex(SourceUnavailable, "DIGEST_MISMATCH"):
            load_source(root)

    def test_missing_source_fails_closed(self):
        root = self.copied_source()
        (root / "coding/workspace_contract.py").unlink()
        with self.assertRaisesRegex(SourceUnavailable, "UNAVAILABLE"):
            load_source(root)

    def test_provenance_cannot_override_operator_pin(self):
        root = self.copied_source()
        (root / "SOURCE_ORIGIN.json").write_text(
            '{"source_verified": true}', encoding="utf-8"
        )
        (root / "coding/sandbox_adapter.py").write_bytes(b"# policy changed\n")
        with self.assertRaisesRegex(SourceUnavailable, "DIGEST_MISMATCH"):
            load_source(root)

    def test_correct_literal_diff_is_bound_but_external_execution_blocked(self):
        source = load_source()
        before = verify_import()
        result = self.review(source, self.proposal(source))
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(
            result["reasons"],
            ["ISOLATED_BACKEND_UNVERIFIED", "SPENDING_LIMIT_UNVERIFIED"],
        )
        self.assertIn("+    seen = {}", result["changes"][0]["diff"])
        self.assertEqual(result["execution"], "NOT_RUN")
        self.assertFalse(result["source_written"])
        self.assertEqual(before, verify_import())

    def test_runner_and_cases_remain_protected(self):
        source = load_source()
        for path in ("runner.py", "cases.json"):
            with self.subTest(path=path):
                proposal = self.proposal(source)
                proposal["replacements"][0].update(
                    path=path,
                    before_sha256=digest(dict(source.contract.originals)[path]),
                )
                self.assertEqual(
                    self.review(source, proposal)["reasons"], ["PROTECTED_FILE_CHANGE"]
                )

    def test_source_policy_and_original_file_mismatches_are_refused(self):
        source = load_source()
        for field, reason in (
            ("snapshot_sha256", "STALE_OR_WRONG_SOURCE"),
            ("policy_sha256", "POLICY_BINDING_MISMATCH"),
        ):
            with self.subTest(field=field):
                self.assertEqual(
                    self.review(source, self.proposal(source, **{field: "0" * 64}))[
                        "reasons"
                    ],
                    [reason],
                )
        proposal = self.proposal(source)
        proposal["replacements"][0]["before_sha256"] = "0" * 64
        self.assertEqual(
            self.review(source, proposal)["reasons"], ["ORIGINAL_FILE_BINDING_MISMATCH"]
        )

    def test_model_text_and_model_readiness_never_execute_or_enable_dispatch(self):
        source = load_source()
        proposal = self.proposal(source)
        proposal["replacements"][0]["after_utf8"] = (
            "raise RuntimeError('MUST_NOT_RUN')\n"
        )
        result = self.review(source, proposal)
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(result["execution"], "NOT_RUN")
        proposal["spending_limit_verified"] = True
        self.assertEqual(
            self.review(source, proposal)["reasons"], ["UNEXPECTED_OR_MISSING_FIELDS"]
        )

    def test_literal_extraction_never_calls_python_functions(self):
        with self.assertRaisesRegex(SourceUnavailable, "NON_LITERAL"):
            extract_constants(
                b"BASELINE = __import__('os').system('unsafe')", ("BASELINE",)
            )
        with self.assertRaisesRegex(SourceUnavailable, "DUPLICATE"):
            extract_constants(b"BASELINE = 'a'\nBASELINE = 'b'", ("BASELINE",))


if __name__ == "__main__":
    unittest.main()
