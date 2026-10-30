"""Treat a provider's JSON parameters as data, then independently review them.

This module has no network client, credential access, source writer or candidate
executor. Replaying an archived response does not prove it came from a provider;
the separately recorded transport receipt supplies the observed-call evidence.
"""
import json

from labrepair.candidate_review import digest, unique_object
from labrepair.scientific_workflow import (
    ScienceReviewError, encode, load_fixture, review_proposal,
)


def review_parameter_text(raw: bytes):
    if not isinstance(raw, bytes) or len(raw) > 4096:
        raise ScienceReviewError("MODEL_PARAMETER_SIZE_OR_TYPE")
    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=unique_object)
        if not isinstance(value, dict) or set(value) != {"channel_signs", "offsets"}:
            raise ValueError
        for name in ("channel_signs", "offsets"):
            items = value[name]
            if not isinstance(items, list) or len(items) != 4:
                raise ValueError
            if any(type(item) is not int or abs(item) > 1 for item in items):
                raise ValueError
        if any(item not in (-1, 1) for item in value["channel_signs"]):
            raise ValueError
    except (UnicodeError, ValueError, TypeError, RecursionError) as exc:
        raise ScienceReviewError("INVALID_MODEL_PARAMETER_JSON") from exc
    files, _, contract = load_fixture()
    lines = files["analysis.py"].decode().splitlines(keepends=True)
    lines[0] = "CHANNEL_SIGNS = " + str(tuple(value["channel_signs"])) + "\n"
    lines[1] = "OFFSETS = " + str(tuple(value["offsets"])) + "\n"
    proposal = {
        "snapshot_sha256": contract.snapshot_sha256,
        "policy_sha256": contract.policy_sha256,
        "replacements": [{
            "path": "analysis.py", "before_sha256": digest(files["analysis.py"]),
            "after_utf8": "".join(lines),
        }],
    }
    result = review_proposal(encode(proposal), proposal_origin="UNTRUSTED_PROVIDER_PARAMETER_TEXT")
    return {
        "schema": "LABREPAIR_MODEL_PARAMETER_REVIEW_V1",
        "model_text_sha256": digest(raw),
        "parameters": value,
        "operator_bound_proposal": proposal,
        "local_review": result,
        "reviewer_network_requests": 0,
        "candidate_execution": "NOT_RUN",
        "provider_generation": "NOT_ATTESTED_BY_OFFLINE_REPLAY",
        "claim_promotion": "FORBIDDEN_FROM_REPAIR_RESULT",
    }


def review_chat_response(raw: bytes):
    """Strictly intake one completed response; never act on tools or prose."""
    if not isinstance(raw, bytes) or len(raw) > 65536:
        raise ScienceReviewError("PROVIDER_RESPONSE_SIZE_OR_TYPE")
    try:
        response = json.loads(raw.decode("utf-8"), object_pairs_hook=unique_object)
        choices = response["choices"]
        if not isinstance(choices, list) or len(choices) != 1:
            raise ValueError
        choice = choices[0]
        message = choice["message"]
        if choice["finish_reason"] != "stop" or message["role"] != "assistant":
            raise ValueError
        if message.get("tool_calls") or message.get("function_call") or message.get("refusal"):
            raise ValueError
        content = message["content"]
        if not isinstance(content, str):
            raise ValueError
    except (KeyError, IndexError, UnicodeError, ValueError, TypeError, RecursionError) as exc:
        raise ScienceReviewError("UNUSABLE_PROVIDER_RESPONSE") from exc
    result = review_parameter_text(content.encode("utf-8"))
    result.update(provider_response_sha256=digest(raw), returned_model=response.get("model", "unknown"), reported_usage=response.get("usage", "unknown"))
    return result
