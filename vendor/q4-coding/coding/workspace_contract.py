"""Frozen staging and recovery evidence for the reviewed coding fixture.

This module prepares deterministic evidence for a future real OpenShell run.
It does not create a sandbox, upload files, or execute candidate source. The
workspace is limited to three reviewed fixture files and a deny-network policy.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import re
from typing import Mapping

from coding.patch_review import BASELINE, CASES, RUNNER
from coding.sandbox_adapter import CONTRACT_VERSION, REQUIRED_COMMAND


HEX_256 = re.compile(r"^[0-9a-f]{64}$")
MANIFEST_VERSION = "coding-review-workspace-v1"
POLICY_VERSION = "coding-review-policy-v1"
ALLOWED_PATHS = ("cases.json", "ledger.py", "runner.py")
MAX_FILE_BYTES = 64 * 1024

FROZEN_POLICY = {
    "version": POLICY_VERSION,
    "network": "DENY_ALL",
    "filesystem": {
        "root": "/workspace/review",
        "allowed_paths": list(ALLOWED_PATHS),
        "unexpected_paths": "DENY",
    },
    "process": {
        "command": list(REQUIRED_COMMAND),
        "shell": False,
        "tty": False,
        "timeout_seconds": 30,
    },
    "credentials": "NONE",
    "local_fallback": "FORBIDDEN",
}


class WorkspaceContractViolation(ValueError):
    """Raised before staging when the exact reviewed workspace changes."""


def _canonical_json(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def policy_sha256(policy: Mapping[str, object] = FROZEN_POLICY) -> str:
    return sha256_bytes(_canonical_json(policy))


def reviewed_workspace(source: str = BASELINE) -> dict[str, bytes]:
    """Return the exact three UTF-8 fixture files intended for pre-staging."""
    return {
        "cases.json": json.dumps(CASES, sort_keys=True).encode(),
        "ledger.py": source.encode(),
        "runner.py": RUNNER.encode(),
    }


def build_manifest(files: Mapping[str, bytes]) -> dict:
    if tuple(sorted(files)) != ALLOWED_PATHS:
        raise WorkspaceContractViolation("WORKSPACE_PATH_SET_CHANGED")

    entries = []
    for path in ALLOWED_PATHS:
        content = files[path]
        if not isinstance(content, bytes):
            raise WorkspaceContractViolation("NON_BYTES_WORKSPACE_ENTRY")
        if not content or len(content) > MAX_FILE_BYTES:
            raise WorkspaceContractViolation("INVALID_WORKSPACE_ENTRY_SIZE")
        entries.append({
            "path": path,
            "size_bytes": len(content),
            "sha256": sha256_bytes(content),
            "mode": "read_only",
        })

    policy_digest = policy_sha256()
    unsigned = {
        "manifest_version": MANIFEST_VERSION,
        "sandbox_contract_version": CONTRACT_VERSION,
        "policy_version": POLICY_VERSION,
        "policy_sha256": policy_digest,
        "command": list(REQUIRED_COMMAND),
        "files": entries,
        "staging_status": "PRE_STAGED_FIXTURE_ONLY",
        "live_validation": "NOT_RUN",
    }
    return {**unsigned, "manifest_sha256": sha256_bytes(_canonical_json(unsigned))}


@dataclass(frozen=True)
class RecoveryExpectation:
    manifest_sha256: str
    source_sha256: str
    suite_sha256: str
    policy_sha256: str


def recovery_receipt(
    provider_result: Mapping[str, object],
    expectation: RecoveryExpectation,
    *,
    current_source_sha256: str,
    candidate_applied: bool,
) -> dict:
    """Verify cleanup and rollback evidence without applying the candidate."""
    for value in (
        expectation.manifest_sha256,
        expectation.source_sha256,
        expectation.suite_sha256,
        expectation.policy_sha256,
        current_source_sha256,
    ):
        if not HEX_256.fullmatch(value):
            raise WorkspaceContractViolation("INVALID_RECOVERY_DIGEST")
    checks = {
        "provider_execution_succeeded": provider_result.get("status") == "EXECUTED_IN_OPENSHELL",
        "sandbox_deleted": provider_result.get("deleted") is True,
        "source_binding_matches": provider_result.get("source_sha256") == expectation.source_sha256,
        "suite_binding_matches": provider_result.get("suite_sha256") == expectation.suite_sha256,
        "policy_binding_matches": provider_result.get("policy_sha256") == expectation.policy_sha256,
        "manifest_binding_matches": provider_result.get("manifest_sha256") == expectation.manifest_sha256,
        "base_source_restored": current_source_sha256 == expectation.source_sha256,
        "candidate_not_applied": candidate_applied is False,
    }
    status = "RECOVERY_VERIFIED" if all(checks.values()) else "RECOVERY_INCOMPLETE"
    body = {
        "status": status,
        "manifest_version": MANIFEST_VERSION,
        "expectation": asdict(expectation),
        "checks": checks,
        "candidate_applied": candidate_applied,
        "live_validation": "NOT_RUN" if provider_result.get("fixture") else "PROVIDER_RESULT",
    }
    return {**body, "receipt_sha256": sha256_bytes(_canonical_json(body))}


def contract_summary() -> dict:
    manifest = build_manifest(reviewed_workspace())
    return {
        "manifest_version": MANIFEST_VERSION,
        "policy_version": POLICY_VERSION,
        "allowed_paths": list(ALLOWED_PATHS),
        "manifest_sha256": manifest["manifest_sha256"],
        "policy_sha256": manifest["policy_sha256"],
        "network": "DENY_ALL",
        "unexpected_paths": "DENY",
        "local_fallback": "FORBIDDEN",
        "live_validation": "NOT_RUN",
    }
