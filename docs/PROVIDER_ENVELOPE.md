# Offline provider envelope — NEBIUS-007

This increment connects the pinned Q4 Coding source to a concrete Nebius request
preview and a saved-response review. It is useful integration code, not a live
model, deployment, real provider usage, isolated execution or track compliance.
The independent invoice fixture does not replace the original Bell/CHSH work.

## What is implemented

`labrepair.provider_envelope.prepare_request()` constructs deterministic request
bytes from the operator-pinned source loader. It includes exactly cases.json,
ledger.py and runner.py, their hashes, the snapshot/policy/staging-manifest/suite
bindings and an output schema. Only ledger.py can be proposed for editing.
The known CORRECT literal is not included in the prompt. Source content is
explicitly labeled untrusted data; independent path/hash checks enforce scope.

The fixed endpoint is https://api.tokenfactory.nebius.com/v1/chat/completions.
The preview uses one non-streaming completion, a planned max_tokens=1024 and
strict JSON-schema output. The request is limited to 16 KiB locally. There are
no tools, arbitrary endpoints, credentials, headers, retry loop or live switch.
No transport is implemented. These planned limits are NOT an enforceable cost
cap or a measured token estimate, and model-specific parameter support is not
verified. `nvidia/Nemotron-3_5-Lightning` is an existing unverified candidate ID;
its syntax, name or presence in a preview does not establish model availability,
NVIDIA provenance, licensing, account entitlement or JSON-schema support.

`review_offline_response()` consumes up to 64 KiB of untrusted saved JSON. It
rebuilds the draft from current operator pins before accepting any content,
requires the exact planned model label, one stopped assistant completion and
rejects truncation, refusal, tool calls, malformed/duplicate JSON and oversized
content. The model field is a consistency check, NOT identity authentication.
The candidate passes through the existing hash/path/byte gate. Protected files,
stale policy, request tampering and model-supplied readiness fail closed. No
candidate is executed, applied or declared test-passing. Valid fixture proposals
still become BLOCKED on unverified isolation and spending gates.

Actual provider usage stays unknown. Optional sanitized counts in an offline
fixture are recorded separately as `fixture_reported_usage`, never real usage.
Missing, negative, boolean or inconsistent counts remain unknown, not zero.
The adapter does not reflect arbitrary response metadata, IDs, error strings or
credentials into reports. Diff text is untrusted and must be escaped by any UI.

## Reproduce this actual offline round

From the workspace's prepared Python environment:

```
python scripts/verify_provider_envelope.py
python -m labrepair.provider_envelope --output evidence/nebius_007_request_preview.json
python -m labrepair.provider_envelope --response-fixture evidence/nebius_007_response_fixture.json --output evidence/nebius_007_response_intake.json
```

Both CLI operations intentionally exit 2: no dispatch is possible. The saved
response is assembled from the original reviewed CORRECT literal, NOT generated
by a model. The negative response proposes changing runner.py and is REJECTED.
Commands, input/source hashes, local timings, tests and exact receipts are saved
in nebius_007_verification.json. The 17 original Coding tests are separate
fake-client/recovery tests; 277/45/60/72 historical totals are not included.
No original source, shared ZIP, old workbench receipt or other lane is modified.

## Official references checked 2026-10-03 UTC

- [Nebius quickstart](https://docs.tokenfactory.nebius.com/quickstart): the fixed
  API base and chat-completion message structure.
- [Structured output](https://docs.tokenfactory.nebius.com/ai-models-inference/json):
  json_schema/strict examples, refusal handling and model-dependent support.
- [API introduction](https://docs.tokenfactory.nebius.com/api-reference/introduction):
  stopped assistant responses and provider token-usage field shapes.
- [Model listing](https://docs.tokenfactory.nebius.com/api-reference/examples/list-of-models):
  authenticated catalog and per-model metadata; no authenticated request was made.
- [Billing](https://docs.tokenfactory.nebius.com/other-capabilities/billing-new):
  standard onboarding and automatic card charges. Promotional credits alone do
  not establish a hard stop. No account/card/billing changes were made.

The NVIDIA-model marketing page could not be opened by this round's research
tool; exact candidate availability remains UNVERIFIED. The latest shared ZIP
listing changed to 107 KB modified 02:54 Taipei; standard download again reported
HTTP error. The imported older snapshot remains byte-verified, not certified
latest. Rules already researched October 3 are not re-scanned in this increment.

## Next exact gate

Read-only verify an already provisioned Token Factory account's exact NVIDIA
model ID/schema support, covered free credits and enforceable spending limit.
If any remains unverified, do not send inference or create a sandbox. Continue
with a small replayable handover/export increment instead. A future transport
must separately record genuine request/usage/timing/error receipts, forbid
automatic retries, then hand proposals only to a truly verified isolated backend.
No model-provided flag, a generic subprocess or a fake-client test can open it.
