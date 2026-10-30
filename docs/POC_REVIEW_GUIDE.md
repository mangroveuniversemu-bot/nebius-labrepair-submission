# Judge guide: scientific repair review

LabRepair is a **verification-first developer tool**, demonstrated with a
synthetic quantum-analysis case. Its recorded NVIDIA task translated an explicitly
declared detector convention into parameters; it was not autonomous discovery of
an unknown scientific correction. Code repair and the original scientific claim
receive separate outcomes.

Start the new application from the repository root:

```sh
python -m labrepair.serve --port 8770
```

Open `http://127.0.0.1:8770/`. The new workflow needs only Python's standard
library. The older domain bridge also needs the pinned `requirements.txt`.
No credential entry, account login, model endpoint or paid resource is required
to use this local review. Only the three allowlisted web assets are served.
The server refuses foreign Host/Origin headers, oversized bodies, arbitrary
paths and any attempt to dispatch code or a cloud job.

## A useful two-minute review

1. Select **Repair the declared channel mapping** and run the review. The
   registered correlations are 0.70, 0.65, 0.75 and -0.50. The proposed mapping
   produces S=2.60; the original claimed S=3.40 remains not reproduced.
2. Select **Same total, wrong pair evidence**. Its S is also 2.60, but its four
   correlations differ. The complete check rejects it. This is a measured
   counterexample in a fixed set, not a general false-accept-rate claim.
3. Try the protected-test, stale-source and executable-instruction cases. All
   are rejected. Missing pair evidence requests review rather than a guess.
4. Record **Hold for evidence** or **Request isolated rerun**. These are review
   intents only. They cannot authorize execution, payment or claim promotion.
5. Download the source-bound evidence JSON. It contains tool outcomes, proposal
   differences, file hashes, the unchanged original claim and runtime blockers.

## What ran, exactly

The three files in `fixtures/scientific/` are newly authored synthetic material.
They are separate from the unchanged vendored EvidencePilot source and the
missing Maya notebook. The proposed program is parsed as data. Only two literal
tuples may vary; the complete remaining AST must match the independently pinned
original. Trusted arithmetic recomputes rational-valued correlations from counts.
The candidate Python function is never imported, evaluated or executed.

This local semantic check is useful evidence, but it is not a Python test run
inside Nebius Sandboxes. The interface therefore says **Locally consistent**,
never “deployed”, “claim approved” or “isolated execution passed”. The six
proposals are reviewed literals, not fabricated model outputs.

The separate real-run panel displays previously observed model and Sandbox
evidence. It does not turn a new local review into a provider execution. A new
rerun remains a separate authorization; the saved completed operation is not
evidence that another run was requested or paid for.

## Verify and replay

```sh
python scripts/verify_poc.py
python scripts/verify_poc.py --output evidence/my-new-poc-validation.json
```

Use a fresh output name. Existing evidence is not overwritten. Full verification
of the earlier Linux descriptor protections uses the reviewed Linux environment:

```sh
python -m pip install -r requirements.txt
python scripts/verify_poc.py --full
```

Windows and Linux results are reported separately. A passing local suite does
not establish provider entitlement, paid-use controls or competition eligibility.
Run the command on the checkout being reviewed. The archived 27-test result at
`c33fefb` must not be relabeled as verification of a later HEAD. The older
`verify_demo.py` recording-checkpoint command is documented only in
[archived validation notes](ARCHIVED_VALIDATION.md).

## Recorded real integration

The authenticated catalog and permission checks were followed by actual
separately authorized integration work:

- NVIDIA `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B` served through **Nebius Token
  Factory** returned HTTP 200, using 121 input / 38 completion tokens.
- One disposable **Nebius Sandbox** operation executed three source variants
  against identical protected counts and tests in 1.273 seconds.
- Baseline passed 2/4 checks and failed as expected; the model repair passed
  4/4; the same-total, wrong-pair operator control passed 3/4 and was rejected
  as expected. This is twelve checks with three deliberate control failures.
- The original 3.40 claim stayed `NOT_REPRODUCED`; physical interpretation
  remains `NOT_ESTABLISHED`. The incomplete-evidence case is curated local
  review, not a fourth recorded cloud case.

See [model evidence](REAL_GENERATION_20261026.md) and
[Sandbox evidence](REAL_SANDBOX_VALIDATION_20261027.md). Hashes bind archived
content; they are not provider signatures or proof of physical quantum results.

## New execution and publication remain separate

Before any new actual compute, independently verify fresh no-new-cash controls,
applicable pricing and promotional-credit coverage. Then use the existing secure
credential mechanism only for an explicitly authorized bounded request. The
local review has no provider-dispatch route. Existing successful runs do not
enable automatic execution or establish an account-wide cash cap. Missing billing
quantities stay unknown. Never enable execution with a fixture flag.

The current repository and narrated video delivery copies remain private. The
draft branch is not merged into `main`, and judge-accessible build/source/video
URLs plus confirmed Devpost submission remain pending. Starting this loopback
server does not constitute deployment. A prepared test-build archive or release
must not be marked judge-accessible until the actual access path is verified.
