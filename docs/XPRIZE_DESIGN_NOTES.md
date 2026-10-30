# XPRIZE design references and LabRepair direction

Researched 2026-10-03. These are design inferences, not the judges' private reasons
for awarding prizes. No competitor code or assets are copied.

## Verified awards

The [XPRIZE final announcement](https://www.xprize.org/news/polyfork-wins-the-build-with-gemini-xprize)
names Polyfork first, TICIAN Cierre second, C2x Professional Services Access winner,
TRAMA AI Small Business Services winner, and MergeGate Agentic Economy winner.
It supersedes the older Top 100 page's finalist labels. Prize claims are not
inferred from project marketing alone.

## What to learn, and what not to copy

| Reference | Observed product pattern | Our design inference |
| --- | --- | --- |
| [Polyfork](https://devpost.com/software/polyfork) | Editable program-based 3D assets and a harness that inspects actual output | Make the handover executable, not just a prose report; show input-to-result visibly |
| [TICIAN Cierre](https://devpost.com/software/tician-cierre) | Domain-specific reconciliation; deterministic arithmetic; external audit and recorded disagreements | Compare the submitted analysis with registered replay; preserve disagreement rather than auto-approve |
| [C2x](https://devpost.com/software/c2x) | Domain expertise, sourced figures, explicit demo labeling and human responsibility | Put quantum analysis expertise in the scene; mark every fixture synthetic and state who must decide |
| [MergeGate](https://devpost.com/software/mergegate) | Pinned tests, protected paths, reproducible acceptance and explicit model-advisory boundary | Use immutable tests and repair receipts, but avoid competing as another generic code escrow |

Financial, customer, test-count and performance claims in project stories are
entrants' reports, not independently reproduced results. We do not reuse those
numbers as evidence for our own product.

## Positioning decision

**EvidencePilot LabRepair: reproducible repair of scientific analysis code.**

Audience: the research engineer who must review an analysis before a group
decision. The first scene is a synthetic Bell/CHSH analysis with a declared but
unapplied detector-channel correction. The submitted number looks exciting;
registered replay contradicts it. The useful product finds the discrepancy,
proposes a bounded repair, and hands back evidence the engineer can rerun.

Distinct promise: an analysis program can be fixed while its original scientific
claim remains rejected. Code acceptance and scientific-claim acceptance are
different records. A green test cannot silently promote a physical conclusion.

This connects the old AWS research-verification project to Coding work through
an actual scientific program repair, not a replacement cloud logo.

## Interface direction

One workbench, not a general chatbot:

1. **Claim versus replay**: submitted number, recomputed number, synthetic label.
2. **Investigation**: observed tool results, ambiguity and missing evidence.
3. **Repair review**: actual diff, protected inputs/tests, execution status.
4. **Handover**: immutable original certificate, separate revision and reviewer
   intent, limitations, downloadable replay instructions.

Unknown/offline/live statuses must be visible. A failed or unconfigured provider
must not render as a zero-cost successful run. Keep model explanations separate
from measured values. Do not present local policy checks as VM isolation.

## Evidence to build next

- Correct patch: same raw counts and convention; repaired analysis matches replay.
- Wrong patch: fits the claimed total but disagrees with per-pair evidence.
- Test/contract tampering: changes a protected test, raw counts or convention.
- Ambiguity: two explanations fit the total; missing per-pair evidence requests
  more information rather than guessing.
- Counterfactual comparison: naive total-only acceptance versus full validation.
  Quantify false accepts only after running that evaluation, not before.

The public Maya fixture's notebook is missing by design. We must add a separately
labeled synthetic repair-program fixture; we cannot claim to repair that absent
original notebook or invent its source code provenance.

## Provider fit

The [Nebius rules](https://nebiusglobalaihackathon.devpost.com/rules) require real
Nebius inference or AI Cloud compute plus an NVIDIA open model. Coding additionally
targets agents that write/run/test code in Token Factory. The [Sandbox API](https://docs.tokenfactory.nebius.com/sandboxes/overview)
is Beta and needs access verification. OpenShell alone does not prove this gate.

[Nemotron on Nebius](https://nebius.com/services/token-factory/models/nvidia-nemotron-models-inference)
provides the reasoning layer through the [Token Factory API](https://docs.tokenfactory.nebius.com/quickstart).
Keys, actual credit coverage, exact model IDs and Sandbox entitlement are separate
checks. No GPU rental, fine-tuning, payment integration or hardware acquisition is
part of this first setup.
