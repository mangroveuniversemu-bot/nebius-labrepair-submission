"""Scientific repair review using trusted arithmetic, never candidate execution.

This is a new, independently labeled synthetic program, not a reconstruction of
the missing Maya notebook. Proposed code is parsed as data. Only two literal
tuples may differ from the pinned source; trusted tools interpret their values.
Neither the Python function nor arbitrary model text is imported or executed.
"""

import ast
import copy
import json
import math
from fractions import Fraction
from pathlib import Path

from labrepair.candidate_review import (
    FrozenContract,
    OperatorGates,
    canonical_digest,
    digest,
    review_candidate,
    unique_object,
)
from labrepair.paths import ROOT

FIXTURE_ROOT = ROOT / "fixtures" / "scientific"
SCENARIOS = {
    "channel-fix": "Repair the declared channel mapping",
    "same-total": "Same total, wrong pair evidence",
    "protected-test": "Attempt to rewrite a protected test",
    "stale-source": "Patch bound to an older source",
    "injected-code": "Executable instruction hidden in a proposal",
    "missing-pair": "Incomplete pair evidence",
}
POLICY = {
    "editable": ["analysis.py"],
    "protected": ["counts.json", "test_analysis.py"],
    "candidate_execution": "FORBIDDEN_ON_HOST",
    "local_check": "PINNED_AST_SHAPE_AND_TRUSTED_ARITHMETIC_ONLY",
    "claim_promotion": "NEVER_FROM_CODE_REPAIR",
}
# Filled from the three reviewed source files, independently of any proposal.
SOURCE_PINS = {
    "analysis.py": "d53efa1e35238352505388a975685412509b784e0528878ef524ed8e82071879",
    "counts.json": "ebe15738fd6443328681cc53f549d7d7d299b4c1958e2db7082d0de032c12eca",
    "test_analysis.py": "d83e65c56f5244e61a49c2d300fe8df2e29f63f6aa7cba97fc1c2daca4b7e3e4",
}


class ScienceReviewError(ValueError):
    """A fixed error code; never echo private or untrusted text."""


def encode(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def load_fixture(root: Path = FIXTURE_ROOT):
    files = {}
    for name, expected in SOURCE_PINS.items():
        path = root / name
        if any(part.is_symlink() for part in (path, *path.parents)):
            raise ScienceReviewError("FIXTURE_SYMLINK_FORBIDDEN")
        try:
            with path.open("rb") as stream:
                raw = stream.read(16385)
        except OSError as exc:
            raise ScienceReviewError("FIXTURE_UNAVAILABLE") from exc
        # Git checkouts may use CRLF. The pins define explicit UTF-8 LF source.
        if len(raw) > 16384:
            raise ScienceReviewError("FIXTURE_SOURCE_TOO_LARGE")
        raw = raw.replace(b"\r\n", b"\n")
        if digest(raw) != expected:
            raise ScienceReviewError("FIXTURE_SOURCE_CHANGED")
        files[name] = raw
    if set(files) != {"analysis.py", "counts.json", "test_analysis.py"}:
        raise ScienceReviewError("FIXTURE_PINS_UNAVAILABLE")
    data = json.loads(files["counts.json"], object_pairs_hook=unique_object)
    return files, data, FrozenContract(
        tuple(sorted(files.items())), ("analysis.py",), canonical_digest(POLICY)
    )


def _parameters(source: str, original: str):
    """Validate the whole AST; literal extraction is not Python execution."""
    try:
        tree = ast.parse(source)
        template = ast.parse(original)
        if len(tree.body) != 3:
            raise ValueError
        values = []
        for index, name in enumerate(("CHANNEL_SIGNS", "OFFSETS")):
            node = tree.body[index]
            if not (
                isinstance(node, ast.Assign)
                and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name)
                and node.targets[0].id == name
                and isinstance(node.value, ast.Tuple)
            ):
                raise ValueError
            value = ast.literal_eval(node.value)
            if len(value) != 4 or any(
                type(item) not in (int, float)
                or not math.isfinite(item)
                or abs(item) > 1
                for item in value
            ):
                raise ValueError
            if index == 0 and any(item not in (-1, 1) for item in value):
                raise ValueError
            values.append(value)
            node.value = template.body[index].value
        if ast.dump(tree) != ast.dump(template):
            raise ValueError
        return values
    except (ValueError, TypeError, SyntaxError, RecursionError, OverflowError) as exc:
        raise ScienceReviewError("CANDIDATE_AST_SHAPE_NOT_PERMITTED") from exc


