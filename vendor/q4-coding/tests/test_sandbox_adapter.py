import unittest
from types import SimpleNamespace

from coding.sandbox_adapter import (
    ContractViolation,
    OpenShellSandboxAdapter,
    REQUIRED_COMMAND,
    SandboxRequest,
    contract_summary,
)


DIGEST = "a" * 64


class FakeClient:
    def __init__(self, *, exit_code=0, fail_exec=False, fail_delete=False):
        self.calls = []
        self.exit_code = exit_code
        self.fail_exec = fail_exec
        self.fail_delete = fail_delete

    def create(self, *, workspace, name):
        self.calls.append(("create", workspace, name))
        return SimpleNamespace(name=name)

    def wait_ready(self, name, *, workspace, timeout_seconds):
        self.calls.append(("wait_ready", workspace, name, timeout_seconds))

    def exec(self, name, command, *, workspace):
        self.calls.append(("exec", workspace, name, tuple(command)))
        if self.fail_exec:
            raise RuntimeError("provider unavailable")
        return SimpleNamespace(exit_code=self.exit_code, stdout="fixture\n", stderr="")

    def delete(self, name, *, workspace):
        self.calls.append(("delete", workspace, name))
        if self.fail_delete:
            raise RuntimeError("delete failed")
        return SimpleNamespace(sandbox_id="sandbox-1")

    def wait_deleted(self, name, *, workspace, expected_sandbox_id):
        self.calls.append(("wait_deleted", workspace, name, expected_sandbox_id))


def request(**changes):
    values = {
        "run_id": "fixture-1",
        "staged_source_sha256": DIGEST,
        "staged_suite_sha256": DIGEST,
        "policy_sha256": DIGEST,
    }
    values.update(changes)
    return SandboxRequest(**values)


class SandboxAdapterCases(unittest.TestCase):
    def test_contract_forbids_local_fallback(self):
        self.assertEqual(contract_summary()["local_fallback"], "FORBIDDEN")
        self.assertEqual(tuple(contract_summary()["required_command"]), REQUIRED_COMMAND)

    def test_happy_lifecycle_uses_provider_and_deletes(self):
        client = FakeClient()
        result = OpenShellSandboxAdapter(client).execute(request())
        self.assertEqual(result["status"], "EXECUTED_IN_OPENSHELL")
        self.assertTrue(result["deleted"])
        self.assertEqual([c[0] for c in client.calls],
                         ["create", "wait_ready", "exec", "delete", "wait_deleted"])

    def test_changed_command_is_blocked_before_provider_call(self):
        client = FakeClient()
        with self.assertRaisesRegex(ContractViolation, "COMMAND_CONTRACT_CHANGED"):
            OpenShellSandboxAdapter(client).execute(request(command=("sh", "-c", "id")))
        self.assertEqual(client.calls, [])

    def test_bad_digest_is_blocked_before_provider_call(self):
        client = FakeClient()
        with self.assertRaisesRegex(ContractViolation, "INVALID_SOURCE_DIGEST"):
            OpenShellSandboxAdapter(client).execute(request(staged_source_sha256="unknown"))
        self.assertEqual(client.calls, [])

    def test_provider_failure_still_deletes(self):
        client = FakeClient(fail_exec=True)
        result = OpenShellSandboxAdapter(client).execute(request())
        self.assertEqual(result["status"], "EXECUTION_FAILED")
        self.assertTrue(result["deleted"])
        self.assertIn("delete", [c[0] for c in client.calls])

    def test_nonzero_exit_fails_closed(self):
        result = OpenShellSandboxAdapter(FakeClient(exit_code=2)).execute(request())
        self.assertEqual(result["status"], "EXECUTION_FAILED")

    def test_cleanup_failure_overrides_success(self):
        result = OpenShellSandboxAdapter(FakeClient(fail_delete=True)).execute(request())
        self.assertEqual(result["status"], "INCOMPLETE_CLEANUP")
        self.assertFalse(result["deleted"])


if __name__ == "__main__":
    unittest.main()
