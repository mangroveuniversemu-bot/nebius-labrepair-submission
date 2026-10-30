"""One explicit Token Factory call for the fixed synthetic repair request.

Preview never reads a key. Live calls require the operator's billing consent;
this acknowledgement is not a provider-enforced spending cap. No candidate code
or Sandbox job is executed. Responses enter the existing deterministic reviewer.
"""
import hashlib
import json
import os
import re
import time
from http.client import HTTPException
from datetime import datetime, timezone
from pathlib import Path
from urllib import error, request

from labrepair.model_parameters import review_chat_response
from labrepair.daily_budget import DEFAULT_STATE_PATH, DailyBudgetError, reserve, status as budget_status
from labrepair.paths import ROOT
from labrepair.scientific_workflow import ScienceReviewError

ENDPOINT = "https://api.tokenfactory.nebius.com/v1/chat/completions"
MODEL = "nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B"
REQUEST_FILE = ROOT / "evidence/nebius-nano-repair-20261026-1/request.json"
REQUEST_SHA256 = "03f944bb8d8bc9b27df6fc9b44689eb65c4d2be025600870ed55e14010acf6da"
MAX_RESPONSE_BYTES = 65536
TIMEOUT_SECONDS = 30
RUN_ROOT = ROOT / ".live-runs"


class LiveRepairError(ValueError):
    pass


def budget_path(output_root=RUN_ROOT):
    # Production deployments must share this ONE path across all checkouts.
    # A custom output_root is for isolated local tests, not a second production cap.
    if Path(output_root) != RUN_ROOT:
        return Path(output_root) / "budget.sqlite"
    return Path(os.environ.get("LABREPAIR_BUDGET_STATE", str(DEFAULT_STATE_PATH)))


def live_status():
    path = budget_path()
    return {**budget_status(path), "disabled": (path.parent / "DISABLED").exists()}


