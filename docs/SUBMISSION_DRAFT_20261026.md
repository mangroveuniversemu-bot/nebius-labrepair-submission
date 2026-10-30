# LabRepair — repair the analysis, preserve the evidence

Working draft. Track target: **Coding and Agentic Engineering**. Positioning:
**verification-first developer tool**. The official track accepts developer
tools; this draft does not claim an autonomous discovery or agent loop.
Judge-accessibility and publication gates below remain unresolved.

## Tagline

Two patches. Same total. One is wrong. Check the evidence behind the score.

## Inspiration

A researcher rarely needs another confident summary. They need to know which
input, convention or program produced a disputed result—and what a correction
would actually change. A plausible patch can match the headline number while
damaging the evidence beneath it. LabRepair makes that disagreement inspectable.

This is relevant to score-driven AI workflows: a successful headline metric can
hide a broken underlying condition. Our wrong-pair control demonstrates that
failure with fixed synthetic inputs. It is not evidence that a deployed model
performed reward hacking, nor a general detector or prevention benchmark.

## What it does

LabRepair turns a synthetic research-analysis discrepancy into a bounded review.
It binds a proposed patch to frozen source and policy, protects raw counts and
tests, recomputes each registered correlation and preserves the original claim.
A reviewer receives a replayable record and an explicit choice to hold or request
an isolated rerun. Repair acceptance and scientific-claim acceptance stay separate.

The new demonstration shows a declared detector-channel mapping omitted from
analysis code. The original claim is 3.40; the registered synthetic replay is
2.60. A correct mapping makes every pair agree. A misleading alternative also
produces 2.60 but fails the pairwise check. Other cases expose protected-test
tampering, stale source, injected executable instructions and incomplete evidence.

## How we built it

The existing MIT-licensed verification core remains unchanged. New code adds a
source-pinned scientific fixture, bounded proposal review, a local syntax-and-
arithmetic evaluator, an interactive workbench, review-intent records and an
evidence download. The browser and local server have no dispatch, payment,
credential-entry or arbitrary file access route.

Verified bounded architecture: NVIDIA Nemotron 3 Nano served through Nebius
Token Factory proposed the two parameter arrays. Independent tools checked the
source/policy binding, and an explicitly authorized Nebius Sandbox executed the
three source variants against unchanged protected tests. The correct repair
passed 4/4 checks; baseline and same-total/wrong-pair controls failed as expected.
The UI separately labels recorded live results and curated local scenarios.

The recorded prompt explicitly supplied the declared convention that flips the
A1 channels. The model's task was to translate that instruction into typed
parameters, not infer the missing convention from unknown experimental evidence.
We gave the model a deliberately small job; even a correct parameter response
cannot authorize the original scientific claim. The negative control is
operator-authored, not a second model generation.

## Demonstrated results and limits

Six fixed cases distinguish a locally consistent repair from four refused
proposals and an evidence request. A total-only comparison falsely accepts one
case in that fixed set; the full pairwise checker refuses it. These are bounded
synthetic observations, not a production accuracy or security benchmark.

The original scientific claim remains not reproduced after the correct repair.
Synthetic CHSH arithmetic does not establish a physical Bell experiment,
loophole closure, quantum advantage or a universal claim.

## Significant work during this competition

Pre-existing: the unchanged EvidencePilot verification core and earlier Q4
invoice fixtures, with attribution and licenses retained.

Added: the Nebius-oriented bounded request/admission contract, durable offline
reservation controls, portable source restoration, authenticated access checks,
new scientific repair fixture, complete interactive review, counterexample and
negative cases, downloadable decision evidence and the current test build.
No old private Git history, unpublished research or real hardware data is used.

## Feedback from actual integration

- Model catalogs and Sandbox token permissions are separate checks. Both returned
  HTTP 200; a later real disposable operation returned SUCCESS and exit 0.
- A credit balance is insufficient evidence of a no-overdraft spending policy.
  Clear account-effective spending controls and Sandbox promotion coverage would
  make small developer experiments easier to approve.
- Cloud command-network permission and managed destination/secret policy are
  separate. Diagnosing a permission error before the provider response resolved
  the separate NVIDIA developer-endpoint smoke without bypassing the proxy.

## Final fields still required

Technical recording prerequisite completed: actual Nebius-hosted NVIDIA repair
generation plus isolated before/after/negative-control execution. See
[observed results](REAL_SANDBOX_VALIDATION_20261027.md).

A new 123-second English demo records interactions with the current judge UI
and is privately saved in Drive. Its local natural male neural voice explicitly
names Nebius Token Factory and NVIDIA Nemotron and discloses the supplied
channel convention. The movie combines actual timestamped browser frames,
explanatory cards and saved real-run evidence; it is not a continuous real-time
recording or a fresh provider execution. Full-width generated character scenes are labeled illustration; their fictional
lab screens are scenery, not product or research evidence. Drive picture playback and 2:03
duration were observed; this revision does not claim cloud-original byte-hash
matching. See [current private media delivery](DEMO_RELEASE_20261030.md). The
earlier 155-second, 160-second and 142-second movies are preserved as historical artifacts.

1. Confirmed Devpost entry status; Builder Program receipt is not registration.
2. A judge-accessible test build URL or release, with its access and launch path
   actually verified. A private archive or a local server alone does not pass.
3. Public repository URL after the user's separate publication approval.
4. Public YouTube URL for a video under three minutes, after publication is
   approved. Existing owner-only Drive delivery is not public video publication.

Official requirements rechecked 30 October 2026:
https://nebiusglobalaihackathon.devpost.com/rules

Deadline: 30 October 2026 10:00 PDT / 31 October 2026 01:00 Asia/Taipei.
Current private repository is preparation, not a completed public submission.
The delivery version is on `codex/poc-completion-20261026` in draft PR #1;
`main` has not been merged. Re-run verification on the exact release candidate
before reporting its test status. Earlier 27-test evidence at `c33fefb` is
historical; it does not establish the later HEAD's current result.
