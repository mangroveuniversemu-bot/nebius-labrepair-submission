import copy
import unittest

from coding.patch_review import BASELINE, SUITE_DIGEST, digest
from coding.workspace_contract import (
    FROZEN_POLICY,
    RecoveryExpectation,
    WorkspaceContractViolation,
    build_manifest,
    policy_sha256,
    recovery_receipt,
    reviewed_workspace,
)


def expectation():
    manifest = build_manifest(reviewed_workspace())
    return RecoveryExpectation(
        manifest_sha256=manifest["manifest_sha256"],
        source_sha256=digest(BASELINE),
        suite_sha256=SUITE_DIGEST,
        policy_sha256=manifest["policy_sha256"],
    )


def provider_result(**changes):
    expected = expectation()
    result = {
        "fixture": True,
        "status": "EXECUTED_IN_OPENSHELL",
        "deleted": True,
        "manifest_sha256": expected.manifest_sha256,
        "source_sha256": expected.source_sha256,
        "suite_sha256": expected.suite_sha256,
        "policy_sha256": expected.policy_sha256,
    }
    result.update(changes)
    return result


class WorkspaceContractCases(unittest.TestCase):
    def test_manifest_is_deterministic_and_exact(self):
        first = build_manifest(reviewed_workspace())
        self.assertEqual(first, build_manifest(reviewed_workspace()))
        self.assertEqual([x["path"] for x in first["files"]],
                         ["cases.json", "ledger.py", "runner.py"])

    def test_extra_file_is_blocked(self):
        files = reviewed_workspace()
        files["notes.txt"] = b"unexpected"
        with self.assertRaisesRegex(WorkspaceContractViolation, "PATH_SET"):
            build_manifest(files)

    def test_path_traversal_is_blocked(self):
        files = reviewed_workspace()
        files["../ledger.py"] = files.pop("ledger.py")
        with self.assertRaisesRegex(WorkspaceContractViolation, "PATH_SET"):
            build_manifest(files)

    def test_non_bytes_entry_is_blocked(self):
        files = reviewed_workspace()
        files["ledger.py"] = "not-bytes"
        with self.assertRaisesRegex(WorkspaceContractViolation, "NON_BYTES"):
            build_manifest(files)

    def test_content_change_changes_manifest_digest(self):
        files = reviewed_workspace()
        original = build_manifest(files)["manifest_sha256"]
        files["ledger.py"] += b"\n# changed"
        self.assertNotEqual(original, build_manifest(files)["manifest_sha256"])

    def test_policy_change_changes_digest(self):
        changed = copy.deepcopy(FROZEN_POLICY)
        changed["network"] = "ALLOW"
        self.assertNotEqual(policy_sha256(), policy_sha256(changed))

    def test_fixture_recovery_receipt_is_verified_but_not_live(self):
        expected = expectation()
        receipt = recovery_receipt(provider_result(), expected,
                                   current_source_sha256=expected.source_sha256,
                                   candidate_applied=False)
        self.assertEqual(receipt["status"], "RECOVERY_VERIFIED")
        self.assertEqual(receipt["live_validation"], "NOT_RUN")

    def test_cleanup_failure_blocks_recovery(self):
        expected = expectation()
        receipt = recovery_receipt(provider_result(deleted=False), expected,
                                   current_source_sha256=expected.source_sha256,
                                   candidate_applied=False)
        self.assertEqual(receipt["status"], "RECOVERY_INCOMPLETE")
        self.assertFalse(receipt["checks"]["sandbox_deleted"])

    def test_changed_base_blocks_recovery(self):
        expected = expectation()
        receipt = recovery_receipt(provider_result(), expected,
                                   current_source_sha256="f" * 64,
                                   candidate_applied=False)
        self.assertEqual(receipt["status"], "RECOVERY_INCOMPLETE")
        self.assertFalse(receipt["checks"]["base_source_restored"])

    def test_binding_mismatch_blocks_recovery(self):
        expected = expectation()
        receipt = recovery_receipt(provider_result(manifest_sha256="0" * 64), expected,
                                   current_source_sha256=expected.source_sha256,
                                   candidate_applied=False)
        self.assertEqual(receipt["status"], "RECOVERY_INCOMPLETE")
        self.assertFalse(receipt["checks"]["manifest_binding_matches"])


if __name__ == "__main__":
    unittest.main()
