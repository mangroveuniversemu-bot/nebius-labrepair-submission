"""Bounded NVIDIA OpenShell adapter contract for untrusted patch evaluation.

The adapter intentionally has no local-process fallback. It follows the public
OpenShell 0.1.2 Python SDK lifecycle (create, wait_ready, exec, delete,
wait_deleted) but requires a pre-staged, review-only sandbox workspace. A real
gateway, policy, upload/staging flow, and audit export remain prerequisites for
executing model-produced source.
"""
from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Protocol, Sequence


HEX_256 = re.compile(r"^[0-9a-f]{64}$")
SAFE_NAME = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$")
REQUIRED_COMMAND = ("python", "-I", "runner.py", "cases.json")
CONTRACT_VERSION = "openshell-review-v1"
OFFICIAL_DOCS = (
    "https://docs.nvidia.com/openshell/latest/sdk/python",
    "https://docs.nvidia.com/openshell/about/overview",
)


class OpenShellClient(Protocol):
    """The minimal OpenShell 0.1.2 SDK surface used by this adapter."""

    def create(self, *, workspace: str, name: str) -> Any: ...
    def wait_ready(self, name: str, *, workspace: str, timeout_seconds: int) -> Any: ...
    def exec(self, name: str, command: Sequence[str], *, workspace: str) -> Any: ...
    def delete(self, name: str, *, workspace: str) -> Any: ...
    def wait_deleted(
        self, name: str, *, workspace: str, expected_sandbox_id: str
    ) -> Any: ...


@dataclass(frozen=True)
class SandboxRequest:
    run_id: str
    staged_source_sha256: str
    staged_suite_sha256: str
    policy_sha256: str
    command: tuple[str, ...] = REQUIRED_COMMAND


class ContractViolation(ValueError):
    """Raised before any provider call when the frozen contract is violated."""


def contract_summary() -> dict:
    return {
        "version": CONTRACT_VERSION,
        "required_command": list(REQUIRED_COMMAND),
        "staging": "PRE_STAGED_SANDBOX_ONLY",
        "local_fallback": "FORBIDDEN",
        "live_validation": "NOT_RUN",
        "official_docs": list(OFFICIAL_DOCS),
    }


def validate_request(request: SandboxRequest) -> None:
    if not SAFE_NAME.fullmatch(request.run_id):
        raise ContractViolation("INVALID_RUN_ID")
    if request.command != REQUIRED_COMMAND:
        raise ContractViolation("COMMAND_CONTRACT_CHANGED")
    for value, reason in (
        (request.staged_source_sha256, "INVALID_SOURCE_DIGEST"),
        (request.staged_suite_sha256, "INVALID_SUITE_DIGEST"),
        (request.policy_sha256, "INVALID_POLICY_DIGEST"),
    ):
        if not HEX_256.fullmatch(value):
            raise ContractViolation(reason)


class OpenShellSandboxAdapter:
    """Use an injected real OpenShell SDK client; never execute locally."""

    def __init__(
        self,
        client: OpenShellClient,
        *,
        workspace: str = "default",
        name_prefix: str = "coding-review",
        ready_timeout_seconds: int = 120,
    ) -> None:
        if not SAFE_NAME.fullmatch(workspace):
            raise ValueError("INVALID_WORKSPACE")
        if not SAFE_NAME.fullmatch(name_prefix):
            raise ValueError("INVALID_NAME_PREFIX")
        if not 1 <= ready_timeout_seconds <= 300:
            raise ValueError("INVALID_READY_TIMEOUT")
        self.client = client
        self.workspace = workspace
        self.name_prefix = name_prefix
        self.ready_timeout_seconds = ready_timeout_seconds

    def execute(self, request: SandboxRequest) -> dict:
        validate_request(request)
        name = f"{self.name_prefix}-{request.run_id}"
        if not SAFE_NAME.fullmatch(name):
            raise ContractViolation("SANDBOX_NAME_TOO_LONG")

        created = None
        deletion = None
        result = None
        execution_error = None
        cleanup_error = None
        try:
            created = self.client.create(workspace=self.workspace, name=name)
            actual_name = getattr(created, "name", name)
            if actual_name != name:
                raise RuntimeError("PROVIDER_NAME_MISMATCH")
            self.client.wait_ready(
                name,
                workspace=self.workspace,
                timeout_seconds=self.ready_timeout_seconds,
            )
            result = self.client.exec(
                name,
                list(request.command),
                workspace=self.workspace,
            )
        except Exception as exc:  # provider errors are evidence, not success
            execution_error = f"{type(exc).__name__}:{exc}"
        finally:
            if created is not None:
                try:
                    deletion = self.client.delete(name, workspace=self.workspace)
                    sandbox_id = getattr(deletion, "sandbox_id", None)
                    if not sandbox_id:
                        raise RuntimeError("MISSING_DELETION_SANDBOX_ID")
                    self.client.wait_deleted(
                        name,
                        workspace=self.workspace,
                        expected_sandbox_id=sandbox_id,
                    )
                except Exception as exc:
                    cleanup_error = f"{type(exc).__name__}:{exc}"

        stdout = getattr(result, "stdout", "") if result is not None else ""
        stderr = getattr(result, "stderr", "") if result is not None else ""
        exit_code = getattr(result, "exit_code", None) if result is not None else None
        status = "EXECUTED_IN_OPENSHELL"
        if execution_error is not None or exit_code != 0:
            status = "EXECUTION_FAILED"
        if cleanup_error is not None:
            status = "INCOMPLETE_CLEANUP"
        return {
            "status": status,
            "contract_version": CONTRACT_VERSION,
            "sandbox_name": name,
            "workspace": self.workspace,
            "command": list(request.command),
            "source_sha256": request.staged_source_sha256,
            "suite_sha256": request.staged_suite_sha256,
            "policy_sha256": request.policy_sha256,
            "exit_code": exit_code,
            "stdout": stdout,
            "stderr": stderr,
            "execution_error": execution_error,
            "cleanup_error": cleanup_error,
            "deleted": deletion is not None and cleanup_error is None,
        }
