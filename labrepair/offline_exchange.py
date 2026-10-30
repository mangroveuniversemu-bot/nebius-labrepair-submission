"""Single-use, bounded HTTP-contract rehearsal. No real HTTP transport exists."""

import argparse
import json
import os
import threading
import time
from dataclasses import dataclass
from pathlib import Path

from labrepair.candidate_review import digest, unique_object
from labrepair.paths import ROOT
from labrepair.provider_admission import MAX_EVIDENCE_BYTES, evaluate_admission
from labrepair.provider_envelope import (
    ENDPOINT,
    MAX_RESPONSE_BYTES,
    RequestDraft,
    prepare_request,
    review_offline_response,
)
from labrepair.q4_source import SOURCE_ROOT, SourceUnavailable

MAX_FIXTURE_BYTES = 131072
FAILURES = {
    "TIMEOUT": "TIMED_OUT_NO_RETRY",
    "CONNECTION": "CONNECTION_FAILED_NO_RETRY",
    "TLS": "TLS_VALIDATION_FAILED_NO_BYPASS",
}


def no_constant(_value):
    raise ValueError("NON_JSON_NUMBER")


def usage_counts(value):
    """Allowlist counts independently of proposal validity; still fixture-only."""
    names = ("prompt_tokens", "completion_tokens", "total_tokens")
    if not isinstance(value, dict):
        return "unknown"
    if not all(
        type(value.get(name)) is int and 0 <= value[name] <= 10**9 for name in names
    ):
        return "unknown"
    if value["total_tokens"] != value["prompt_tokens"] + value["completion_tokens"]:
        return "unknown"
    return {name: value[name] for name in names}


@dataclass(frozen=True)
class HTTPFixture:
    """Synthetic wire outcome, not a provider receipt or a live-enable grant."""

    status_code: int | None = None
    content_type: str = "application/json"
    body: bytes = b""
    failure: str | None = None

    def valid(self):
        if type(self.body) is not bytes or type(self.content_type) is not str:
            return False
        if self.failure is not None:
            return (
                type(self.failure) is str
                and self.failure in FAILURES
                and self.status_code is None
                and not self.body
            )
        return type(self.status_code) is int and 100 <= self.status_code <= 599


def parse_fixture(raw: bytes) -> HTTPFixture:
    if len(raw) > MAX_FIXTURE_BYTES:
        raise ValueError("FIXTURE_TOO_LARGE")
    try:
        data = json.loads(
            raw, object_pairs_hook=unique_object, parse_constant=no_constant
        )
        if not isinstance(data, dict):
            raise TypeError
        if set(data) == {"failure"}:
            fixture = HTTPFixture(failure=data["failure"])
        elif set(data) == {"status_code", "content_type", "body_utf8"}:
            if type(data["body_utf8"]) is not str:
                raise ValueError
            fixture = HTTPFixture(
                data["status_code"],
                data["content_type"],
                data["body_utf8"].encode("utf-8"),
            )
        else:
            raise ValueError
        if not fixture.valid():
            raise ValueError
        return fixture
    except (ValueError, UnicodeError, RecursionError, TypeError):
        # Never echo keys, headers, error bodies, account IDs or exception text.
        raise ValueError("INVALID_OFFLINE_FIXTURE") from None


def live_blocked_preview(draft: RequestDraft, evidence_raw: bytes | None = None) -> dict:
    """Evaluate separate evidence claims; never grant live dispatch or read keys."""
    admission = evaluate_admission(draft, evidence_raw)
    return {
        "mode": "DISABLED_LIVE_PREFLIGHT",
        "status": "BLOCKED",
        "reasons": admission["policy_reasons"] + admission["runtime_reasons"],
        "provider_admission": admission,
        "endpoint": ENDPOINT,
        "request_body_sha256": admission["request_body_sha256"],
        "actual_network_requests": 0,
        "actual_provider_usage": "unknown",
        "model": "NOT_RUN",
        "candidate_execution": "NOT_RUN",
        "credentials_accessed": False,
    }


