"""Fail-closed, credential-free evaluation of provider/cost evidence claims.

This is an offline policy evaluator, not evidence authentication or a transport.
Even complete evidence claims never grant runtime admission in this prototype.
"""

import json
import re
from datetime import datetime, timedelta, timezone
from decimal import Decimal, localcontext

from labrepair.candidate_review import canonical_digest, digest, unique_object
from labrepair.provider_envelope import (
    ENDPOINT, MAX_INPUT_TOKENS, MAX_OUTPUT_TOKENS, MAX_CREDIT_COST_USD,
    SDK_MAX_RETRIES, TIMEOUT_SECONDS, RequestDraft, prepare_request,
)
from labrepair.paths import ROOT
from labrepair.q4_source import SourceUnavailable

SCHEMA = "LABREPAIR_PROVIDER_ADMISSION_V1"
PROVIDER = "nebius_token_factory"
MAX_EVIDENCE_BYTES = 16384
MAX_EVIDENCE_AGE = timedelta(minutes=15)
MAX_ACTUAL_CASH_USD = "0"
SHA256 = re.compile(r"[0-9a-f]{64}\Z")
# Bounded decimal strings only: no floats, exponents, signs, NaN or Infinity.
USD = re.compile(r"(?:0|[1-9][0-9]{0,8})(?:\.[0-9]{1,12})?\Z")
UTC_TIME = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z\Z")

SECTION_FIELDS = {
    "pricing": {
        "verified", "currency", "input_usd_per_million_tokens",
        "output_usd_per_million_tokens", "input_token_bound_verified",
        "max_input_tokens", "max_output_tokens", "max_requests",
        "all_fees_included", "entire_request_token_bound_verified",
        "completion_includes_reasoning_verified",
    },
    "credits": {
        "verified", "currency", "remaining_usd", "covers_this_request",
    },
    "cash_controls": {
        "verified", "currency", "max_actual_cash_usd", "provider_hard_stop",
        "fail_closed_on_credit_exhaustion", "automatic_top_up",
        "overage_charging", "pay_as_you_go",
    },
    "permissions": {
        "credential_use_approved", "model_access_verified",
        "schema_support_verified", "isolated_backend_verified",
    },
}
PROVENANCE_FIELDS = {"scope_sha256", "source_sha256"}
SCOPE_FIELDS = {
    "provider", "endpoint", "model_id", "request_body_sha256", "account_scope_sha256",
}
ROOT_FIELDS = {
    "schema", "evidence_kind", "scope", "checked_at_utc", "expires_at_utc",
    *SECTION_FIELDS,
}


def _non_json_number(_value):
    raise ValueError("NON_JSON_NUMBER")


def _keys(value, expected):
    return type(value) is dict and set(value) == expected


def _sha(value):
    return type(value) is str and SHA256.fullmatch(value) is not None


def _usd(value):
    return Decimal(value) if type(value) is str and USD.fullmatch(value) else None


def _utc(value):
    if type(value) is not str or not UTC_TIME.fullmatch(value):
        raise ValueError("INVALID_UTC_TIME")
    return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


