"""Exercise candidate intake with labeled in-memory synthetic contracts only."""

import json
import unittest

from labrepair.candidate_review import (
    MAX_PROPOSAL_BYTES,
    FrozenContract,
    OperatorGates,
    canonical_digest,
    digest,
    review_candidate,
)

ORIGINALS = (
    ("solution.py", b"def add(a, b):\n    return a - b\n"),
    ("tests/test_solution.py", b"# Synthetic protected acceptance tests\n"),
    ("policy.json", b'{"network": "deny"}\n'),
)
CONTRACT = FrozenContract(
    ORIGINALS, ("solution.py",), canonical_digest({"network": "deny"})
)
READY = OperatorGates(True, True, True)


def proposal(**updates):
    result = {
        "snapshot_sha256": CONTRACT.snapshot_sha256,
        "policy_sha256": CONTRACT.policy_sha256,
        "replacements": [
            {
                "path": "solution.py",
                "before_sha256": digest(ORIGINALS[0][1]),
                "after_utf8": "def add(a, b):\n    return a + b\n",
            }
        ],
    }
    result.update(updates)
    return result


def inspect(value, gates=READY, contract=CONTRACT):
    return review_candidate(json.dumps(value).encode(), contract, gates)


class CandidateReviewTests(unittest.TestCase):
    def test_duplicate_keys_and_nonobject_json_rejected(self):
        self.assertEqual(
            review_candidate(b'{"replacements":[],"replacements":[]}', CONTRACT, READY)[
                "reasons"
            ],
            ["INVALID_JSON"],
        )
        # A valid array must still fail the object schema. The inherited Python
        # recursion setting can instead reject this nesting during JSON parsing.
        result = review_candidate(b"[" * 2000 + b"]" * 2000, CONTRACT, READY)
        self.assertEqual(result["status"], "REJECTED")
        self.assertIn(
            result["reasons"], (["INVALID_JSON"], ["UNEXPECTED_OR_MISSING_FIELDS"])
        )

    def test_good_proposal_is_only_ready_not_accepted(self):
        result = inspect(proposal())
        self.assertEqual(result["status"], "READY_FOR_ISOLATED_TEST")
        self.assertEqual(result["execution"], "NOT_RUN")
        self.assertEqual(result["usage"], "unknown")
        self.assertFalse(result["source_written"])
        self.assertIn("+    return a + b", result["changes"][0]["diff"])

    def test_source_unavailable_cannot_be_bypassed(self):
        result = inspect(proposal(), READY, None)
        self.assertEqual(result["reasons"], ["VERIFIED_SOURCE_UNAVAILABLE"])
        self.assertEqual(result["status"], "BLOCKED")

    def test_external_gates_must_be_operator_verified(self):
        result = inspect(proposal(), OperatorGates(True, False, False))
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(
            result["reasons"],
            ["ISOLATED_BACKEND_UNVERIFIED", "SPENDING_LIMIT_UNVERIFIED"],
        )

    def test_proposal_cannot_claim_test_success_or_live_permission(self):
        for key in ("tests_passed", "live", "source_verified", "usage"):
            with self.subTest(key=key):
                self.assertEqual(
                    inspect(proposal(**{key: True}))["reasons"],
                    ["UNEXPECTED_OR_MISSING_FIELDS"],
                )

    def test_wrong_source_and_policy_rejected(self):
        for field, reason in (
            ("snapshot_sha256", "STALE_OR_WRONG_SOURCE"),
            ("policy_sha256", "POLICY_BINDING_MISMATCH"),
        ):
            with self.subTest(field=field):
                self.assertEqual(
                    inspect(proposal(**{field: "0" * 64}))["reasons"], [reason]
                )

    def test_protected_tests_and_policy_cannot_change(self):
        for path, before in ORIGINALS[1:]:
            value = proposal()
            value["replacements"][0].update(path=path, before_sha256=digest(before))
            self.assertEqual(inspect(value)["reasons"], ["PROTECTED_FILE_CHANGE"])

    def test_unsafe_or_unknown_paths_rejected(self):
        for path in (
            "../solution.py",
            "C:/solution.py",
            "solution.py:stream",
            "tests\\test.py",
            "/tmp.py",
            "a//b.py",
            "./solution.py",
            "solution.py\x00",
            "solution.py.",
            "solution.py ",
        ):
            with self.subTest(path=path):
                value = proposal()
                value["replacements"][0]["path"] = path
                self.assertEqual(inspect(value)["reasons"], ["UNSAFE_PATH"])
        value = proposal()
        value["replacements"][0]["path"] = "unlisted.py"
        self.assertEqual(inspect(value)["reasons"], ["OUTSIDE_FROZEN_WORKSPACE"])

    def test_stale_file_binding_and_duplicate_rejected(self):
        value = proposal()
        value["replacements"][0]["before_sha256"] = "0" * 64
        self.assertEqual(inspect(value)["reasons"], ["ORIGINAL_FILE_BINDING_MISMATCH"])
        value = proposal()
        value["replacements"].append(value["replacements"][0].copy())
        result = inspect(value)
        self.assertEqual(result["reasons"], ["DUPLICATE_PATH"])
        self.assertEqual(result["changes"], [])

    def test_malformed_oversized_and_noop_rejected(self):
        self.assertEqual(
            review_candidate(b"not-json", CONTRACT, READY)["reasons"], ["INVALID_JSON"]
        )
        self.assertEqual(
            review_candidate(b"x" * (MAX_PROPOSAL_BYTES + 1), CONTRACT, READY)[
                "reasons"
            ],
            ["PROPOSAL_TOO_LARGE"],
        )
        value = proposal()
        value["replacements"][0]["after_utf8"] = ORIGINALS[0][1].decode()
        self.assertEqual(inspect(value)["reasons"], ["NO_SOURCE_CHANGE"])

    def test_model_source_is_never_executed(self):
        value = proposal()
        value["replacements"][0]["after_utf8"] = (
            "raise RuntimeError('MUST NEVER EXECUTE')\n"
        )
        result = inspect(value)
        self.assertEqual(result["status"], "READY_FOR_ISOLATED_TEST")
        self.assertEqual(result["execution"], "NOT_RUN")
        self.assertEqual(result["network_requests"], 0)
        self.assertEqual(CONTRACT.originals, ORIGINALS)

    def test_source_encoding_and_size_are_bounded(self):
        for text, reason in (
            ("\ud800", "INVALID_SOURCE_ENCODING"),
            ("x" * 8193, "REPLACEMENT_TOO_LARGE"),
            ("a\x00b", "INVALID_SOURCE_TEXT"),
        ):
            with self.subTest(reason=reason):
                value = proposal()
                value["replacements"][0]["after_utf8"] = text
                self.assertEqual(inspect(value)["reasons"], [reason])

    def test_contract_rejects_case_aliases_and_extra_files(self):
        for originals in (
            ORIGINALS + (("extra.py", b""),),
            (("Solution.py", b""), ("solution.py", b""), ORIGINALS[2]),
        ):
            with self.assertRaises(ValueError):
                FrozenContract(originals, (), CONTRACT.policy_sha256)


if __name__ == "__main__":
    unittest.main()
