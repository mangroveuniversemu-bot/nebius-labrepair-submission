# Judge interface acceptance — 28 October 2026 (Taipei)

Current release review and portable browser build: [2026-10-30 record](DEMO_RELEASE_20261030.md). The dated checks below retain their original scope.

LabRepair remains a verification-first developer tool for quantum research
software. This increment improves the zero-key judge path; it does not publish,
merge, submit, deploy a hosted service or run another model.

## Reviewer path

1. Start `python -m labrepair.serve --port 8770` and open the printed loopback URL.
2. Select sample A and run: **PASS / Locally consistent**, four matching pairs.
3. Select sample B and run: **FAIL / Proposal rejected**, same 2.60 total but four
   disagreeing pairs. Selecting a sample clears prior results and export state.
4. Select sample C and run: **REVIEW / More evidence needed**. Unknown pair values
   remain unknown, visibly distinct from contradictory evidence.
5. Record a hold or rerun intent and download its source-bound local receipt.
   A delayed response from another review cannot attach intent to the new one.
6. Inspect the separately labeled recorded Token Factory and Sandbox evidence.
   Playback does not generate a new model call. Its prompt explicitly supplied
   the convention; it did not ask the model to discover an unknown correction.

## Acceptance observed this increment

- 29 cross-platform Python product checks passed, including real loopback HTTP,
  tampered/absent receipt refusal, protected-source checks and six fixed cases.
  This is separate from the historical 27-test result and from the old real run.
- Three Node standard-library regressions passed against the actual UI script:
  stale A intent cannot attach to B, overlapping decisions are refused, and a
  stale response cannot unlock a newer pending decision. No network was used.
- Browser checks in a newly opened localhost tab observed A=PASS, B=FAIL,
  C=REVIEW, selection-only=READY, and hold intent. The browser did not supply an
  account or API key. This is not an isolated browser profile or hosted endpoint.
- A temporary fault-injection server refused only the receipt reader. The browser
  visibly reported **SAVED EVIDENCE UNAVAILABLE**, disabled the cloud receipt
  download, and still completed a local review. No original file or pin changed.
- GET `/healthz` checks only service liveness; GET `/ready` checks saved receipt
  readiness. Both are provider-free. A failed receipt read returns 503 for
  readiness/evidence while local sample review remains independent.
- The saved real execution remains the three-case run from 26 October UTC:
  baseline 2/4; model repair 4/4; wrong-pair control 3/4. The curated incomplete
  case has not been run in that cloud operation. No fresh provider test occurred.

## Delivery gates

| Gate | Current evidence | Remaining action |
| --- | --- | --- |
| G0 Canonical | Private delivery branch `codex/poc-completion-20261026`; base of this increment `993954b` | Keep one explicit release ref; main is still older |
| G1 UI journey | Local three-case browser journey and source-bound HTTP export verified | Isolated judge context / accessible test-build validation pending |
| G2 Real provider | Pinned earlier Token Factory NVIDIA generation and real Sandbox receipts | No new run required to replay these records |
| G3 Controls | Real baseline/wrong-pair rejection; curated local uncertainty; receipt failure and async intent controls | Do not relabel local uncertainty as cloud execution |
| G4 Deployment | Loopback-only UI plus provider-free health/readiness | Hosted or distributed judge-access path remains pending |
| G5 Verification/release | New local product checks, UI observation and source manifest | CI has not been run; no private Actions job enabled |
| G6 Submission | Draft PR, private source/media, private prepared artifacts | Public source/video/build access and Devpost confirmation pending |

A local PASS does not close G4 or G6. A readable private Drive video is not a
public YouTube submission. A test-build ZIP is not a hosted URL or submitted entry.

## Official-rule distinctions

Official pages checked for this increment: [rules](https://nebiusglobalaihackathon.devpost.com/rules),
[overview](https://nebiusglobalaihackathon.devpost.com/),
[FAQ](https://nebiusglobalaihackathon.devpost.com/details/faqs).

- Deadline: **30 October 2026, 10:00 PDT = 31 October, 01:00 Taipei**.
- Coding includes developer tools. No explicit autonomous-loop requirement was
  found. The actual required platform/model use still needs to be demonstrated.
- Public code with license/instructions, a working demo or test build, and a
  public YouTube video under three minutes are required delivery items.
- Demonstrate Token Factory and NVIDIA integration. No literal spoken-brand
  phrase requirement was found; naming them precisely reduces ambiguity.
- Rule 5 restricts changes after the deadline; it is not a present-day feature
  freeze requirement. This increment intentionally keeps the bounded task.

## Media alignment

The verified 27 October 155-second movie is preserved unchanged and predates
this UI revision. A separate [160-second current-UI film](DEMO_MEDIA_20261028.md)
now records actual interactions at UI commit `4c1cc58`, names Nebius Token
Factory and NVIDIA Nemotron, and discloses the supplied channel convention.
Its local neural narration, new subtitle timings and output hashes are recorded
separately. The film is edited for explanation; it is not a real-time performance
benchmark. Public video/build access and Devpost confirmation remain pending.

## Boundaries

Synthetic inputs only; no physical Bell experiment, quantum advantage or broad
accuracy claim. The original 3.40 claim stays NOT_REPRODUCED and physical
interpretation stays NOT_ESTABLISHED. Checksums establish integrity, not provider
signatures. Actual billed money and account-wide cash controls remain unknown.
No new paid resources, model requests, publicity or submission were performed.
