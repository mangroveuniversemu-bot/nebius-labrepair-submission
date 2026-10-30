# Bounded exchange contract — NEBIUS-011

This is an offline provider-adapter increment, **not a real HTTP client or model
call**. It closes an integration gap between the existing immutable request and
response-intake adapter: what happens on authentication errors, rate limits,
redirects, TLS failures, truncated or oversized replies, and rejected proposals
that still report token usage. No SDK, key, account or network is accessed.

## Implemented behavior

`labrepair.offline_exchange.FixtureSession` accepts only an explicitly synthetic
`HTTPFixture`, not a client/callback, credential or operator grant. It rebuilds
the request from independent source pins before consuming one exchange. The
same session cannot exchange again, even after a timeout or HTTP error; a lock
also prevents concurrent double consumption. This is a local fixture-session
limit, **not an account-wide monetary cap or a verified runtime policy**.

The endpoint is fixed to the existing Token Factory chat-completions endpoint.
Redirects are never followed. Failures are classified without copying error
text, arbitrary headers, response extensions, IDs, proposal text or credentials
into the receipt. A response read is bounded to 64 KiB plus one detection byte;
an oversized read records a prefix hash, not a claimed whole-response digest.

Only HTTP-200 JSON enters the existing independent candidate reviewer. Normal
invoice proposals remain BLOCKED; protected-test edits are REJECTED. The original
scientific certificate is not evaluated or promoted by this Coding fixture.
Sanitized `fixture_reported_usage` is retained separately even when the proposal
is refused. Missing/invalid usage and all **actual provider usage** remain
`unknown`, never an assumed zero bill. Local elapsed time is not provider time.

The default CLI only produces a disabled-live preflight. There is no `--live`,
model-owned readiness flag, arbitrary URL, automatic retry or credential option.
The three fixed original files remain the only reviewed source scope; no patch
is staged or executed. New receipts must use new paths inside `evidence/`.

## Reproduce

From this workspace using its existing prepared Python environment:

```
python scripts/verify_offline_exchange.py
python -m labrepair.offline_exchange --output evidence/my_disabled_preflight.json
python -m labrepair.offline_exchange --fixture evidence/nebius_011_normal_wire_fixture.json --output evidence/my_offline_exchange.json
```

Both CLI examples exit 2 intentionally: they cannot dispatch or approve a repair.
The verifier exercises normal/error CLI flows, overwrite refusal, six negative
controls, local regression and six separate synthetic domain replays. Its saved
counts are actual executions; earlier checks are not added to this round's total.
Any Q4 adapter regression uses fake-client/recovery fixtures, not real OpenShell.

## Official API references

Checked on October 3 UTC, resumed October 4 without another model/account claim:

- [Quickstart](https://docs.tokenfactory.nebius.com/quickstart) documents the
  fixed API base and an OpenAI-compatible chat-completion request.
- [Structured output](https://docs.tokenfactory.nebius.com/ai-models-inference/json)
  documents JSON/schema output, refusal handling and model-dependent support.
- [API introduction](https://docs.tokenfactory.nebius.com/api-reference/introduction)
  documents request/response integration and token-usage fields.

The offline failure/refusal policy here is our conservative design; these
references do not verify the account's exact NVIDIA model, entitlement, schema
support, free credits, enforceable cost ceiling or actual isolation. No SDK was
installed. A future authenticated bounded client still needs those independent
account-evidence gates, no redirect/retry, genuine usage/timing/error receipts,
and a verified isolated backend before candidate execution. This module cannot
enable them with a fixture field or by renaming a mock as live.

Drive synchronization remains a separate PENDING_SYNC obligation. A passing local
contract rehearsal is not a cloud save, deployed agent or approved submission.
