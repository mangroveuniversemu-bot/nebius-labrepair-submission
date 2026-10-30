# LabRepair — repair the analysis, preserve the evidence

Current submission draft, updated **30 October 2026**. The dated filename is
retained so existing links keep working. This is preparation, not a submitted
Devpost entry.

Track target: **Coding and Agentic Engineering**. Positioning:
**verification-first developer tool**, using a bounded, human-authorized,
single-pass workflow. No autonomous repair loop or scientific discovery is claimed.

## Public links and current gates

- [Public MIT-licensed submission repository](https://github.com/mangroveuniversemu-bot/nebius-labrepair-submission)
- [Public key-free interactive Demo](https://mangroveuniversemu-bot.github.io/nebius-labrepair-submission/)
- [Selected public film and canonical media index](../media/demo-public-20261030/README.md)
- Public YouTube URL: **NOT_UPLOADED**.
- Event registration: **REGISTER_NOT_JOINED**. The signed-in account's My projects
  screen requested event registration. Its form is open but not submitted.
  Owner survey responses and eligibility/rules/terms confirmation remain pending.
  Builder Program participation is not this event's registration.
- Devpost entry: **NOT_SUBMITTED**.

Public source/MIT and Pages access were verified on 30 October. All six
anonymously fetched HTTPS assets returned HTTP 200 with expected hashes. Actual
browser interaction verified all three cases, result visibility and a 3,615-byte
evidence download. The original development repository remains private; this
clean snapshot includes no old private Git/PR history or old private Release
attachments.

## Tagline

Two patches. Same total. One is wrong. Check the evidence behind the score.

## Inspiration

AI can patch a research program until its headline number looks right. A research
software engineer still needs to know whether the correction agrees with the
underlying evidence. A plausible patch can match the score while changing the
meaning of the result. LabRepair makes that disagreement inspectable before the
analysis is carried into a research decision.

The synthetic Bell–CHSH example makes the problem concrete: two repairs both
produce 2.60, but only one matches the four registered correlations. This is a
counterexample to total-only checking, not evidence that a deployed model
performed reward hacking or that the tool detects it generally.

## What it does

LabRepair binds a bounded repair to frozen source and policy, protects raw counts
and tests, recomputes each registered value and preserves the original claim.
The reviewer can inspect the candidate change, record a hold/review intent and
download source-bound evidence. Review intent launches no new job and authorizes
neither execution nor payment.

The public browser provides **exactly three fixed interactive cases**:

| Browser case | Computed S | Registered pair matches | Verdict |
| --- | ---: | ---: | --- |
| Declared channel repair | 2.60 | 4/4 | Repair passes |
| Same-total, wrong-pair control | 2.60 | 0/4 | Repair rejected |
| Missing pair | unknown | Incomplete | REVIEW |

For the missing-pair case, the table preserves the three available candidate
values (0.70, 0.65, 0.75) and marks only the fourth as UNKNOWN. The complete
candidate vector and total remain unknown; partial evidence cannot approve a
complete result.

The original **3.40 claim remains NOT_REPRODUCED in every case**. Browser
calculation is local, needs no key/account, sends no inference request and does
not execute candidate Python. The incomplete-evidence sample is a curated browser
case, not part of the recorded Sandbox experiment.

## How we built it

NVIDIA Nemotron 3 Nano on **Nebius Token Factory** proposed two bounded integer
arrays. The prompt supplied the declared channel convention. The model translated
that instruction into parameters; it did not discover an unknown convention.
An operator-owned adapter validates the arrays and constructs an allowlisted
source change. Arbitrary model-generated Python is not accepted by this intake.

The earlier real run then used one disposable **Nebius Sandbox** operation to
execute baseline, model repair and an operator-written negative control against
unchanged protected inputs/tests. It was accepted on 26 October UTC / 27 October
Taipei and took 1.273 seconds, with guest networking disabled:

| Historical Sandbox variant | S | Protected checks passed | Process exit |
| --- | ---: | ---: | ---: |
| Baseline | 0.10 | 2/4 | 1, expected failure |
| Model-proposed repair | 2.60 | 4/4 | 0 |
| Operator wrong-pair control | 2.60 | 3/4 | 1, expected failure |

These are three historical cloud variants, with twelve executed checks and three
intended control failures, **not twelve passing checks**. The cloud negative
control differs from the browser's 0/4 same-total sample. See the
[exact Sandbox observation and boundaries](REAL_SANDBOX_VALIDATION_20261027.md).

On **30 October**, the repository's own direct CLI performed one additional real
Token Factory inference: **HTTP 200, 121 input / 38 completion tokens, 0.9245
seconds**, followed by deterministic verification. It made one attempt with no
retry and **no new Sandbox dispatch**. The new request, response, transport and
review records are [separate exact receipts](../evidence/nebius-direct-cli-20261030-1/).
Offline replay of a saved result does not become a fresh provider call.

The direct CLI has a fixed model/request, at most 64 completion tokens, a
30-second network timeout, no redirects and no retries. A shared persistent
ledger permits at most **five attempts / US$0.05 reserved per Taipei day**,
retaining US$0.01 for each failure or uncertain attempt. The sixth attempt is
blocked before HTTP. This is an **application reservation envelope, not a
Nebius account-wide hard spending cap**. Actual billed currency is unknown.

## Verification and supported review path

For **Windows with Python 3.12**, run from the repository root:

```powershell
python scripts/verify_poc.py
```

This standard-library product verifier performs no provider call and executes
no candidate Python. Its recorded Windows increment passed 61 product,
mocked-transport and budget checks. A new invocation reports its own result.
The verifier also checks **six curated offline fixtures**, separate from the
three interactive browser cases and three historical Sandbox variants. Their
counts are not an accuracy benchmark.

Optional Node.js verification of the portable browser implementation is separate:

```sh
node judge-site/tests/engine.test.mjs
node judge-site/tests/visibility.test.mjs
```

The recorded portable suite passed 18 engine/DOM checks. The full legacy security
suite requires the reviewed Linux environment and its descriptor/filesystem
contracts. No macOS verification is claimed. Earlier 27-test evidence at
`c33fefb` is historical and is not proof of a later checkout's result.

## Significant work during this competition

The pre-existing MIT-licensed EvidencePilot verification core remains unchanged,
with its license, attribution and source pin retained. Earlier Q4 fixtures are
also identified separately. The original EvidencePilot repositories were not
modified.

New work adds the Nebius/NVIDIA integration, bounded parameter-to-source repair,
synthetic research fixture and counterexamples, recorded isolated validation,
interactive review and evidence download, portable public Pages build, direct
Token Factory CLI, persistent daily reservations and the current demo film. The
clean public snapshot contains no old private Git/PR history or old private
Release attachments. No unpublished research, patent materials or real quantum
hardware measurements are used.

## Tool feedback

- The Token Factory chat-completion interface made a tightly bounded integration
  practical. Typed Nemotron parameters were easier to validate independently
  than unconstrained model prose. The successful model was
  `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B`.
- Disposable Sandbox execution with networking disabled helped contain the three
  source variants and preserve inspectable records. Model access and Sandbox
  permissions remained separate checks.
- Clear account-effective spending caps, explicit credit coverage and consistently
  documented cost units would help distinguish a credit balance from a
  no-overdraft guarantee. We preserve unknown billed currency instead of treating
  a rounded balance as proof of zero cost.

## Selected movie and remaining steps

The current selected film is **LabRepair_DEMO_Public_20261030.mp4**, 123 seconds,
1080p/25 fps, with matching English subtitles and unchanged natural local Kokoro
male narration. Its corrected end card shows the verified public Demo and clean
submission repo. Exact artifact names, hashes and provenance belong to the
[canonical public media index](../media/demo-public-20261030/README.md).

The movie combines edited actual application footage, explanatory cards, labeled
AI illustration and saved real-run evidence. It is not continuous real-time
capture or a fresh Sandbox execution. Historical image content predates the
latest portable result-scrolling fix. The old
`media/demo-20261030-live-review/render_live_review.py` is an archived predecessor
renderer, not the selected-public-film entry point.

Remaining actions are event registration, public YouTube upload/watch-URL
verification and Devpost entry submission. Open registration/upload dialogs are
not completed actions. The YouTube channel is signed in, but no video has been
sent. Required owner answers and binding rules/terms confirmations are pending;
this draft does not supply them.

The [official rules](https://nebiusglobalaihackathon.devpost.com/rules) were checked
on 30 October: deadline **30 October 2026, 10:00 PDT / 31 October 2026, 01:00
Taipei**. The public project must remain freely available to judges through the
judging period ending 23 December 2026, 12:00 Pacific. Track eligibility remains
the organizer's decision.

No physical Bell experiment, loophole closure, quantum advantage, autonomous
scientific discovery, general repair security benchmark or successful
reproduction of the original 3.40 claim is established.
