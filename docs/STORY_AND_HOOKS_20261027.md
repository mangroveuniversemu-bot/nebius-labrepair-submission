# LabRepair story and demo hooks

Reviewed on 27 October 2026. This brief draws editorial lessons from official
winner announcements and builders' published descriptions. It does not claim
that these patterns caused the awards, that their code was independently
audited here, or that their outcomes establish LabRepair's effectiveness.

## Positioning

**LabRepair — A passing repair is not a reproduced result.**

LabRepair helps a research engineer review a bounded NVIDIA-proposed code repair
against protected inputs and independent checks, while retaining the original
scientific claim as a separate decision. The current demonstration uses a new
synthetic Bell/CHSH channel-mapping case and separately recorded real model and
Nebius Sandbox executions.

The user has an understandable job: decide whether to accept a repaired analysis
without rewriting what the original evidence supports. Code repair and scientific
reproduction receive separate verdicts. The bounded mechanism supports that job;
the architecture is explained after the viewer sees the problem.

## Lessons from the reviewed winners

| Competition and observed example | Editorial lesson | LabRepair application |
| --- | --- | --- |
| Build with Gemini XPRIZE: Polyfork won first place. XPRIZE reports paying customers and revenue from configurable 3D assets. TICIAN Cierre placed second; its project page describes aggregate figures that balanced while individual receipts were invalid. | A specific deliverable and inspectable outcome make the value legible. An aggregate can conceal a consequential error. | Show the paired-correlations counterexample and the research handover. No invented customers, revenue, avoided losses or time savings. |
| Gemini 3 Hackathon: Globot won the grand prize. Its project description opens with a supply-chain disruption and the operator's decision. | A person facing a concrete decision is easier to grasp than a list of agents. | Start with a research engineer comparing two plausible repairs. Borrow the narrative structure, not the project's unverified performance claims. |
| Google Cloud All Things Agentic: Plant Debugger won the grand prize. Its published workflow couples agent planning to operator observations and deterministic recovery checks; plant dynamics are explicitly simulated. | Show how new evidence changes the workflow, and make the person's contribution meaningful. | Separate model proposal, independent checks and the researcher's conclusion. Keep synthetic inputs and recorded execution explicit. |
| OpenAI Build Week: veTriage won first in Work & Productivity; Dấu and Sentinel placed second in Education and Developer Tools. OpenAI describes domain-specific workflows, usable feedback and deliberately bounded AI roles. | Domain knowledge, a comprehensible interaction and visible limits can support a focused product story. | Put input correlations and the two verdicts on screen. Explain a constrained model proposal in the middle of the demo, not as the opening hook. |

These examples also show why a deterministic verification layer alone should not
be presented as an unprecedented invention. LabRepair's current distinction is
the observable separation between **repair correctness**, **evidence integrity**
and **the original research claim**, demonstrated with a same-total counterexample.
This is a positioning argument, not a claim of technical novelty over every entry.

## Three narrative beats

The opening now identifies the protagonist as a **quantum research software
engineer**. This is an illustrative user role, not a customer testimonial. Their
job is to turn detector counts and channel conventions into a defensible analysis.
The concrete pain in this synthetic case is a mapping error that changes the
reported result while an aggregate check can miss inconsistent individual pairs.
No hardware experiment, quantum advantage, customer saving or industry-wide
failure rate is implied.

This focus is consistent with the importance of preserving code, measurement
and configuration artifacts discussed in [1-2-3 Reproducibility for Quantum
Software Experiments](https://arxiv.org/abs/2201.12031), and the separation of
experiment, data and analysis in [Qiskit Experiments](https://joss.theoj.org/papers/10.21105/joss.05329).
These sources motivate the workflow; neither independently evaluates LabRepair.

The spoken hook is now seven words: **Two patches. Same total. One is wrong.**
Both the valid repair and the deliberately wrong operator control remain labeled.
The engineer's introduction precedes the hook; its spoken reveal still finishes
within the opening fifteen seconds.

1. **Visible contradiction:** two candidate patches both compute 2.60. Only one
   matches the protected individual correlations. Label the deliberately wrong
   operator control from its first appearance.
2. **A useful repair:** the actual NVIDIA-proposed parameters pass four checks
   inside the real Nebius execution. Inputs and protected tests stay fixed.
3. **A restrained conclusion:** the original 3.40 claim remains NOT_REPRODUCED.
   Accepting a code repair does not authorize changing the scientific conclusion.

The first hook earns attention. The real execution supplies technical evidence.
The final distinction explains why this matters to the researcher.

## Recorded evidence to use

| Case | Computed S | Checks passed | Observed result |
| --- | ---: | ---: | --- |
| Baseline | 0.10 | 2/4 | Expected failure |
| NVIDIA-proposed repair | 2.60 | 4/4 | Repair passed |
| Deliberately wrong, same-total control | 2.60 | 3/4 | Expected rejection |

Correct correlations: `[0.70, 0.65, 0.75, -0.50]`.
Wrong control: `[0.80, 0.75, 0.65, -0.40]`.
Both totals are 2.60; a total-only predicate cannot distinguish them. This is a
mathematical comparison of these fixed cases, not a newly run ablation study.

Use the archived NVIDIA response's 121 input / 38 completion tokens and the
Sandbox operation's 1.273-second duration as supporting evidence. These measure
different stages; do not add them into an invented end-to-end benchmark. Do not
turn one repaired case into an accuracy rate or claim a monetary saving.

The 155-second [recording script](DEMO_WALKTHROUGH_20261027.md) and its
[narration source](demo_narration_20261027.json) use the current
workbench and existing receipts. No new API call is required. Judge-accessible
publication, user validation, broader task coverage and a continuous product
execution loop remain separate delivery work; they are not implied by this story.

## Sources

- [XPRIZE official winner announcement](https://annualreport.xprize.org/news/polyfork-wins-the-build-with-gemini-xprize)
- [TICIAN Cierre builder's project description](https://devpost.com/software/tician-cierre)
- [Gemini 3 official winner announcement](https://gemini3.devpost.com/updates/40729-the-moment-you-ve-been-waiting-so-patiently-for)
- [Globot builder's project description](https://devpost.com/software/globot-341w9q)
- [All Things Agentic official winner announcement](https://allthingsagentichackathon.devpost.com/updates/45669-the-moment-you-ve-long-awaited-winners-are-here)
- [Plant Debugger builder's project description](https://devpost.com/software/plant-debugger)
- [OpenAI official Build Week winner profiles](https://developers.openai.com/blog/build-week-winners)

Winner status comes from the official announcements. Workflow descriptions and
reported product outcomes retain their original publisher's provenance. These
sources inform storytelling; they do not license copying another project's code,
research material or unsupported claims into LabRepair.
