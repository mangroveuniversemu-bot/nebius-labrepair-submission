# Archived validation and design notes

This preserves the earlier README's offline-core and historical recording
checks. It is not the judge quickstart and it does not describe the latest
recorded provider integration or narrated demo. Use [the current review
guide](POC_REVIEW_GUIDE.md) and [README](../README.md) first.

In particular, `python scripts/verify_demo.py` checks an older recording
checkpoint and intentionally returns exit 2 when that checkpoint is absent.
That historical result must not be presented as the current product test result.
The old `recording/submission NOT_RUN` statement below belongs to that archived
recording checkpoint. The later private narrated video exists; public video
publication and competition submission are still pending.

## Earlier offline contract and verification core

Nebius LabRepair is an offline prototype for reviewing small, model-proposed
code repairs against fixed source, tests, and policy. It shows the review path
from a bounded candidate diff to replayable evidence and a human decision.

The offline prototype itself makes no model or provider call. It does not run a
candidate patch and is not an isolated execution environment. The observations
above are separate integration evidence. The local
fixtures use synthetic invoice and analysis examples; they are not customer,
private research, or hardware measurements.

## Run locally

Requirements: Python 3.12 and the pinned dependency in `requirements.txt`.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python -m labrepair.preflight
python -m labrepair.replay
python scripts/verify_offline_exchange.py
```

The offline verifier uses synthetic fixtures and fake responses. It does not
contact Nebius, NVIDIA, AWS, GitHub, or any model endpoint. A passing local
test does not verify cloud access, monetary limits, sandbox isolation, or
hackathon eligibility.

The disabled-live preflight also evaluates structured provider/cost evidence
claims. Missing pricing, credit coverage, a provider-enforced zero-cash cap,
disabled automatic charging, credential permission, or runtime access blocks
admission. A credit balance is never a cash cap. Even complete synthetic or
operator-supplied claims cannot enable dispatch. See
[`docs/PROVIDER_ADMISSION.md`](PROVIDER_ADMISSION.md) for the offline contract.

For a readable, read-only admission report, run:

```sh
python -m labrepair.admission_view --review-name review-001
```

Open `admission-workbench/review-001/index.html`. Each review needs a new name;
existing reviews are preserved. The report separates claim consistency from
runtime admission, explains blockers, and records evidence/request/source hashes.
It never treats a saved verdict as an input or authorizes dispatch. Exit 0 means
only that the report was written. See
[`docs/ADMISSION_REVIEWER.md`](ADMISSION_REVIEWER.md) for evidence inputs,
provenance and the saved missing-evidence example.

To check the archived recording draft's available evidence without changing it,
run `python scripts/verify_demo.py`. The current clean checkout returns exit 2
with a JSON report: five of six historical source pins match, but the original
checkpoint is missing. Draft timing and captions can be checked separately;
recording and submission remain NOT_RUN. See
[`docs/DEMO_EVIDENCE_GAPS.md`](DEMO_EVIDENCE_GAPS.md) for the exact boundary.

To view the saved read-only handover, open `handover-workbench/index.html`.
Serve only that directory if using a local web server; never serve the project
root or a user workspace. Candidate text is displayed as data. The page has no
dispatch or patch-apply controls.

## Design boundary

- The model may propose a bounded diff; the proposal is untrusted input.
- Deterministic checks bind the proposal to a fixed source and policy.
- Protected files and test changes are rejected.
- Missing source, isolation, or cost evidence keeps the candidate blocked.
- No code is staged by the local review UI. The separately authorized recorded
  Sandbox run executed only the pinned synthetic variants.

## Source and license notes

The vendored `vendor/evidencepilot/` snapshot is preserved byte-for-byte from
[`mangroveuniversemu-bot/evidencepilot-submission`](https://github.com/mangroveuniversemu-bot/evidencepilot-submission),
commit `c9595a6e0d7cb15d28755624eb9baa7695038ef5`, with its MIT license and
notices. Its example data is synthetic. A small pinned Coding fixture is
included under `vendor/q4-coding/`; the loader verifies the three source files
and two matching tests by content hash. It reads literal constants without
importing or executing the fixtures. Review third-party licensing before any
public release.

This repository starts with a new Git history. It does not import commits from
the EvidencePilot development or submission repositories.

## V3 bounded test preparation

The active offline gate enforces one request, entire input at most 512 tokens,
completion including reasoning at most 256 tokens, zero SDK retries, a 30-second
timeout and credit cost at most USD 0.01 with zero new cash. Configuration cannot
authorize dispatch. Its archived admission examples remain synthetic. The separate
one-shot generation above supplies current transport and full-input token evidence;
it does not enable this offline gate or verify Sandbox spending controls.
Historical handovers retain their archived request format for replay only.
See [V3 bounded gate](V3_BOUNDED_GATE.md) for implementation and limitations.
