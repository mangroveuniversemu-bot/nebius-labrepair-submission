# V3 bounded provider gate — offline implementation

Evidence: INTERNAL execution and SYNTHETIC fixtures. No provider or Sandbox run.

The active request envelope now requests `max_completion_tokens=256`, never a
fallback to the former `max_tokens=1024`. The account/model must independently
support a total completion ceiling including reasoning. Unknown support blocks
admission. The new bounded configuration is consumed by the existing admission
evaluator: one request, entire input <=512 tokens, total completion 256, SDK
retries zero, timeout 30 seconds, credit cost <=USD 0.01, new cash USD 0.
Missing, malformed, type-confused or relaxed configuration blocks policy.
Environment templates cannot override the reviewed hard limits.

Pricing claims must bind to the exact request and model, include all fees and
cover the entire input (system/user messages, schema and provider template) and
reasoning output. Decimal arithmetic checks the one-cent boundary and available
covered credit. Existing freshness, permission, provider hard-stop and disabled
charging checks remain mandatory. These are offline claims checks, not account
authentication. Even a complete synthetic/ operator claim stays runtime BLOCKED.
There is no HTTP transport, SDK client, live switch or candidate executor.
Consequently retry/timeout settings are checked preparatory options, not proven
provider enforcement; no real request can be sent by this implementation.

The existing full-source request is retained, not silently truncated. Its 5,211
serialized bytes are NOT a token measurement. A trusted model-specific total
input bound <=512 has not been established. If it cannot fit, prepare a reviewed
smaller typed suggestion request in a later increment; do not bypass the limit.
Do not use the synthetic 512-token evidence fixture as actual input measurement.

`evaluate_admission` refuses any dispatch state other than NEW, including unknown
or previously reserved/sent/completed states. The existing `FixtureSession` can
now take an operator-owned durable journal directory. Exclusive directory create
and fsync consume it before a simulated exchange. A new session cannot reuse it
after timeout, interruption, corrupt/empty state or concurrent reservation. The
marker deliberately remains DISPATCH_UNKNOWN and is labelled OFFLINE_FIXTURE_ONLY;
it is not a real provider intent or proof of durable account-wide dispatch.
Never delete a live reservation to retry. A future authenticated transport still
needs a persistent coordinator-owned live reservation and reconciliation.

Historical handover reconstruction explicitly uses its archived request format.
Historical bytes, source fixtures and saved verdicts are unchanged. The V3
admission path rejects that archived body, so replay compatibility cannot relax
new limits. Historical review still does not execute candidate code.

## Verification

Use Python 3.12 and requirements.txt (pydantic 2.13.5):

```bash
python -m unittest discover -s tests -v
python scripts/verify_offline_exchange.py
```

Positive synthetic policy evaluation remains runtime BLOCKED. Negative controls
cover missing cash/permission evidence, 513 input tokens, 257 completion tokens,
reasoning/scope ambiguity, one-cent exact/over boundary, unsafe configuration,
old archived request, repeated/unknown state, restart and concurrent reservation.
The verifier's fixed samples are trusted synthetic tests; its subprocesses are
not isolation and never execute arbitrary model candidate patches.
