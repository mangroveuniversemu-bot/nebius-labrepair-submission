"""Offline intake controls use explicitly fabricated provider-shaped test data."""
import json
import unittest
from unittest.mock import patch

from labrepair.model_parameters import review_chat_response, review_parameter_text
from labrepair.scientific_workflow import ScienceReviewError


class ModelParameterTests(unittest.TestCase):
    def test_typed_parameters_are_independently_checked_without_execution(self):
        with patch("os.system", side_effect=AssertionError("must not execute")):
            result = review_parameter_text(b'{"channel_signs":[1,1,-1,-1],"offsets":[0,0,0,0]}')
        self.assertEqual(result["local_review"]["local_result"], "LOCAL_SEMANTIC_MATCH")
        self.assertTrue(result["local_review"]["per_pair_match"])
        self.assertEqual(result["local_review"]["original_claim"]["claim_state"], "NOT_REPRODUCED")
        self.assertEqual(result["candidate_execution"], "NOT_RUN")
        self.assertEqual(result["reviewer_network_requests"], 0)
        self.assertEqual(result["provider_generation"], "NOT_ATTESTED_BY_OFFLINE_REPLAY")

    def test_unexpected_fields_duplicate_keys_bool_and_code_are_refused(self):
        bad = [
            b'{"channel_signs":[1,1,-1,-1],"offsets":[0,0,0,0],"approved":true}',
            b'{"channel_signs":[1,1,-1,-1],"offsets":[0,0,0,0],"offsets":[0,0,0,0]}',
            b'{"channel_signs":[true,1,-1,-1],"offsets":[0,0,0,0]}',
            b'{"channel_signs":[1,1,-1,-1],"offsets":[NaN,0,0,0]}',
            b'{"channel_signs":[1,1,-1,-1],"offsets":["__import__(os)",0,0,0]}',
            b'```json\n{"channel_signs":[1,1,-1,-1],"offsets":[0,0,0,0]}\n```',
        ]
        for raw in bad:
            with self.subTest(raw=raw), self.assertRaises(ScienceReviewError):
                review_parameter_text(raw)

    def test_valid_but_incorrect_parameters_are_not_accepted(self):
        result = review_parameter_text(b'{"channel_signs":[-1,1,-1,-1],"offsets":[0,0,0,0]}')
        self.assertEqual(result["local_review"]["local_result"], "REJECTED")
        self.assertFalse(result["local_review"]["per_pair_match"])

    def test_truncated_or_tool_call_responses_never_become_a_proposal(self):
        fake = {"choices": [{"finish_reason": "stop", "message": {"role": "assistant", "content": '{"channel_signs":[1,1,-1,-1],"offsets":[0,0,0,0]}'}}]}
        result = review_chat_response(json.dumps(fake).encode())
        self.assertEqual(result["local_review"]["local_result"], "LOCAL_SEMANTIC_MATCH")
        for change in ("truncated", "tool"):
            sample = json.loads(json.dumps(fake))
            if change == "truncated":
                sample["choices"][0]["finish_reason"] = "length"
            else:
                sample["choices"][0]["message"]["tool_calls"] = [{"name": "run"}]
            with self.assertRaises(ScienceReviewError):
                review_chat_response(json.dumps(sample).encode())


if __name__ == "__main__":
    unittest.main()
