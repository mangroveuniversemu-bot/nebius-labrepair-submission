# Nebius LabRepair

**Two patches. Same total. One is wrong.**

LabRepair checks whether a repaired analysis agrees with the evidence behind its
headline number. Quantum research software is the first demonstration: a plausible
patch can reproduce the score while every registered correlation is wrong.
Inspect the repair before carrying that result into a research decision.
The example uses synthetic Bell–CHSH inputs.

## Try the judge review

This is the clean, MIT-licensed public submission snapshot. Previous Git/PR
history and old private Release bundles are not included. The separately retained
development repository stays private.

**[Open the interactive Demo](https://mangroveuniversemu-bot.github.io/nebius-labrepair-submission/)**

No login, API key, installation or model charge is needed. Click **Check the
wrong-pair repair**, compare the declared repair, then try missing evidence.
Download a source-bound review. These three cases run entirely in your browser.

The public HTTPS build was verified on 30 October: all six assets matched the
reviewed hashes, all three cases behaved correctly, the first button revealed
its result, and an actual review download succeeded. The saved cloud record is
a separate historical execution, not a new model call by this page.

## Windows quickstart — Python 3.12

From the repository root, run the Windows product verification entry point:

```powershell
python scripts/verify_poc.py
```

It uses the Python standard library and checks the local product, recorded-result
replay, mocked transport and daily budget controls. It makes no provider or
Sandbox request and does not execute candidate Python. The recorded Windows
increment passed 61 checks; a fresh invocation reports its own results.

To open the original local workbench:

```powershell
python -m labrepair.serve --port 8770
```

Open **http://127.0.0.1:8770/**. The public Pages demo above needs neither Python
nor Node.js. Optional Node.js checks are listed separately under verification.
The **full legacy security suite requires the reviewed Linux environment** and
its descriptor/filesystem guarantees. No macOS verification is claimed.

## Portable browser build

The [portable browser review](judge-site/README.md) is the shortest path: open
its built `index.html`, select the wrong-pair repair, and check the evidence.
It needs no API key and performs fixed-case arithmetic in your browser. The
separate saved Nebius records remain historical executions.

The Python workbench uses the same key-free local syntax/arithmetic review.
Try the valid repair, same-total control and incomplete-evidence case.

## Live mode with your own key

The repository includes an opt-in, direct **Nebius Token Factory inference API**
client. It uses the same fixed synthetic request and NVIDIA Nemotron model as
the archived 26 October call. Start with a key-free preview:

```sh
python scripts/run_live_repair.py
```

After setting `NEBIUS_API_KEY` in your process environment and verifying your own
account's current credits, model access and billing controls, opt into **one** call:

```sh
python scripts/run_live_repair.py --live --confirm-provider-billing --run-id reviewer-1
```

Do not put a key in a command argument, source file, screenshot or issue. The CLI
does not load `.env` automatically. It fixes the endpoint/model/request, requests
at most 64 completion tokens, uses a 30-second network timeout and never retries or follows
redirects. The billing confirmation acknowledges your provider account settings;
**a token limit is not a monetary cap or proof that credits cover a call**.

The response enters the same `review_chat_response` validation used by
`scripts/review_model_response.py`. It accepts only bounded parameters and checks
them against protected synthetic evidence. No candidate Python or Sandbox job is
executed. Request, response, local review and sanitized transport/usage receipts
are saved under ignored `.live-runs/<run-id>/`; existing run IDs are not overwritten.
Provider failures produce an explicit failure receipt; billed currency remains
`unknown` unless separately observed. Output from a new call is never relabeled as
the archived run or inserted into its pinned evidence.

The transport passed mocked HTTP tests and a **real direct CLI call on 30 October**:
HTTP 200, 121 input / 38 completion tokens, 0.9245 seconds, deterministic repair
verified. The shared ledger retained one US$0.01 reservation. Actual billed money
is unknown. [New exact receipts](evidence/nebius-direct-cli-20261030-1/transport-receipt.json)
are separate from the historical model/Sandbox runs below. The legacy invoice
request-preview module remains preview-only.
See [implementation and verification scope](docs/LIVE_MODE_20261030.md).

Live requests share a persistent **five-attempt / US$0.05 reserved daily envelope**
in Taipei time; every attempt reserves US$0.01, including failures and timeouts.
The sixth attempt is blocked. Use `--budget-status` to inspect the ledger and
`--disable-live` to stop live work. All production workers must use the same
`LABREPAIR_BUDGET_STATE` path. This application envelope is not a Nebius account
hard cap; [provider overage and operation details](docs/DAILY_LIMITS_AND_OVERAGE_20261030.md)
explain the remaining billing boundary.

## Recorded real results

**NVIDIA Nemotron 3 Nano on Nebius Token Factory** proposed bounded parameters;
one real disposable **Nebius Sandbox** operation ran the three variants:

| Case | Computed S | Checks passed | Observed outcome |
| --- | ---: | ---: | --- |
| Before repair | 0.10 | 2/4 | Expected failure |
| NVIDIA-proposed repair | 2.60 | 4/4 | Repair passed |
| Deliberately wrong operator control | 2.60 | 3/4 | Expected rejection |

The prompt supplied the declared channel convention; this tests its translation
into parameters, not autonomous scientific discovery. The original **3.40 claim
remains NOT_REPRODUCED**. A physical quantum result is not established.

## A useful two-minute inspection

1. Compare the valid repair with the same-total control: both give 2.60, but only
   the valid repair matches all four registered correlations.
2. Try incomplete evidence. That curated local case requests review rather than
   guessing; it was not part of the recorded three-case cloud execution.
3. Inspect the source diff, protected counts/tests and saved real-run record.
   Record a review intent or download its source-bound evidence.

The browser separates **curated local review** from **recorded real execution**.
Replaying either does not create a new provider job. Review intent authorizes
neither execution nor payment and does not change the scientific claim.

## Evidence and verification

The recorded request used `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B`: HTTP 200,
121 input / 38 completion tokens. The separate Sandbox operation took 1.273
seconds. Protected data and tests stayed unchanged; guest networking was
disabled. Its twelve checks include three intended control failures, not twelve
passing checks. These are fixed synthetic cases, not an accuracy benchmark.

- [Judge review guide](docs/POC_REVIEW_GUIDE.md)
- [Actual model response and limits](docs/REAL_GENERATION_20261026.md)
- [Actual Sandbox results and receipt boundaries](docs/REAL_SANDBOX_VALIDATION_20261027.md)
- [Selected 123-second public film and media provenance](media/demo-public-20261030/README.md)
- [Archived predecessor narration refinements](media/demo-20261030-live-review/NARRATION_REFINEMENT.md)
- [Historical private rc.1 film and portable-build notes](docs/DEMO_RELEASE_20261030.md)
- [Previous cinematic review cut](docs/DEMO_MEDIA_20261030.md)
- [Previous 142-second UI demo](docs/DEMO_MEDIA_20261029.md)
- [Design research and reference decisions](docs/DESIGN_REVIEW_20261029.md)
- [Previous 160-second current-UI demo and natural narration](docs/DEMO_MEDIA_20261028.md)
- [Historical 155-second demo delivery](docs/DEMO_MEDIA_20261027.md)

The Windows product verification command is the quickstart near the top of this
README. **Optional Node.js checks** cover the portable browser engine and
result-visibility contract separately:

```sh
node judge-site/tests/engine.test.mjs
node judge-site/tests/visibility.test.mjs
```

The published 27-test result belongs to earlier commit `c33fefb`; it is historical,
not proof that a later HEAD passed. Full legacy security verification requires
the reviewed Linux environment. [Archived commands and design notes](docs/ARCHIVED_VALIDATION.md)
are separate from this quickstart.

The local Python verifier contains **six curated offline fixtures**. They are a
different set from the **three interactive browser cases**, and from the **three
historically executed Sandbox variants**. Their counts and outcomes must not be
combined into an accuracy score. The browser's same-total sample has 0/4 pair
matches and is rejected; the historical cloud negative control passed 3/4 protected checks
and correctly failed overall.

The Live-mode increment on 30 October ran [61 product, mocked-transport and persistent-budget checks](evidence/poc_daily_budget_20261030.json),
the portable build's [18 offline checks](judge-site/test-result.json), and three
[asynchronous decision regressions](tests/ui_decision_race.cjs), all passing.
These separate suites do not re-run a cloud provider. See the
[recorded browser acceptance](evidence/judge_browser_acceptance_20261029.json),
[design decisions](docs/DESIGN_REVIEW_20261029.md), and [remaining delivery gates](docs/JUDGE_ACCEPTANCE_20261028.md).
Check this increment's source/evidence bindings with
`python scripts/check_judge_release.py`; the [manifest](evidence/judge_release_20261028.json)
records local access, historical provider evidence and the separate pending release gates.

## Access and release status

This repository has a new history containing only the reviewed application
snapshot. The original private development repository, its PR history and old
Release assets are not published here. Earlier dated private-release documents
are historical records, not the current access status.

The public Demo is live on GitHub Pages. The original development repo stays
private. The selected public film is 123 seconds with the actual public URLs on
its end card. Its [canonical media index](media/demo-public-20261030/README.md)
identifies the current artifact; `media/demo-20261030-live-review/render_live_review.py`
is an archived predecessor renderer.

The current Devpost account is **REGISTER_NOT_JOINED**: the event registration
form was opened but not submitted. Public YouTube upload is **NOT_UPLOADED**, and
Devpost entry is **NOT_SUBMITTED**. An open upload/registration dialog is not a
completed action. Owner survey responses and action-time rules/terms confirmation
remain pending.
See [submission preparation](docs/SUBMISSION_DRAFT_20261026.md).

Automatic provider dispatch stays disabled. Existing saved runs do not establish
fresh spending authorization; actual billed currency remains unknown.

## Sources and license

MIT. The unchanged `vendor/evidencepilot/` snapshot retains the license and
attribution from [EvidencePilot submission](https://github.com/mangroveuniversemu-bot/evidencepilot-submission),
commit `c9595a6e0d7cb15d28755624eb9baa7695038ef5`. The pinned Q4 Coding fixture is
also preserved. This repository starts a clean Git history and contains no
private research or real hardware measurements. See the archived notes for the
earlier offline verification core and third-party source boundaries.