def compute_pairs(rows, signs, offsets):
    """Trusted exact-rational tool, independent of the proposed function body."""
    if len(rows) != 4:
        raise ScienceReviewError("MISSING_PAIR_EVIDENCE")
    result = []
    for row, sign, offset in zip(rows, signs, offsets):
        if len(row) != 4 or any(type(x) is not int or x < 0 for x in row) or not sum(row):
            raise ScienceReviewError("INVALID_SYNTHETIC_COUNTS")
        result.append(
            Fraction(sign * (row[0] - row[1] - row[2] + row[3]), sum(row))
            + Fraction(str(offset))
        )
    return result


def _s_value(pairs, terms):
    return sum(value * term for value, term in zip(pairs, terms))


def make_proposal(scenario, files, contract):
    if scenario not in SCENARIOS:
        raise ScienceReviewError("UNKNOWN_SCENARIO")
    original = files["analysis.py"].decode()
    fixed = original.replace("(1, 1, 1, 1)", "(1, 1, -1, -1)", 1)
    after = fixed
    path = "analysis.py"
    if scenario == "same-total":
        after = fixed.replace("(0, 0, 0, 0)", "(0.1, 0.1, -0.1, 0.1)", 1)
    elif scenario == "protected-test":
        path = "test_analysis.py"
        after = "def check_correlations(actual):\n    return True\n"
    elif scenario == "injected-code":
        after += '\n__import__("os").system("echo UNTRUSTED")\n'
    proposal = {
        "snapshot_sha256": "0" * 64 if scenario == "stale-source" else contract.snapshot_sha256,
        "policy_sha256": contract.policy_sha256,
        "replacements": [{"path": path, "before_sha256": digest(files[path]), "after_utf8": after}],
    }
    return proposal


def review_proposal(raw, *, scenario="channel-fix", root=FIXTURE_ROOT, proposal_origin="UNTRUSTED_OFFLINE_INPUT"):
    if scenario not in SCENARIOS:
        raise ScienceReviewError("UNKNOWN_SCENARIO")
    files, data, contract = load_fixture(root)
    original_claim = copy.deepcopy(data["original_claim"])
    claim_hash = canonical_digest(original_claim)
    intake = review_candidate(raw, contract, OperatorGates(source_verified=True))
    registered = compute_pairs(data["rows"], data["registered_channel_signs"], (0, 0, 0, 0))
    before = compute_pairs(data["rows"], (1, 1, 1, 1), (0, 0, 0, 0))
    report = {
        "schema": "LABREPAIR_SCIENTIFIC_REVIEW_V1",
        "scenario": scenario,
        "title": SCENARIOS[scenario],
        "data_origin": data["data_origin"],
        "mode": "ACTUAL_LOCAL_TRUSTED_ARITHMETIC; NOT_CANDIDATE_EXECUTION",
        "proposal_origin": proposal_origin,
        "snapshot_sha256": contract.snapshot_sha256,
        "policy_sha256": contract.policy_sha256,
        "proposal_sha256": digest(raw),
        "original_source_sha256": {name: digest(value) for name, value in files.items()},
        "original_claim": original_claim,
        "original_claim_sha256": claim_hash,
        "original_claim_after_sha256": claim_hash,
        "original_claim_unchanged": True,
        "claimed_s": float(original_claim["claimed_s"]),
        "baseline_s": float(_s_value(before, data["chsh_terms"])),
        "registered_s": float(_s_value(registered, data["chsh_terms"])),
        "pairs": data["pairs"],
        "registered_pairs": list(map(float, registered)),
        "baseline_pairs": list(map(float, before)),
        "candidate_pairs": None,
        "candidate_s": None,
        "total_only_match": False,
        "per_pair_match": False,
        "local_result": "REJECTED" if intake["status"] == "REJECTED" else "PENDING",
        "reasons": list(intake["reasons"] if intake["status"] == "REJECTED" else []),
        "changes": intake["changes"],
        "runtime_admission": "BLOCKED",
        "runtime_reasons": ["MONETARY_GUARD_UNVERIFIED", "ISOLATED_EXECUTION_NOT_RUN"],
        "candidate_execution": "NOT_RUN",
        "nebius_generation": "NOT_RUN",
        "actual_provider_usage": "unknown",
        "actual_provider_charge": "unknown",
        "source_written": False,
        "network_requests": 0,
        "claim_promotion": "FORBIDDEN_FROM_REPAIR_RESULT",
        "physical_interpretation": "NOT_ESTABLISHED_SYNTHETIC_DATA",
        "limitations": [
            "Local AST and arithmetic checks are not execution of the candidate.",
            (
                "The curated proposal is not generated by an NVIDIA or Nebius model."
                if proposal_origin == "CURATED_SYNTHETIC_FIXTURE_NOT_MODEL_OUTPUT"
                else "This local reviewer makes no model call; upstream generation evidence is separate."
            ),
            "This new synthetic analysis is not the missing original Maya notebook.",
            "One matching number is insufficient; every registered pair must match.",
            "Checksums establish content integrity, not authenticated identity.",
        ],
    }
    if intake["status"] != "REJECTED":
        try:
            proposal = json.loads(raw, object_pairs_hook=unique_object)
            source = proposal["replacements"][0]["after_utf8"]
            signs, offsets = _parameters(source, files["analysis.py"].decode())
            rows = data["rows"][:3] if scenario == "missing-pair" else data["rows"]
            actual = compute_pairs(rows, signs, offsets)
            total = _s_value(actual, data["chsh_terms"])
            report["candidate_pairs"] = list(map(float, actual))
            report["candidate_s"] = float(total)
            report["total_only_match"] = total == _s_value(registered, data["chsh_terms"])
            report["per_pair_match"] = actual == registered
            report["local_result"] = "LOCAL_SEMANTIC_MATCH" if actual == registered else "REJECTED"
            if actual != registered:
                report["reasons"].append("PER_PAIR_EVIDENCE_MISMATCH")
        except ScienceReviewError as exc:
            report["reasons"].append(str(exc))
            report["local_result"] = "REVIEW" if str(exc) == "MISSING_PAIR_EVIDENCE" else "REJECTED"
    # Check source again; fail if it changed while constructing the handover.
    _, after_data, after_contract = load_fixture(root)
    if after_contract.snapshot_sha256 != contract.snapshot_sha256:
        raise ScienceReviewError("SOURCE_CHANGED_DURING_REVIEW")
    if canonical_digest(after_data["original_claim"]) != claim_hash:
        raise ScienceReviewError("CLAIM_CHANGED_DURING_REVIEW")
    report["steps"] = [
        {"tool": "inspect_fixture", "result": "Three pinned files verified; synthetic source only."},
        {"tool": "review_patch", "result": intake["status"]},
        {"tool": "recompute_correlations", "result": report["local_result"]},
        {"tool": "compare_pairwise", "result": "MATCH" if report["per_pair_match"] else "NOT_MATCHED"},
        {"tool": "preserve_claim", "result": "NOT_REPRODUCED; original claim unchanged."},
        {"tool": "runtime_admission", "result": "BLOCKED; no paid compute dispatched."},
    ]
    report["receipt_sha256"] = canonical_digest(report)
    return report