class FixtureSession:
    """One simulated exchange, including failures; never accepts a client/key."""

    def __init__(self, journal_directory: Path | None = None):
        self._consumed = False
        self._lock = threading.Lock()
        self._journal_directory = journal_directory

    def _reserve_fixture(self, request_hash: str) -> bool:
        """Crash-conservative, optional durable reservation for synthetic tests.

        Directory creation is exclusive across sessions/processes. An empty,
        corrupt, interrupted or unknown reservation is never reused. This is
        not a provider intent, secret store or account-wide live dispatch lock.
        The caller owns the parent directory; do not delete it to retry.
        """
        if self._journal_directory is None:
            return True
        path = self._journal_directory
        try:
            if path.absolute() != path.resolve() or not path.parent.is_dir():
                return False
            path.mkdir(mode=0o700)  # No exist_ok: any prior state blocks reuse.
            with (path / "intent.json").open("x", encoding="utf-8") as stream:
                json.dump({"mode": "OFFLINE_FIXTURE_ONLY",
                           "state": "DISPATCH_UNKNOWN",
                           "request_body_sha256": request_hash}, stream)
                stream.flush()
                os.fsync(stream.fileno())
            for directory in (path, path.parent):
                fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)
                try:
                    os.fsync(fd)
                finally:
                    os.close(fd)
            return True
        except OSError:
            return False

    def rehearse(
        self, draft: RequestDraft, fixture: HTTPFixture, source_root: Path = SOURCE_ROOT
    ) -> dict:
        started = time.perf_counter()
        result = {
            "mode": "OFFLINE_HTTP_CONTRACT_REHEARSAL",
            "status": "REJECTED",
            "reasons": [],
            "endpoint": ENDPOINT,
            "method": "POST",
            "request_body_sha256": "unknown",
            "fixture_exchanges_this_call": 0,
            "fixture_exchanges_per_session_limit": 1,
            "automatic_retries": 0,
            "actual_network_requests": 0,
            "actual_provider_usage": "unknown",
            "fixture_reported_usage": "unknown",
            "http_status_fixture": "unknown",
            "response_sha256": "unknown",
            "response_read_bytes_fixture": "unknown",
            "local_elapsed_seconds": "unknown",
            "provider_elapsed_seconds": "unknown",
            "error_body_or_headers_recorded": False,
            "proposal_text_recorded": False,
            "credentials_accessed": False,
            "model": "NOT_RUN",
            "candidate_execution": "NOT_RUN",
            "source_written": False,
            "scientific_claim": "UNCHANGED_NOT_EVALUATED",
        }

        def finish(status, reason):
            result["status"] = status
            result["reasons"] = [reason]
            result["local_elapsed_seconds"] = time.perf_counter() - started
            return result

        if type(draft) is not RequestDraft or type(fixture) is not HTTPFixture:
            return finish("REJECTED", "INVALID_OFFLINE_TYPES")
        try:
            expected = prepare_request(draft.model_id, source_root)
        except (SourceUnavailable, ValueError):
            return finish("BLOCKED", "REQUEST_OR_SOURCE_UNAVAILABLE")
        if draft.body != expected.body:
            return finish("REJECTED", "REQUEST_BINDING_MISMATCH")
        result["request_body_sha256"] = digest(draft.body)
        if not fixture.valid():
            return finish("REJECTED", "INVALID_OFFLINE_FIXTURE")
        with self._lock:
            if self._consumed:
                return finish("BLOCKED", "FIXTURE_SESSION_ALREADY_CONSUMED")
            self._consumed = True
            if not self._reserve_fixture(result["request_body_sha256"]):
                return finish("BLOCKED", "DURABLE_FIXTURE_RESERVATION_UNAVAILABLE")
        result["fixture_exchanges_this_call"] = 1
        if fixture.failure is not None:
            return finish("FAILED", FAILURES[fixture.failure])
        status = fixture.status_code
        result["http_status_fixture"] = status
        raw = fixture.body[: MAX_RESPONSE_BYTES + 1]
        result["response_read_bytes_fixture"] = len(raw)
        if status != 200:
            if 300 <= status < 400:
                reason = "REDIRECT_REFUSED_NO_FOLLOW"
            elif status == 401:
                reason = "AUTHENTICATION_REQUIRED_NO_RETRY"
            elif status == 403:
                reason = "ACCESS_DENIED_NO_RETRY"
            elif status == 429:
                reason = "RATE_LIMITED_NO_RETRY"
            elif status >= 500:
                reason = "PROVIDER_ERROR_NO_RETRY"
            else:
                reason = "UNEXPECTED_HTTP_STATUS_NO_RETRY"
            # Never parse/persist provider error text or record zero billed usage.
            return finish("FAILED", reason)
        if len(raw) > MAX_RESPONSE_BYTES:
            result["bounded_prefix_sha256"] = digest(raw)
            return finish("REJECTED", "RESPONSE_TOO_LARGE_BOUNDED_PREFIX_ONLY")
        result["response_sha256"] = digest(raw)
        if fixture.content_type.partition(";")[0].strip().lower() != "application/json":
            return finish("REJECTED", "UNEXPECTED_CONTENT_TYPE")
        try:
            response = json.loads(
                raw, object_pairs_hook=unique_object, parse_constant=no_constant
            )
        except (ValueError, UnicodeError, RecursionError):
            return finish("REJECTED", "INVALID_RESPONSE_JSON")
        if isinstance(response, dict):
            result["fixture_reported_usage"] = usage_counts(response.get("usage"))
        intake = review_offline_response(raw, draft, source_root)
        # Model prose/diffs/unknown extensions are deliberately not copied here.
        result["candidate_intake"] = {
            "status": intake["status"],
            "reasons": intake["reasons"],
            "request_body_sha256": intake["request_body_sha256"],
            "execution": "NOT_RUN",
            "source_written": False,
        }
        result["status"] = intake["status"]
        result["reasons"] = intake["reasons"]
        result["local_elapsed_seconds"] = time.perf_counter() - started
        return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    inputs = parser.add_mutually_exclusive_group()
    inputs.add_argument("--fixture", type=Path)
    inputs.add_argument("--admission-evidence", type=Path)
    args = parser.parse_args()
    evidence_path = ROOT / "evidence"
    evidence = evidence_path.resolve()
    if evidence_path.is_symlink() or not evidence.is_relative_to(ROOT.resolve()):
        parser.error("evidence directory must stay inside this workspace without a symlink")
    targets = [args.output, *([args.fixture] if args.fixture else []),
               *([args.admission_evidence] if args.admission_evidence else [])]
    if any(not path.resolve().is_relative_to(evidence) for path in targets):
        parser.error("paths must remain inside this workspace's evidence folder")
    if args.output.exists():
        parser.error("use a new receipt path; existing evidence is not overwritten")
    try:
        draft = prepare_request()
        evidence_raw = None
        if args.admission_evidence:
            with args.admission_evidence.open("rb") as stream:
                evidence_raw = stream.read(MAX_EVIDENCE_BYTES + 1)
        result = live_blocked_preview(draft, evidence_raw)
        if args.fixture:
            with args.fixture.open("rb") as stream:
                raw = stream.read(MAX_FIXTURE_BYTES + 1)
            result = FixtureSession().rehearse(draft, parse_fixture(raw))
    except (SourceUnavailable, ValueError, OSError):
        result = {
            "mode": "DISABLED_LIVE_PREFLIGHT",
            "status": "BLOCKED",
            "reasons": ["REQUEST_SOURCE_OR_FIXTURE_UNAVAILABLE"],
            "model": "NOT_RUN",
            "actual_provider_usage": "unknown",
        }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))
    return 2  # Offline verification is never dispatch/repair approval.


if __name__ == "__main__":
    raise SystemExit(main())