class NoRedirect(request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None  # Never forward a credential or POST to another location.


def fixed_request():
    raw = REQUEST_FILE.read_bytes()
    if hashlib.sha256(raw).hexdigest() != REQUEST_SHA256:
        raise LiveRepairError("PINNED_REQUEST_CHANGED")
    body = json.loads(raw)
    if not (body["model"] == MODEL and body["max_completion_tokens"] == 64
            and body["n"] == 1 and body["stream"] is False and body["store"] is False):
        raise LiveRepairError("PINNED_REQUEST_LIMITS_CHANGED")
    return raw


def preview():
    raw = fixed_request()
    return {"mode": "PREVIEW", "endpoint": ENDPOINT, "model": MODEL,
            "request_sha256": hashlib.sha256(raw).hexdigest(),
            "max_completion_tokens": 64, "max_attempts": 1, "retries": 0,
            "timeout_seconds": TIMEOUT_SECONDS, "network_requests": 0,
            "daily_max_calls": 5, "daily_reservation_usd": "0.05",
            "reserve_usd_per_attempt": "0.01", "day_timezone": "Asia/Taipei",
            "credentials_accessed": False, "monetary_cap": "NOT_ENFORCED_BY_TOKEN_LIMIT"}


def _json_file(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8", newline="\n")


def run_live(*, confirm_provider_billing, run_id, output_root=RUN_ROOT):
    if not confirm_provider_billing:
        raise LiveRepairError("OPERATOR_BILLING_CONFIRMATION_REQUIRED")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", run_id):
        raise LiveRepairError("INVALID_RUN_ID")
    raw = fixed_request()  # Verify source before accessing a credential.
    ledger = budget_path(output_root)
    if (ledger.parent / "DISABLED").exists():
        raise LiveRepairError("LIVE_DISABLED_BY_OPERATOR")
    key = os.environ.get("NEBIUS_API_KEY", "")
    if not key or len(key) > 4096 or any(ord(c) < 33 or ord(c) > 126 for c in key):
        raise LiveRepairError("NEBIUS_API_KEY_MISSING_OR_INVALID")
    destination = Path(output_root) / run_id
    if any(p.is_symlink() for p in (destination, *destination.parents)):
        raise LiveRepairError("SYMLINK_OUTPUT_FORBIDDEN")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.mkdir(exist_ok=False)  # A run ID is never overwritten/retried.
    reservation = reserve(ledger, run_id)
    if not reservation["request_slot_granted"]:
        raise LiveRepairError("DUPLICATE_BUDGET_RESERVATION")
    (destination / "request.json").write_bytes(raw)
    receipt = {"schema": "LABREPAIR_DIRECT_TOKEN_FACTORY_V1", "run_id": run_id,
               "created_utc": datetime.now(timezone.utc).isoformat(),
               "endpoint": ENDPOINT, "model": MODEL,
               "request_sha256": REQUEST_SHA256, "max_completion_tokens": 64,
               "attempted_count": 0, "retries": 0, "http_status": "unknown",
               "network_timeout_seconds": TIMEOUT_SECONDS,
               "daily_budget_reservation": reservation,
               "usage": "unknown", "actual_billed_currency": "unknown",
               "status": "FAILED", "candidate_execution": "NOT_RUN",
               "sandbox_execution": "NOT_RUN", "scientific_claim": "NOT_REPRODUCED",
               "provenance": "Client-observed transport; not a provider signature"}
    started = time.perf_counter()
    try:
        client = request.build_opener(NoRedirect())
        outgoing = request.Request(ENDPOINT, data=raw, method="POST", headers={
            "Authorization": "Bearer " + key, "Content-Type": "application/json",
            "Accept": "application/json", "User-Agent": "LabRepair/0.1"})
        receipt["attempted_count"] = 1
        with client.open(outgoing, timeout=TIMEOUT_SECONDS) as response:
            receipt["http_status"] = response.status
            if response.status != 200:
                raise LiveRepairError("UNEXPECTED_HTTP_STATUS")
            returned = response.read(MAX_RESPONSE_BYTES + 1)
        if len(returned) > MAX_RESPONSE_BYTES:
            raise LiveRepairError("RESPONSE_TOO_LARGE")
        parsed = json.loads(returned)
        if key in json.dumps(parsed, ensure_ascii=False):
            raise LiveRepairError("SECRET_ECHO_REJECTED")
        if parsed.get("model") != MODEL:
            raise LiveRepairError("RESPONSE_MODEL_MISMATCH")
        (destination / "response.json").write_bytes(returned)
        receipt["response_sha256"] = hashlib.sha256(returned).hexdigest()
        review = review_chat_response(returned)
        _json_file(destination / "local-review.json", review)
        usage = parsed.get("usage", {})
        fields = ("prompt_tokens", "completion_tokens", "total_tokens")
        if (isinstance(usage, dict)
                and all(type(usage.get(f)) is int and usage[f] >= 0 for f in fields)
                and usage["total_tokens"] == usage["prompt_tokens"] + usage["completion_tokens"]):
            receipt["usage"] = {f: usage[f] for f in fields}
        receipt["status"] = ("MODEL_REPAIR_VERIFIED" if review["local_review"]["local_result"]
                             == "LOCAL_SEMANTIC_MATCH" else "MODEL_REPAIR_REJECTED")
        receipt["local_review_sha256"] = hashlib.sha256((destination / "local-review.json").read_bytes()).hexdigest()
    except error.HTTPError as exc:
        receipt.update(http_status=exc.code, reason="HTTP_ERROR_NO_RETRY")
        exc.close()  # Do not print or persist error bodies/headers/credentials.
    except (error.URLError, TimeoutError, OSError, HTTPException):
        receipt["reason"] = "TRANSPORT_ERROR_NO_RETRY"
    except (ScienceReviewError, LiveRepairError) as exc:
        receipt["reason"] = str(exc)  # Controlled local error codes only.
    except (ValueError, TypeError, KeyError, AttributeError, RecursionError):
        receipt["reason"] = "INVALID_PROVIDER_RESPONSE"
    finally:
        receipt["elapsed_seconds"] = round(time.perf_counter() - started, 4)
        _json_file(destination / "transport-receipt.json", receipt)
    return receipt
