"""Fixed offline demo audit controls; no provider, browser or candidate runs."""

import contextlib
import copy
import io
import json
import os
import shutil
import socket
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import verify_demo as demo


class DemoEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "source"
        self.root.mkdir()
        for name in (*demo.PINS, *demo.DRAFT_FILES, "scripts/verify_demo.py", "labrepair/historical_bytes.py"):
            source = demo.ROOT / name
            if source.is_file():
                destination = self.root / name
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, destination)

    def report(self):
        return demo.audit_demo(self.root)

    def test_clean_checkout_reports_real_gap_without_claiming_readiness(self):
        report = self.report()
        self.assertFalse(report["success"])
        self.assertEqual(report["status"], "BLOCKED_EVIDENCE_GAPS")
        self.assertEqual(report["source_evidence"]["matched_count"], 5)
        self.assertEqual(report["source_evidence"]["required_count"], 6)
        self.assertEqual(report["draft_validation"]["status"], "MATCHED_DRAFT_STRUCTURE")
        self.assertEqual(report["draft_validation"]["measurements"]["planned_seconds"], 165)
        self.assertEqual(report["blockers"], [{"artifact": "ops/nebius_009_checkpoint_final.json",
                                             "reason": "REQUIRED_SOURCE_MISSING"}])
        self.assertEqual(report["source_evidence"]["static_facts"], "MATCHED_PINNED_STATIC_FACTS")
        self.assertEqual(report["historical_packaging_helper"]["status"], "MISSING")
        self.assertFalse(report["historical_packaging_helper"]["required_for_draft_check"])
        for field in ("recording_ready", "submission_ready", "source_inputs_modified"):
            self.assertIs(report[field], False)
        for field in ("recording", "submission", "live_provider", "candidate_execution", "isolated_runtime",
                      "visual_qa", "manual_content_review"):
            self.assertEqual(report[field], "NOT_RUN")
        self.assertEqual(report["actual_provider_usage"], "unknown")
        self.assertEqual(report["actual_provider_cost"], "unknown")
        self.assertEqual(report["network_requests"], 0)
        with patch.object(demo, "ROOT", self.root), self.assertRaisesRegex(demo.DemoInvalid, "SOURCE_EVIDENCE_INCOMPLETE"):
            demo.checked_source()

    def test_unchanged_original_pins_and_archived_draft_are_read_only(self):
        before = {path.relative_to(self.root): path.read_bytes() for path in self.root.rglob("*") if path.is_file()}
        self.report()
        after = {path.relative_to(self.root): path.read_bytes() for path in self.root.rglob("*") if path.is_file()}
        self.assertEqual(before, after)
        data = json.loads((self.root / demo.DRAFT_FILES[0]).read_bytes())
        self.assertEqual(demo.PINS, data["source_sha256"])
        self.assertEqual(demo.SOURCE_PACKAGE_SHA256, data["source_package_sha256"])
        self.assertFalse((self.root / "ops/nebius_009_checkpoint_final.json").exists())

    def test_exact_historical_restoration_is_reported_separately(self):
        name = "handover-workbench/historical-domain.json"
        source = (self.root / name).read_bytes()
        report = self.report()
        entry = report["source_evidence"]["files"][name]
        self.assertEqual(entry["status"], "MATCHED")
        self.assertEqual(entry["representation"], "LF_TO_HISTORICAL_CRLF")
        self.assertEqual(entry["observed_sha256"], demo.sha(source))
        self.assertEqual(entry["pinned_representation_sha256"], demo.PINS[name])
        self.assertNotEqual(entry["observed_sha256"], demo.PINS[name])
        self.assertEqual((self.root / name).read_bytes(), source)

    def test_changed_and_mixed_line_endings_fail_existing_pin(self):
        name = "handover-workbench/historical-domain.json"
        path = self.root / name
        raw = path.read_bytes()
        for changed in (raw.replace(b"\n", b"\r\n", 1), raw + b" ", raw.replace(b'"BLOCK"', b'"ALLOW"')):
            with self.subTest(changed_hash=demo.sha(changed)):
                path.write_bytes(changed)
                self.assertEqual(self.report()["source_evidence"]["files"][name]["status"], "DIGEST_MISMATCH")
        path.write_bytes(raw.replace(b"\n", b"\r\n"))
        self.assertEqual(self.report()["source_evidence"]["files"][name]["representation"], "EXACT")

    def test_forged_checkpoint_does_not_fill_the_missing_requirement(self):
        path = self.root / "ops/nebius_009_checkpoint_final.json"
        path.parent.mkdir()
        path.write_text('{"status":"PASS","live_provider":"SUCCESS"}')
        report = self.report()
        self.assertEqual(report["source_evidence"]["files"]["ops/nebius_009_checkpoint_final.json"]["status"], "DIGEST_MISMATCH")
        self.assertFalse(report["source_evidence"]["all_required_sources_matched"])
        self.assertFalse(report["success"])

    def test_optional_archive_is_not_required_but_mismatch_blocks(self):
        missing = self.report()["source_evidence"]["historical_archive"]
        self.assertEqual(missing["status"], "MISSING")
        self.assertFalse(missing["required_for_draft_check"])
        (self.root.parent / "Nebius_Coding_PoC_nebius_009.zip").write_bytes(b"not an archive")
        report = self.report()
        self.assertIn({"artifact": "historical_source_archive", "reason": "ARCHIVE_SIZE_MISMATCH"}, report["blockers"])

    def test_symlinks_and_symlinked_ancestors_are_never_followed(self):
        name = "handover-workbench/index.html"
        path = self.root / name
        raw = path.read_bytes()
        external = self.root.parent / "external.html"
        external.write_bytes(raw)
        path.unlink()
        path.symlink_to(external)
        self.assertEqual(self.report()["source_evidence"]["files"][name]["status"], "UNSAFE_PATH")
        path.unlink()
        path.write_bytes(raw)
        actual = self.root / "handover-workbench"
        moved = self.root.parent / "moved"
        actual.rename(moved)
        actual.symlink_to(moved, target_is_directory=True)
        self.assertEqual(self.report()["source_evidence"]["files"][name]["status"], "UNSAFE_PATH")

    def test_directory_fifo_and_oversize_inputs_fail_bounded(self):
        path = self.root / "handover-workbench/index.html"
        path.unlink()
        path.mkdir()
        self.assertEqual(self.report()["source_evidence"]["files"]["handover-workbench/index.html"]["status"], "REGULAR_FILE_REQUIRED")
        path.rmdir()
        os.mkfifo(path)
        self.assertEqual(self.report()["source_evidence"]["files"]["handover-workbench/index.html"]["status"], "REGULAR_FILE_REQUIRED")
        path.unlink()
        path.write_bytes(b"x" * (demo.MAX_FILE_BYTES + 1))
        self.assertEqual(self.report()["source_evidence"]["files"]["handover-workbench/index.html"]["status"], "FILE_TOO_LARGE")

    def test_missing_and_invalid_draft_inputs_do_not_hide_source_gap(self):
        path = self.root / demo.DRAFT_FILES[0]
        for raw in (b'{"schema_version":1,"schema_version":1}', b'NaN', b'\xff', b'[]', b'{"private":"DO_NOT_ECHO"}'):
            with self.subTest(raw=raw):
                path.write_bytes(raw)
                report = self.report()
                self.assertEqual(report["draft_validation"]["status"], "BLOCKED_INVALID_DRAFT")
                self.assertNotIn("DO_NOT_ECHO", json.dumps(report))
                self.assertGreaterEqual(len(report["blockers"]), 2)
        path.unlink()
        self.assertEqual(self.report()["draft_validation"]["status"], "BLOCKED_INPUT_UNAVAILABLE")

    def test_malformed_scene_has_fixed_diagnostic(self):
        path = self.root / demo.DRAFT_FILES[0]
        data = json.loads(path.read_bytes())
        data["scenes"][0] = "PRIVATE_SCENE_SENTINEL"
        path.write_text(json.dumps(data))
        report = self.report()
        self.assertEqual(report["draft_validation"]["reason"], "INVALID_SCENE_SHAPE")
        self.assertNotIn("PRIVATE_SCENE_SENTINEL", json.dumps(report))

    def test_all_six_historical_negative_controls_still_reject(self):
        data = json.loads((self.root / demo.DRAFT_FILES[0]).read_bytes())
        captions = (self.root / demo.DRAFT_FILES[1]).read_text()
        markdown = (self.root / demo.DRAFT_FILES[2]).read_text()
        for name in ("forged_live_status", "original_claim_promotion", "source_pin_tamper", "timeline_overrun",
                     "caption_overstatement", "recorded_video_claim"):
            changed, altered = copy.deepcopy(data), captions
            if name == "forged_live_status":
                changed["facts"]["model"] = "SUCCESS"
            elif name == "original_claim_promotion":
                changed["facts"]["original_claim"] = "ALLOW"
            elif name == "source_pin_tamper":
                changed["source_sha256"]["handover-workbench/index.html"] = "0" * 64
            elif name == "timeline_overrun":
                changed["timeline_seconds"] = 181
            elif name == "caption_overstatement":
                altered = captions.replace("prototype", "production")
                self.assertNotEqual(altered, captions)
            else:
                changed["video_recorded"] = True
            with self.subTest(control=name), self.assertRaises(demo.DemoInvalid):
                demo.validate(changed, altered, markdown)

    def test_network_attempt_is_not_needed_for_complete_audit(self):
        with patch.object(socket, "socket", side_effect=AssertionError("network forbidden")):
            self.assertEqual(self.report()["source_evidence"]["matched_count"], 5)

    def test_cli_prints_and_saves_blocked_report_with_exit_two(self):
        output = self.root.parent / "new-audit.json"
        captured = io.StringIO()
        with patch.object(demo, "ROOT", self.root), contextlib.redirect_stdout(captured):
            code = demo.main(["--output", str(output)])
        self.assertEqual(code, 2)
        self.assertEqual(output.read_text(), captured.getvalue())
        self.assertEqual(json.loads(output.read_bytes())["status"], "BLOCKED_EVIDENCE_GAPS")

    def test_cli_default_is_read_only_and_reports_implementation_hashes(self):
        captured = io.StringIO()
        with patch.object(demo, "ROOT", self.root), contextlib.redirect_stdout(captured):
            self.assertEqual(demo.main([]), 2)
        report = json.loads(captured.getvalue())
        for name in ("scripts/verify_demo.py", "labrepair/historical_bytes.py"):
            self.assertEqual(report["implementation"][name]["observed_sha256"], demo.sha((self.root / name).read_bytes()))
        self.assertFalse((self.root / "evidence").exists())

    def test_existing_output_symlink_and_ancestor_are_preserved(self):
        output = self.root.parent / "existing.json"
        output.write_bytes(b"preserve me")
        link = self.root.parent / "linked.json"
        link.symlink_to(output)
        linked_parent = self.root.parent / "linked-parent"
        linked_parent.symlink_to(self.root, target_is_directory=True)
        for destination in (output, link, linked_parent / "new.json"):
            captured = io.StringIO()
            with self.subTest(destination=destination.name), patch.object(demo, "ROOT", self.root), contextlib.redirect_stdout(captured):
                self.assertEqual(demo.main(["--output", str(destination)]), 2)
            self.assertEqual(json.loads(captured.getvalue())["status"], "AUDIT_NOT_SAVED")
            self.assertEqual(output.read_bytes(), b"preserve me")
        self.assertFalse((self.root / "new.json").exists())

    def test_invalid_cli_arguments_never_echo_private_values(self):
        captured = io.StringIO()
        with contextlib.redirect_stdout(captured):
            self.assertEqual(demo.main(["--private-token", "PRIVATE_SENTINEL"]), 2)
        self.assertNotIn("PRIVATE_SENTINEL", captured.getvalue())
        self.assertEqual(json.loads(captured.getvalue())["reason"], "INPUT_OR_NEW_OUTPUT_UNAVAILABLE")

    def test_partial_write_failure_never_publishes_final_receipt(self):
        output = self.root.parent / "partial.json"
        original_fdopen = os.fdopen

        class BrokenWriter:
            def __init__(self, descriptor, mode):
                self.stream = original_fdopen(descriptor, mode)

            def __enter__(self):
                return self

            def __exit__(self, *args):
                self.stream.close()

            def write(self, raw):
                self.stream.write(raw[:7])
                self.stream.flush()
                self.assert_final_absent()
                raise OSError("injected partial write")

            def assert_final_absent(self):
                if output.exists():
                    raise AssertionError("partial final receipt became visible")

        with patch.object(os, "fdopen", BrokenWriter), self.assertRaises(OSError):
            demo._write_new(output, b'{"complete": true}\n')
        self.assertFalse(output.exists())
        self.assertFalse(list(output.parent.glob(".labrepair-demo-*.tmp")))

    def test_receipt_cannot_create_any_missing_reserved_input(self):
        reserved = (*demo.PINS, *demo.DRAFT_FILES, "scripts/package_checkpoint.py",
                    "scripts/verify_demo.py", "labrepair/historical_bytes.py")
        for name in reserved:
            output = self.root / name
            if output.exists():
                output.unlink()
            output.parent.mkdir(parents=True, exist_ok=True)
            with self.subTest(name=name), patch.object(demo, "ROOT", self.root), self.assertRaisesRegex(
                demo.DemoInvalid, "RESERVED_INPUT_OUTPUT_FORBIDDEN"
            ):
                demo._write_new(output, b'{"not_a_source": true}\n')
            self.assertFalse(output.exists())
        archive = self.root.parent / "Nebius_Coding_PoC_nebius_009.zip"
        with patch.object(demo, "ROOT", self.root), self.assertRaisesRegex(
            demo.DemoInvalid, "RESERVED_INPUT_OUTPUT_FORBIDDEN"
        ):
            demo._write_new(archive, b'{"not_an_archive": true}\n')
        self.assertFalse(archive.exists())

    def test_destination_creation_race_never_overwrites_receipt(self):
        output = self.root.parent / "race.json"
        original_link = os.link

        def concurrent_create(source, target, **kwargs):
            output.write_bytes(b"other writer's receipt")
            return original_link(source, target, **kwargs)

        # Preserve the capability catalog while injecting only the link call.
        with patch.object(os, "link", concurrent_create), patch.object(
            os, "supports_dir_fd", os.supports_dir_fd | {concurrent_create}
        ), self.assertRaises(FileExistsError):
            demo._write_new(output, b'{"complete": true}\n')
        self.assertEqual(output.read_bytes(), b"other writer's receipt")
        self.assertFalse(list(output.parent.glob(".labrepair-demo-*.tmp")))

    def test_publication_uses_open_anonymous_inode_without_staging_name(self):
        output = self.root.parent / "anonymous.json"
        original_link = os.link
        payload = b'{"complete": true}\n'

        def inspect_publication(source, target, **kwargs):
            self.assertRegex(source, r"^/proc/self/fd/[0-9]+$")
            self.assertEqual(Path(source).read_bytes(), payload)
            self.assertEqual(os.stat(source).st_nlink, 0)
            self.assertTrue(kwargs["follow_symlinks"])
            self.assertFalse(output.exists())
            self.assertFalse(list(output.parent.glob(".labrepair-demo-*.tmp")))
            return original_link(source, target, **kwargs)

        with patch.object(os, "link", inspect_publication), patch.object(
            os, "supports_dir_fd", os.supports_dir_fd | {inspect_publication}
        ):
            demo._write_new(output, payload)
        self.assertFalse(output.is_symlink())
        self.assertEqual(output.read_bytes(), payload)

    def test_complete_synthetic_source_control_never_authorizes_recording(self):
        # Test-only source substitution exercises the all-matched branch. It is
        # not historical recovery and does not modify production source pins.
        checkpoint = self.root / "ops/nebius_009_checkpoint_final.json"
        checkpoint.parent.mkdir()
        checkpoint.write_bytes(b"synthetic checkpoint control")
        pins = {**demo.PINS, "ops/nebius_009_checkpoint_final.json": demo.sha(checkpoint.read_bytes())}
        data_path = self.root / demo.DRAFT_FILES[0]
        data = json.loads(data_path.read_bytes())
        data["source_sha256"] = pins
        data_path.write_text(json.dumps(data))
        with patch.object(demo, "PINS", pins):
            report = self.report()
        self.assertTrue(report["success"])
        self.assertEqual(report["status"], "OFFLINE_DRAFT_CHECKS_MATCHED")
        self.assertFalse(report["recording_ready"])
        self.assertFalse(report["submission_ready"])
        self.assertEqual(report["manual_content_review"], "NOT_RUN")


if __name__ == "__main__":
    unittest.main()