def run_scenario(scenario):
    files, _, contract = load_fixture()
    return review_proposal(
        encode(make_proposal(scenario, files, contract)), scenario=scenario,
        proposal_origin="CURATED_SYNTHETIC_FIXTURE_NOT_MODEL_OUTPUT",
    )


def decision_record(review, choice):
    if choice not in ("hold-for-evidence", "request-isolated-rerun"):
        raise ScienceReviewError("INVALID_REVIEW_CHOICE")
    # Recompute independently; a browser-supplied verdict is not authoritative.
    fresh = run_scenario(review["scenario"])
    if review.get("receipt_sha256") != fresh["receipt_sha256"]:
        raise ScienceReviewError("STALE_REVIEW_RECEIPT")
    return {
        "schema": "LABREPAIR_REVIEW_INTENT_V1",
        "choice": choice,
        "review_receipt_sha256": fresh["receipt_sha256"],
        "original_claim_sha256": fresh["original_claim_sha256"],
        "review_intent_only": True,
        "executes_candidate": False,
        "authorizes_payment": False,
        "changes_scientific_claim": False,
    }


def verify_scenarios():
    receipts = [run_scenario(scenario) for scenario in SCENARIOS]
    expected = ["LOCAL_SEMANTIC_MATCH", "REJECTED", "REJECTED", "REJECTED", "REJECTED", "REVIEW"]
    return {
        "schema": "LABREPAIR_SCIENTIFIC_ACCEPTANCE_V1",
        "success": [r["local_result"] for r in receipts] == expected,
        "curated_scenarios": len(receipts),
        "naive_total_only_false_accepts": sum(r["total_only_match"] and not r["per_pair_match"] for r in receipts),
        "full_pair_checker_false_accepts_in_this_fixed_set": sum(
            r["local_result"] == "LOCAL_SEMANTIC_MATCH" and not r["per_pair_match"]
            for r in receipts
        ),
        "scope": "Six fixed synthetic cases; not a general robustness benchmark.",
        "receipts": receipts,
    }
