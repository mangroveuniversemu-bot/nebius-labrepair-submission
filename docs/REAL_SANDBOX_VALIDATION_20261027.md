# Real model-to-isolated-test validation

The technical recording material now includes an observed NVIDIA model response
on Nebius and actual code execution in Nebius Sandboxes. The workbench displays
their saved receipts and can export the checked record without another API call.

## Observed execution

Run: `nebius-sandbox-validation-20261026-1`.
Accepted at **2026-10-26T16:07:55Z / 27 October 00:07:55 Taipei**.
HTTP 201, one POST, one status GET, zero retries, terminal **SUCCESS**, exit 0.
Operation: `01a178f7-ee09-7133-a4c4-87922e4db2eb`.
Provider operation duration: **1.273 seconds**; measured guest loop: 0.669504 s.

| Actual case | S | Checks passed | Process exit | Expected outcome |
| --- | ---: | ---: | ---: | --- |
| Original mapping | 0.10 | 2/4 | 1 | Failure observed |
| Real NVIDIA-proposed correction | 2.60 | 4/4 | 0 | Repair passed |
| Same total, wrong pair values | 2.60 | 3/4 | 1 | Failure observed |

All three expected outcomes were observed. There were twelve executed checks
with three deliberate control failures; this is **not twelve passing checks**.
Every case used the same SHA-pinned counts and protected test file. The guest
verified the source bytes before and after each subprocess. The original claim
remained `{claimed_s: "3.4", claim_state: "NOT_REPRODUCED"}` with physical
interpretation not established.

## Model and operator boundary

The archived NVIDIA Nano response was generated through Nebius with HTTP 200,
121 prompt tokens, 38 completion tokens and 826.48 ms latency. This stage did
not call the model again. The only model-contributed values were the validated
integer arrays `[1,1,-1,-1]` and `[0,0,0,0]`.

The operator-owned adapter constructed the bounded analysis source, fixed the
independent test logic and bound it to the recorded response and source hashes.
Only the two literal tuples may differ from the original analysis AST. The
baseline and deceptive alternative are declared operator controls. Candidate
Python was executed inside the actual Nebius guest, never on the host computer.

## Environment and containment observed

- Public `python:3.12-slim` image, immutable UUID
  `4fa16c8f-62a9-35a4-a4ea-07b7e8cd44ae`.
- Linux, x86_64, Python 3.12.13; guest interface list exactly `["lo"]`.
- Disposable operation, no result image retained, server execution timeout 30 s.
- Explicit PATH-only guest environment; no provider credential variable present.
- Guest process address-space limit 256 MiB, CPU-time limit 20 s and each child
  timeout 5 s; writable-layer ceiling 16 MiB, output capture 32 KiB per stream.
- The REST schema does not expose VM CPU/RAM allocation, so these process limits
  are not described as a one-CPU or fixed-memory VM allocation.

The original cloud checkout/index, historical fixture and generation receipt were
unchanged. Neither original EvidencePilot repository nor its vendored code changed.

## Evidence and replay

Exact stdout: 5641 bytes, SHA-256
`31c9900c3e55c6d2f059cf00f836f7cae836e781921d91de739da7be8f723b36`.
Safe operation and transport records retain status, measured resources and request
bindings without account/project IDs or credentials. Git attributes preserve
their exact bytes across platforms. These are client-observed receipts; content
hashes are not a cryptographic provider attestation.

```sh
python -c "from labrepair.recorded_validation import load_recorded_validation; import json; print(json.dumps(load_recorded_validation(), indent=2))"
python scripts/verify_poc.py
python -m labrepair.serve --port 8770
```

The preparation command `scripts/prepare_sandbox_experiment.py` constructs a
reviewable request for an explicit immutable image. It never submits a job.
The workbench has no provider-dispatch route, and the automatic admission gate
remains disabled. All files and counts in this experiment are synthetic.

## Billing and remaining delivery

The authenticated account displayed US$25.00 before the run. No top-up, billing
plan or card change was made. Sandbox rate and actual billed currency remain
unknown. The provider's raw `resources.cost` metric has unconfirmed units and
must not be reported as USD. A rounded account balance cannot prove a zero bill.

This bounded run establishes the three-case technical recording material; it is
not a broad security/performance benchmark or physical quantum experiment.
Final recording, judge-accessible release, Devpost registration verification and
publication/submission remain separate work. The repository stays private and
the draft PR stays unmerged pending the user's publication decision.