def evaluate_admission(
    draft: RequestDraft, evidence_raw: bytes | None = None, *, now: datetime | None = None,
    dispatch_state: str = "NEW"
) -> dict:
    """Inspect bounded claims; return sanitized reasons, never a dispatch grant.

    Evidence must be supplied separately by the operator, not from a response or
    candidate. Hashes prove binding/integrity only. No account, key or network is
    accessed, and neither SYNTHETIC_FIXTURE nor OPERATOR_ASSERTION is trusted.
    """
    report = {
        "schema": SCHEMA,
        "mode": "OFFLINE_PROVIDER_ADMISSION_EVALUATION",
        "status": "BLOCKED",
        "policy_evaluation": "BLOCKED",
        "policy_reasons": [],
        "runtime_admission": "BLOCKED",
        "runtime_reasons": [
            "INDEPENDENT_ACCOUNT_EVIDENCE_NOT_AUTHENTICATED",
            "LIVE_HTTP_TRANSPORT_NOT_IMPLEMENTED",
        ],
        "evidence_kind": "unknown",
        "evidence_sha256": None,
        "request_body_sha256": None,
        "maximum_authorized_actual_cash_usd": MAX_ACTUAL_CASH_USD,
        "claimed_request_cost_upper_bound_usd": "unknown",
        "actual_provider_usage": "unknown",
        "actual_provider_cost": "unknown",
        "actual_provider_latency": "unknown",
        "model": "NOT_RUN",
        "candidate_execution": "NOT_RUN",
        "credentials_accessed": False,
        "actual_network_requests": 0,
    }

    def blocked(reason):
        report["policy_reasons"].append(reason)
        return report

    if type(dispatch_state) is not str or dispatch_state != "NEW":
        return blocked("DISPATCH_ALREADY_RESERVED_SENT_OR_UNKNOWN")
    if not bounded_config_valid():
        return blocked("BOUNDED_RUNTIME_CONFIG_INVALID")
    if type(draft) is not RequestDraft or type(draft.body) is not bytes:
        return blocked("INVALID_REQUEST_DRAFT")
    try:
        expected = prepare_request(draft.model_id)
    except (SourceUnavailable, ValueError, TypeError, OSError):
        return blocked("REQUEST_OR_SOURCE_UNAVAILABLE")
    if draft.body != expected.body:
        return blocked("REQUEST_BINDING_MISMATCH")
    report["request_body_sha256"] = digest(draft.body)
    if evidence_raw is None:
        return blocked("ADMISSION_EVIDENCE_MISSING")
    if type(evidence_raw) is not bytes:
        return blocked("INVALID_ADMISSION_EVIDENCE_TYPE")
    if len(evidence_raw) > MAX_EVIDENCE_BYTES:
        return blocked("ADMISSION_EVIDENCE_TOO_LARGE")
    report["evidence_sha256"] = digest(evidence_raw)
    try:
        data = json.loads(
            evidence_raw.decode("utf-8"),
            object_pairs_hook=unique_object,
            parse_constant=_non_json_number,
        )
    except (ValueError, UnicodeError, RecursionError):
        return blocked("INVALID_ADMISSION_EVIDENCE_JSON")
    if (
        not _keys(data, ROOT_FIELDS)
        or data["schema"] != SCHEMA
        or data["evidence_kind"] not in ("SYNTHETIC_FIXTURE", "OPERATOR_ASSERTION")
        or not _keys(data["scope"], SCOPE_FIELDS)
        or any(not _keys(data[name], fields | PROVENANCE_FIELDS)
               for name, fields in SECTION_FIELDS.items())
    ):
        return blocked("INVALID_ADMISSION_EVIDENCE_SCHEMA")
    report["evidence_kind"] = data["evidence_kind"]
    scope = data["scope"]
    if (
        scope["provider"] != PROVIDER
        or scope["endpoint"] != ENDPOINT
        or scope["model_id"] != draft.model_id
        or scope["request_body_sha256"] != report["request_body_sha256"]
        or not _sha(scope["account_scope_sha256"])
    ):
        return blocked("ADMISSION_SCOPE_MISMATCH")
    scope_hash = canonical_digest(scope)
    if any(
        data[name]["scope_sha256"] != scope_hash
        or not _sha(data[name]["source_sha256"])
        for name in SECTION_FIELDS
    ):
        return blocked("SECTION_EVIDENCE_BINDING_MISMATCH")
    try:
        current = datetime.now(timezone.utc) if now is None else now
        if type(current) is not datetime or current.utcoffset() is None:
            raise ValueError("INVALID_CLOCK")
        checked = _utc(data["checked_at_utc"])
        expires = _utc(data["expires_at_utc"])
        fresh = checked <= current < expires and expires - checked <= MAX_EVIDENCE_AGE
    except (ValueError, TypeError, OverflowError):
        return blocked("INVALID_EVIDENCE_TIME")
    if not fresh:
        return blocked("STALE_OR_FUTURE_ADMISSION_EVIDENCE")

    pricing, credits, cash, permissions = (data[name] for name in SECTION_FIELDS)
    rates = [_usd(pricing[name]) for name in (
        "input_usd_per_million_tokens", "output_usd_per_million_tokens"
    )]
    prices_valid = (
        pricing["verified"] is True
        and pricing["currency"] == "USD"
        and pricing["input_token_bound_verified"] is True
        and pricing["all_fees_included"] is True
        and pricing["entire_request_token_bound_verified"] is True
        and pricing["completion_includes_reasoning_verified"] is True
        and all(rate is not None for rate in rates)
        and type(pricing["max_input_tokens"]) is int
        and 1 <= pricing["max_input_tokens"] <= MAX_INPUT_TOKENS
        and type(pricing["max_output_tokens"]) is int
        and pricing["max_output_tokens"] == MAX_OUTPUT_TOKENS
        and json.loads(draft.body)["max_completion_tokens"] == MAX_OUTPUT_TOKENS
        and type(pricing["max_requests"]) is int
        and pricing["max_requests"] == 1
    )
    if not prices_valid:
        blocked("VERIFIED_PRICING_OR_REQUEST_BOUND_MISSING")
    else:
        # Enough precision for every accepted bounded decimal/token input.
        with localcontext() as context:
            context.prec = 50
            upper = (rates[0] * pricing["max_input_tokens"]
                     + rates[1] * pricing["max_output_tokens"]) / Decimal(1_000_000)
        report["claimed_request_cost_upper_bound_usd"] = format(upper, "f")
        if upper > Decimal(MAX_CREDIT_COST_USD):
            blocked("CREDIT_COST_EXCEEDS_ONE_CENT")

    remaining = _usd(credits["remaining_usd"])
    credits_valid = (
        credits["verified"] is True
        and credits["currency"] == "USD"
        and credits["covers_this_request"] is True
        and remaining is not None
    )
    if not credits_valid:
        blocked("COVERED_FREE_CREDITS_UNVERIFIED")
    elif prices_valid and remaining < upper:
        blocked("INSUFFICIENT_COVERED_FREE_CREDITS")
    if (
        cash["verified"] is not True
        or cash["currency"] != "USD"
        or _usd(cash["max_actual_cash_usd"]) != Decimal(MAX_ACTUAL_CASH_USD)
        or cash["provider_hard_stop"] is not True
        or cash["fail_closed_on_credit_exhaustion"] is not True
    ):
        blocked("ENFORCEABLE_ZERO_CASH_CAP_UNVERIFIED")
    if any(cash[name] is not False for name in (
        "automatic_top_up", "overage_charging", "pay_as_you_go"
    )):
        blocked("AUTOMATIC_CHARGING_NOT_VERIFIED_DISABLED")
    for field, reason in (
        ("credential_use_approved", "CREDENTIAL_USE_PERMISSION_MISSING"),
        ("model_access_verified", "MODEL_ENTITLEMENT_UNVERIFIED"),
        ("schema_support_verified", "MODEL_SCHEMA_SUPPORT_UNVERIFIED"),
        ("isolated_backend_verified", "ISOLATED_BACKEND_UNVERIFIED"),
    ):
        if permissions[field] is not True:
            blocked(reason)
    if not report["policy_reasons"]:
        report["policy_evaluation"] = "CLAIMS_SATISFY_POLICY"
    return report


def bounded_config_valid() -> bool:
    """Config is an enforced refusal condition, never an authorization source.

    Env templates cannot override these reviewed hard limits. No SDK/HTTP
    transport exists, so timeout/retry options are validated, not claimed live.
    """
    try:
        data = json.loads((ROOT / "config/providers.json").read_text(),
                          object_pairs_hook=unique_object)
        expected = {
            "max_requests": 1, "max_input_tokens": MAX_INPUT_TOKENS,
            "max_completion_tokens": MAX_OUTPUT_TOKENS,
            "output_includes_reasoning": True, "sdk_max_retries": SDK_MAX_RETRIES,
            "timeout_seconds": TIMEOUT_SECONDS,
            "max_credit_cost_usd": MAX_CREDIT_COST_USD, "max_new_cash_usd": "0",
            "input_accounting": "entire_request_including_schema_and_template",
            "dispatch_enabled": False,
        }
        policy = data.get("bounded_test_policy")
        return (data.get("live_enabled") is False and type(policy) is dict
                and policy.keys() == expected.keys()
                and all(type(policy[k]) is type(v) and policy[k] == v
                        for k, v in expected.items()))
    except (OSError, ValueError, TypeError, RecursionError):
        return False
