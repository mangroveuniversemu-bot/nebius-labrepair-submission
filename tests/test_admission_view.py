"""Fixed, offline review-page checks. No candidate or provider is executed."""

import contextlib
import io
import json
import os
import tempfile
import unittest
from datetime import timedelta
from html.parser import HTMLParser
from pathlib import Path
from unittest.mock import patch

from labrepair.admission_view import (
    BINDINGS, CSP, REASONS, SOURCE_FILES, _read_claims, create_view, main, write_view,
)
from labrepair.candidate_review import digest
from labrepair.paths import ROOT
from labrepair.provider_admission import MAX_EVIDENCE_BYTES, evaluate_admission
from labrepair.provider_envelope import encoded, prepare_request
from labrepair.q4_source import SourceUnavailable
from test_provider_admission import NOW, synthetic_evidence


class PageAudit(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags = []
        self.links = []
        self.attributes = []

    def handle_starttag(self, tag, attrs):
        self.tags.append(tag)
        self.attributes.extend(attrs)
        self.links.extend(value for name, value in attrs if name == "href")


class AdmissionViewTests(unittest.TestCase):
    def setUp(self):
        self.draft = prepare_request()
        self.claims = synthetic_evidence(self.draft)

    def build(self, raw=None, now=NOW):
        files = create_view(raw, now=now)
        return files, json.loads(files["report.json"]), files["index.html"].decode()

    def test_missing_evidence_has_readable_blockers_and_provenance(self):
        files, report, page = self.build()
        self.assertEqual(set(files), {"report.json", "index.html"})
        self.assertIn("No separate evidence claims were supplied", page)
        self.assertEqual(report["admission"]["policy_reasons"], ["ADMISSION_EVIDENCE_MISSING"])
        self.assertEqual(report["admission"]["request_body_sha256"], digest(self.draft.body))
        self.assertIsNone(report["admission"]["evidence_sha256"])
        self.assertEqual(set(report["source_bindings"]), set(BINDINGS))
        self.assertEqual(report["generated_at_utc"], NOW.isoformat())
        for name in SOURCE_FILES:
            self.assertEqual(report["implementation_sha256"][name], digest((ROOT / name).read_bytes()))
        self.assertIn(digest(files["report.json"]), page)
        self.assertIn("not recorded", page)

    def test_complete_synthetic_claims_never_look_like_runtime_approval(self):
        raw = encoded(self.claims)
        _, report, page = self.build(raw)
        admission = report["admission"]
        self.assertEqual(admission, evaluate_admission(self.draft, raw, now=NOW))
        self.assertEqual(admission["policy_evaluation"], "CLAIMS_SATISFY_POLICY")
        self.assertEqual(admission["runtime_admission"], "BLOCKED")
        self.assertEqual(admission["claimed_request_cost_upper_bound_usd"], "0.000128")
        for expected in ("Provider access stays blocked.", "SYNTHETIC_FIXTURE", "US$0 maximum authorized actual cash",
                         "A US$25 credit balance is not a US$25 cash allowance", "not a current quote", "NOT_RUN"):
            self.assertIn(expected, page)
        for field in ("actual_provider_usage", "actual_provider_cost", "actual_provider_latency"):
            self.assertEqual(admission[field], "unknown")
        self.assertEqual(admission["evidence_sha256"], digest(raw))

    def test_operator_assertions_remain_unauthenticated(self):
        self.claims["evidence_kind"] = "OPERATOR_ASSERTION"
        _, report, page = self.build(encoded(self.claims))
        self.assertEqual(report["admission"]["status"], "BLOCKED")
        self.assertEqual(report["evidence_authentication"], "NOT_IMPLEMENTED")
        self.assertIn("OPERATOR_ASSERTION", page)
        self.assertIn("Claims and hashes do not authenticate", page)

    def test_invalid_stale_and_saved_verdict_inputs_fail_closed(self):
        files, _, _ = self.build()
        variants = (
            (b"\xff", NOW, "INVALID_ADMISSION_EVIDENCE_JSON"),
            (b'{"schema":1,"schema":1}', NOW, "INVALID_ADMISSION_EVIDENCE_JSON"),
            (json.dumps(self.claims).encode("utf-16"), NOW, "INVALID_ADMISSION_EVIDENCE_JSON"),
            (encoded(self.claims), NOW + timedelta(hours=1), "STALE_OR_FUTURE_ADMISSION_EVIDENCE"),
            (encoded(self.claims), NOW - timedelta(hours=1), "STALE_OR_FUTURE_ADMISSION_EVIDENCE"),
            (files["report.json"], NOW, "INVALID_ADMISSION_EVIDENCE_SCHEMA"),
            (b"x" * (MAX_EVIDENCE_BYTES + 1), NOW, "ADMISSION_EVIDENCE_TOO_LARGE"),
        )
        for raw, now, reason in variants:
            with self.subTest(reason=reason, size=len(raw)):
                _, report, page = self.build(raw, now)
                self.assertEqual(report["admission"]["policy_reasons"], [reason])
                self.assertEqual(report["admission"]["runtime_admission"], "BLOCKED")
                self.assertIn(REASONS[reason], page)

    def test_raw_evidence_account_scope_and_untrusted_text_are_not_exported(self):
        sentinel = "<script>alert('PRIVATE_SENTINEL')</script>"
        self.claims["credential"] = sentinel
        raw = encoded(self.claims)
        files, report, _ = self.build(raw)
        for value in files.values():
            self.assertNotIn(sentinel.encode(), value)
            self.assertNotIn(b"PRIVATE_SENTINEL", value)
            self.assertNotIn(self.claims["scope"]["account_scope_sha256"].encode(), value)
            self.assertNotIn(self.draft.body, value)
        self.assertEqual(report["admission"]["evidence_sha256"], digest(raw))

    def test_semantic_policy_blockers_have_concrete_explanations(self):
        self.claims["cash_controls"]["provider_hard_stop"] = False
        self.claims["cash_controls"]["automatic_top_up"] = True
        self.claims["permissions"]["isolated_backend_verified"] = False
        _, report, page = self.build(encoded(self.claims))
        for reason in report["admission"]["policy_reasons"] + report["admission"]["runtime_reasons"]:
            self.assertIn(reason, REASONS)
            self.assertIn(REASONS[reason], page)
        self.assertIn("credit exhaustion", page)

    def test_page_is_script_free_with_only_local_allowlisted_links(self):
        _, _, page = self.build()
        audit = PageAudit()
        audit.feed(page)
        self.assertFalse(set(audit.tags) & {"script", "button", "form", "input", "iframe", "object", "embed", "img", "base"})
        self.assertEqual(audit.links, ["#blockers", "#provenance", "#report", "report.json"])
        self.assertFalse(any(name.startswith("on") or name == "src" for name, _ in audit.attributes))
        self.assertIn(("content", CSP), audit.attributes)
        self.assertIn(("lang", "en"), audit.attributes)

    def test_source_failure_or_invalid_clock_never_returns_saved_view(self):
        with patch("labrepair.admission_view.prepare_request", side_effect=SourceUnavailable("PRIVATE_FAILURE")):
            with self.assertRaises(SourceUnavailable):
                create_view()
        with self.assertRaisesRegex(ValueError, "INVALID_REVIEW_CLOCK"):
            create_view(now=NOW.replace(tzinfo=None))

    def test_changed_evaluator_runtime_boundary_cannot_be_rendered(self):
        changed = evaluate_admission(self.draft, now=NOW)
        changed["runtime_admission"] = "ALLOWED"
        with patch("labrepair.admission_view.evaluate_admission", return_value=changed):
            with self.assertRaisesRegex(ValueError, "OFFLINE_BOUNDARY_CHANGED"):
                create_view(now=NOW)

    def test_fresh_directory_writes_exact_bytes_and_repeat_preserves_review(self):
        files, _, _ = self.build()
        with tempfile.TemporaryDirectory() as directory, patch("labrepair.admission_view.ROOT", Path(directory)):
            output = write_view("review-1", files)
            self.assertEqual({p.name for p in output.iterdir()}, set(files))
            for name, raw in files.items():
                self.assertEqual((output / name).read_bytes(), raw)
            with self.assertRaises(FileExistsError):
                write_view("review-1", {name: b"replacement" for name in files})
            for name, raw in files.items():
                self.assertEqual((output / name).read_bytes(), raw)

    def test_output_names_reject_traversal_nested_and_absolute_paths(self):
        files, _, _ = self.build()
        with tempfile.TemporaryDirectory() as directory, patch("labrepair.admission_view.ROOT", Path(directory)):
            for name in ("../escape", "/tmp/escape", "a/b", ".", "", "a" * 65, "bad name", "bad\n"):
                with self.subTest(name=name), self.assertRaises(ValueError):
                    write_view(name, files)
            self.assertFalse((Path(directory) / "admission-workbench").exists())

    def test_symlinked_output_root_and_review_are_rejected(self):
        files, _, _ = self.build()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            outside = root / "outside"
            outside.mkdir()
            output = root / "admission-workbench"
            output.symlink_to(outside, target_is_directory=True)
            with patch("labrepair.admission_view.ROOT", root), self.assertRaises(OSError):
                write_view("review-1", files)
            output.unlink()
            output.mkdir()
            (output / "review-1").symlink_to(outside, target_is_directory=True)
            with patch("labrepair.admission_view.ROOT", root), self.assertRaises(OSError):
                write_view("review-1", files)
            self.assertEqual(list(outside.iterdir()), [])

    def test_claim_reader_is_bounded_and_refuses_outside_and_symlink_inputs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            evidence = root / "evidence"
            evidence.mkdir()
            claims = evidence / "claims.json"
            claims.write_bytes(b"x" * (MAX_EVIDENCE_BYTES + 100))
            outside = root / "outside.json"
            outside.write_bytes(b"PRIVATE_SENTINEL")
            link = evidence / "link.json"
            link.symlink_to(outside)
            with patch("labrepair.admission_view.ROOT", root):
                self.assertEqual(len(_read_claims(claims)), MAX_EVIDENCE_BYTES + 1)
                for path in (outside, link, evidence, evidence / "missing.json"):
                    with self.subTest(name=path.name), self.assertRaises((ValueError, OSError)):
                        _read_claims(path)

    def test_symlinked_evidence_root_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            real = root / "real"
            real.mkdir()
            (real / "claims.json").write_bytes(b"{}")
            (root / "evidence").symlink_to(real, target_is_directory=True)
            with patch("labrepair.admission_view.ROOT", root), self.assertRaises(OSError):
                _read_claims(root / "evidence/claims.json")

    def test_output_directory_swap_before_open_cannot_redirect_writes(self):
        files, _, _ = self.build()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            outside = root / "outside"
            outside.mkdir()
            target = root / "admission-workbench/race"
            real_mkdir = os.mkdir

            def swap(name, *args, **kwargs):
                result = real_mkdir(name, *args, **kwargs)
                if name == "race":
                    target.rmdir()
                    target.symlink_to(outside, target_is_directory=True)
                return result

            with patch("labrepair.admission_view.ROOT", root), patch("os.mkdir", side_effect=swap) as mocked:
                with patch("os.supports_dir_fd", {*os.supports_dir_fd, mocked}), self.assertRaises(OSError):
                    write_view("race", files)
            self.assertEqual(list(outside.iterdir()), [])

    def test_input_swap_before_open_cannot_read_external_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "evidence").mkdir()
            claims = root / "evidence/claims.json"
            claims.write_bytes(b"{}")
            outside = root / "outside.json"
            outside.write_bytes(b"PRIVATE_SENTINEL")
            real_open = os.open

            def swap(name, *args, **kwargs):
                if name == "claims.json":
                    claims.unlink()
                    claims.symlink_to(outside)
                return real_open(name, *args, **kwargs)

            with patch("labrepair.admission_view.ROOT", root), patch("os.open", side_effect=swap) as mocked:
                with patch("os.supports_dir_fd", {*os.supports_dir_fd, mocked}), self.assertRaises(OSError):
                    _read_claims(claims)

    def test_unsupported_descriptor_platform_fails_closed(self):
        files, _, _ = self.build()
        with tempfile.TemporaryDirectory() as directory, patch("labrepair.admission_view.ROOT", Path(directory)):
            with patch("os.supports_dir_fd", set()), self.assertRaises(ValueError):
                write_view("unsupported", files)
            self.assertFalse((Path(directory) / "admission-workbench").exists())

    def test_unknown_or_missing_cli_arguments_do_not_echo_private_text(self):
        for arguments in (["--unknown", "PRIVATE_SENTINEL"], ["--review-name"], []):
            with self.subTest(arguments=arguments):
                output, error = io.StringIO(), io.StringIO()
                with patch("sys.argv", ["admission_view", *arguments]), contextlib.redirect_stdout(output), contextlib.redirect_stderr(error):
                    self.assertEqual(main(), 2)
                self.assertNotIn("PRIVATE_SENTINEL", output.getvalue() + error.getvalue())
                self.assertEqual(json.loads(output.getvalue())["view"], "NOT_CREATED")

    def test_cli_generation_success_is_not_admission_and_failures_are_sanitized(self):
        files, _, _ = self.build()
        with tempfile.TemporaryDirectory() as directory, patch("labrepair.admission_view.ROOT", Path(directory)):
            with patch("labrepair.admission_view.create_view", return_value=files):
                output = io.StringIO()
                with patch("sys.argv", ["admission_view", "--review-name", "fresh"]), contextlib.redirect_stdout(output):
                    self.assertEqual(main(), 0)
                self.assertEqual(json.loads(output.getvalue())["runtime_admission"], "BLOCKED")
                repeated = io.StringIO()
                with patch("sys.argv", ["admission_view", "--review-name", "fresh"]), contextlib.redirect_stdout(repeated):
                    self.assertEqual(main(), 2)
                self.assertEqual(json.loads(repeated.getvalue())["view"], "NOT_CREATED")
            with patch("labrepair.admission_view.create_view", side_effect=SourceUnavailable("PRIVATE_SENTINEL")):
                failed = io.StringIO()
                with patch("sys.argv", ["admission_view", "--review-name", "failed"]), contextlib.redirect_stdout(failed):
                    self.assertEqual(main(), 2)
                self.assertNotIn("PRIVATE_SENTINEL", failed.getvalue())
                self.assertFalse((Path(directory) / "admission-workbench/failed").exists())


if __name__ == "__main__":
    unittest.main()
