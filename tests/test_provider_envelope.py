"""Offline provider envelope checks; no model response or token use is measured."""

import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from labrepair.candidate_review import digest
from labrepair.provider_envelope import (
    ENDPOINT,
    MAX_RESPONSE_BYTES,
    MODEL_CANDIDATE,
    RequestDraft,
    encoded,
    prepare_request,
    review_offline_response,
)
from labrepair.q4_pins import PINNED_FILES
from labrepair.q4_source import SOURCE_ROOT, load_source, verify_import


def response_fixture():
    source = load_source()
    proposal = {
        "snapshot_sha256": source.contract.snapshot_sha256,
        "policy_sha256": source.contract.policy_sha256,
        "replacements": [
            {
                "path": "ledger.py",
                "before_sha256": digest(dict(source.contract.originals)["ledger.py"]),
                "after_utf8": source.correct_literal_fixture,
            }
        ],
    }
    return {
        "model": MODEL_CANDIDATE,
        "choices": [
            {
                "index": 0,
                "finish_reason": "stop",
                "message": {
                    "role": "assistant",
                    "content": json.dumps(proposal),
                },
            }
        ],
    }


class ProviderEnvelopeTests(unittest.TestCase):
    def setUp(self):
        self.draft = prepare_request()

    def review(self, response):
        return review_offline_response(encoded(response), self.draft)

    def test_preview_is_bounded_and_excludes_solution_keys_and_dispatch(self):
        source = load_source()
        body = json.loads(self.draft.body)
        data = json.loads(body["messages"][1]["content"])
        self.assertEqual(body["model"], MODEL_CANDIDATE)
        self.assertEqual(body["max_completion_tokens"], 256)
        self.assertFalse(body["stream"])
        self.assertEqual(body["n"], 1)
        self.assertNotIn("tools", body)
        self.assertNotIn(source.correct_literal_fixture, self.draft.body.decode())
        self.assertEqual(
            [item["path"] for item in data["files"]],
            ["cases.json", "ledger.py", "runner.py"],
        )
        self.assertEqual(
            [item["editable"] for item in data["files"]], [False, True, False]
        )
        self.assertEqual(
            tuple(
                (item["path"], item["content_utf8"].encode()) for item in data["files"]
            ),
            source.contract.originals,
        )
        self.assertEqual(data["bindings"]["suite_sha256"], source.suite_sha256)
        info = self.draft.receipt()
        self.assertEqual(info["endpoint"], ENDPOINT)
        self.assertEqual(info["dispatch"], "NOT_IMPLEMENTED")
        self.assertLess(info["body_bytes"], info["request_limit_bytes"])
        self.assertEqual(info["actual_provider_usage"], "unknown")
        self.assertFalse(info["credentials_accessed"])
        self.assertEqual(info["model_id_and_schema_support"], "UNVERIFIED")

    def test_known_literal_response_stays_blocked_without_execution(self):
        originals = verify_import()
        result = self.review(response_fixture())
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(
            result["reasons"],
            ["ISOLATED_BACKEND_UNVERIFIED", "SPENDING_LIMIT_UNVERIFIED"],
        )
        self.assertEqual(len(result["candidate_review"]["changes"]), 1)
        self.assertFalse(result["source_written"])
        self.assertEqual(result["model"], "NOT_RUN")
        self.assertEqual(result["fixture_reported_usage"], "unknown")
        self.assertEqual(verify_import(), originals)

    def test_tool_calls_and_refusals_are_not_candidates(self):
        for key, value, reason in (
            ("tool_calls", [{"function": {"name": "run"}}], "TOOL_CALL_FORBIDDEN"),
            ("function_call", {"name": "exec"}, "TOOL_CALL_FORBIDDEN"),
            ("refusal", "no", "MODEL_REFUSAL"),
        ):
            with self.subTest(key=key):
                data = response_fixture()
                data["choices"][0]["message"][key] = value
                self.assertEqual(self.review(data)["reasons"], [reason])

    def test_truncated_multiple_and_wrong_role_model_are_rejected(self):
        for field, value, reason in (
            ("finish_reason", "length", "INCOMPLETE_OR_NONSTOP_RESPONSE"),
            ("index", True, "INVALID_CHOICE_INDEX"),
        ):
            data = response_fixture()
            data["choices"][0][field] = value
            self.assertEqual(self.review(data)["reasons"], [reason])
        data = response_fixture()
        data["choices"].append(data["choices"][0])
        self.assertEqual(self.review(data)["reasons"], ["INVALID_CHOICE_COUNT"])
        data = response_fixture()
        data["choices"][0]["message"]["role"] = "system"
        self.assertEqual(self.review(data)["reasons"], ["INVALID_ASSISTANT_MESSAGE"])
        data = response_fixture()
        data["model"] = "unverified-other-model"
        self.assertEqual(self.review(data)["reasons"], ["MODEL_BINDING_MISMATCH"])

    def test_duplicate_malformed_deep_and_nonjson_numbers_are_rejected(self):
        for raw in (
            b'{"model":1,"model":2}',
            b"NaN",
            b"not-json",
            b"[" * 2000 + b"]" * 2000,
            b"\xff",
        ):
            result = review_offline_response(raw, self.draft)
            self.assertEqual(result["status"], "REJECTED")

    def test_byte_limits_surrogates_and_nonstring_content_fail_closed(self):
        result = review_offline_response(b"x" * (MAX_RESPONSE_BYTES + 1), self.draft)
        self.assertEqual(result["reasons"], ["RESPONSE_TOO_LARGE"])
        for value, reason in (
            (None, "MISSING_PROPOSAL_CONTENT"),
            ("x" * 32769, "PROPOSAL_TOO_LARGE"),
            ("\ud800", "INVALID_CONTENT_ENCODING"),
        ):
            data = response_fixture()
            data["choices"][0]["message"]["content"] = value
            self.assertEqual(self.review(data)["reasons"], [reason])

    def test_protected_files_and_stale_policy_survive_provider_wrapping(self):
        for path in ("cases.json", "runner.py"):
            data = response_fixture()
            proposal = json.loads(data["choices"][0]["message"]["content"])
            proposal["replacements"][0]["path"] = path
            data["choices"][0]["message"]["content"] = json.dumps(proposal)
            self.assertEqual(self.review(data)["reasons"], ["PROTECTED_FILE_CHANGE"])
        data = response_fixture()
        proposal = json.loads(data["choices"][0]["message"]["content"])
        proposal["policy_sha256"] = "0" * 64
        data["choices"][0]["message"]["content"] = json.dumps(proposal)
        self.assertEqual(self.review(data)["reasons"], ["POLICY_BINDING_MISMATCH"])

    def test_model_readiness_never_supplies_operator_gates(self):
        data = response_fixture()
        data.update(
            isolated_backend_verified=True,
            spending_limit_verified=True,
            tests_passed=True,
        )
        self.assertEqual(self.review(data)["status"], "BLOCKED")
        proposal = json.loads(data["choices"][0]["message"]["content"])
        proposal["spending_limit_verified"] = True
        data["choices"][0]["message"]["content"] = json.dumps(proposal)
        self.assertEqual(self.review(data)["reasons"], ["UNEXPECTED_OR_MISSING_FIELDS"])

    def test_fixture_usage_is_separate_and_missing_invalid_counts_are_unknown(self):
        data = response_fixture()
        data["usage"] = {
            "prompt_tokens": 10,
            "completion_tokens": 20,
            "total_tokens": 30,
            "private_extension": "not echoed",
        }
        receipt = self.review(data)
        self.assertEqual(
            receipt["fixture_reported_usage"],
            {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
        )
        self.assertEqual(receipt["actual_provider_usage"], "unknown")
        for usage in (
            {},
            {"prompt_tokens": False},
            {"prompt_tokens": 1, "completion_tokens": -1, "total_tokens": 0},
            {"prompt_tokens": 1, "completion_tokens": 2, "total_tokens": 9},
        ):
            data["usage"] = usage
            self.assertEqual(self.review(data)["fixture_reported_usage"], "unknown")

    def test_changed_saved_request_cannot_override_pins_or_endpoint(self):
        body = json.loads(self.draft.body)
        body["max_completion_tokens"] = 999999
        draft = RequestDraft(MODEL_CANDIDATE, encoded(body))
        self.assertEqual(
            review_offline_response(encoded(response_fixture()), draft)["reasons"],
            ["REQUEST_BINDING_MISMATCH"],
        )
        body["endpoint"] = "https://untrusted.example"
        draft = RequestDraft(MODEL_CANDIDATE, encoded(body))
        self.assertEqual(
            review_offline_response(encoded(response_fixture()), draft)["reasons"],
            ["REQUEST_BINDING_MISMATCH"],
        )

    def test_changed_source_after_request_blocks_response(self):
        temporary = tempfile.TemporaryDirectory(prefix="nebius-provider-negative-")
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        for name in PINNED_FILES:
            target = root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(SOURCE_ROOT / name, target)
        draft = prepare_request(source_root=root)
        (root / "coding/patch_review.py").write_bytes(
            b"raise RuntimeError('MUST_NOT_RUN')"
        )
        result = review_offline_response(encoded(response_fixture()), draft, root)
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(result["reasons"], ["SOURCE_FILE_DIGEST_MISMATCH"])

    def test_arbitrary_source_and_environment_credentials_never_run_or_leak(self):
        with patch.dict(
            "os.environ", {"NEBIUS_API_KEY": "synthetic-secret-DO-NOT-READ"}
        ):
            draft = prepare_request()
            self.assertNotIn(b"synthetic-secret", draft.body)
            data = response_fixture()
            proposal = json.loads(data["choices"][0]["message"]["content"])
            proposal["replacements"][0]["after_utf8"] = (
                "raise RuntimeError('MUST_NOT_RUN')\n"
            )
            data["choices"][0]["message"]["content"] = json.dumps(proposal)
            result = review_offline_response(encoded(data), draft)
            self.assertEqual(result["execution"], "NOT_RUN")
            self.assertEqual(result["network_requests"], 0)

    def test_model_syntax_is_not_availability_and_no_arbitrary_url(self):
        for value in (
            "https://other.example",
            "nvidia/abc?key=secret",
            "other/model",
            "nvidia/../secret",
            "nvidia/abc\n",
        ):
            with self.assertRaisesRegex(ValueError, "MODEL_ID"):
                prepare_request(value)
        preview = prepare_request("nvidia/SYNTHETIC-NONEXISTENT-ID")
        self.assertEqual(preview.receipt()["model_id_and_schema_support"], "UNVERIFIED")


if __name__ == "__main__":
    unittest.main()
