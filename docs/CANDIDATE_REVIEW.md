# Candidate intake and dispatch gate — NEBIUS-004

This independent addition previews a bounded candidate diff, binds it to an
operator-owned three-file snapshot and policy digest, rejects protected-file
changes, and requires verified execution and spending gates before dispatch.
It does not apply patches, run submitted source or accept a scientific claim.

The original Q4 adapter remains unavailable. Its historical manifest digest is
not a substitute for verified current source bytes. The shipped CLI therefore
has no trusted source loader and returns `BLOCKED: VERIFIED_SOURCE_UNAVAILABLE`.
There is deliberately no flag to bypass this check. The in-memory synthetic
contract in tests demonstrates the review behavior; it is not the old Q4 source.

## States

- `REJECTED`: malformed, stale, wrong-policy, protected or out-of-scope proposal.
- `BLOCKED`: missing verified source, isolated execution backend or cost ceiling.
- `READY_FOR_ISOLATED_TEST`: intake checks pass; tests and execution remain NOT_RUN.

The candidate cannot provide its own test outcome, credits, usage or permission
flags. A ready status is not a security assessment of the proposed source. It
only permits subsequent testing in an actually verified isolated backend.
Diffs are untrusted text and must be escaped if displayed in a future web UI.

## Local use

    .venv/Scripts/python.exe -m labrepair.candidate_review --proposal evidence/review_candidate_fixture.json --output evidence/review_cli_receipt.json

An exit code of 2 is an expected refusal, not a passing repair. The receipt
records proposal digest, reasons, elapsed review time and unknown provider usage.
No source is written; no network, model, subprocess or source import is invoked.

## Exact next integration step

Download and verify the latest shared Q4 ZIP and its manifest. Read its AGENTS,
workspace contract, policy and tests before implementing a trusted source loader.
Determine its actual three pre-staged files and writable paths; do not invent
them from the historical summary. Retain protected tests and policy. Only then
connect this review output to the existing adapter and actual Nebius runtime.
