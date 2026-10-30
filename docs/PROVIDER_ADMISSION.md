# Offline provider/cost admission gate

This increment replaces the disabled-live preview's static list with a strict,
replayable evidence-claim evaluator. It makes no account, model, credential,
billing, sandbox or network call. It never applies or executes candidate code.
No provider SDK or dependency was added.

## Two separate outcomes

`labrepair.provider_admission.evaluate_admission()` returns:

- `policy_evaluation`: `BLOCKED` or `CLAIMS_SATISFY_POLICY`, describing only the
  consistency and completeness of supplied claims.
- `runtime_admission` and overall `status`: always `BLOCKED` in this prototype.
  Independent account evidence is not authenticated and no transport exists.

The evaluator accepts only `SYNTHETIC_FIXTURE` or `OPERATOR_ASSERTION` evidence.
Neither label establishes authority, availability, provider identity, actual
pricing, billing enforcement or user permission. Even all-true claims cannot
grant live execution. Hashes establish integrity/binding, not authenticity.
No config flag, credential in an environment variable, model response or
candidate proposal supplies a grant. Configuration records the zero-cash policy
descriptively; the evaluator does not use config values to relax that policy.

## Fail-closed contract

The request must rebuild exactly from the current pinned source. An evidence
document is separate from response/candidate intake and at most 16 KiB. Invalid
UTF-8/JSON, duplicate keys, non-JSON numbers, unknown or missing fields, and
invalid field types are blocked. Reports contain allowlisted reasons and hashes,
not account identifiers, evidence text, keys, arbitrary metadata or error text.

The exact `LABREPAIR_PROVIDER_ADMISSION_V1` schema is defined by `ROOT_FIELDS`,
`SCOPE_FIELDS` and `SECTION_FIELDS` in the evaluator. Required evidence covers:

1. A common provider, fixed endpoint, exact model, request-byte digest and opaque
   account-scope digest. Each pricing, credit, cash-control and permission section
   independently carries the common scope digest and a source-evidence digest.
   Mixed account/request records and absent evidence hashes fail closed.
2. Strict UTC verification and expiry timestamps. The current time must be at or
   after verification and strictly before expiry; the entire validity window is
   at most 15 minutes. Expired, future-dated and excessively long-lived records
   fail closed. This is a local policy limit, not a provider guarantee.
3. Verified USD input/output rates, a verified input-token upper bound for this
   exact request, output bound matching its `max_tokens`, one request, and a claim
   that all fees are included. Missing prices or unbounded input cannot become
   zero cost. Rates and balances are bounded decimal strings, never binary floats,
   booleans, exponent notation, negative values or non-finite numbers.
4. Verified free-credit coverage for this request and a balance at least the
   decimal cost upper bound. The estimate is input-bound times input-rate plus
   output-bound times output-rate, divided by one million. It is a calculation
   over supplied claims, not a quote, real usage or a monetary enforcement limit.
5. A provider-enforced hard cap of exactly US$0 actual cash and fail-closed behavior
   on credit exhaustion. US$25 credit balance does not authorize US$25 cash.
6. Automatic top-up, overage charging and pay-as-you-go all explicitly false.
   Unknown, absent or truthy/falsy substitute values cannot pass.
7. Separate credential-use permission, model entitlement, schema support and
   verified isolated-backend claims. Each must be the Boolean `true`. A model or
   response cannot add these fields to bypass its existing strict intake schema.

All actual provider usage, cost and latency stay `unknown`; the model and
candidate execution stay `NOT_RUN`. Synthetic rate and balance values in the
tests are invented fixtures, not Nebius prices or verified account information.

## Reproduce

Use Python 3.12 with the unchanged pinned `requirements.txt`:

```sh
PYTHONPATH=tests python -m unittest test_provider_admission test_offline_exchange test_provider_envelope -v
python -m labrepair.offline_exchange --output evidence/new_disabled_admission.json
```

The CLI exits 2 intentionally and requires a fresh output path inside `evidence/`.
It refuses a symlinked evidence root or input/output paths resolving outside it.
An optional `--admission-evidence evidence/claims.json` evaluates a bounded
operator-supplied claim document while still blocking dispatch. It is mutually
exclusive with `--fixture`; response fixtures cannot double as admission claims.
No evidence file is loaded implicitly. See `synthetic_evidence()` in
`tests/test_provider_admission.py` for the fixed synthetic positive example and
the negative mutations. Its timestamps are deliberately fixed for replay using
the test's explicit clock, not suitable as current account evidence.

The existing full fixed replay has not become a live provider test. Do not count
earlier replay totals as tests executed by this increment.

## Remaining live blockers

Before any future live implementation, independently establish account ownership,
scoped credential-use authorization, current covered prices/credits, genuine hard
zero-cash enforcement, disabled automatic charging, exact model/schema access
and real isolation. A trusted evidence collection/authentication boundary, atomic
request/budget consumption and actual transport/runtime enforcement are still
unimplemented. Evidence assertions and this offline policy pass do not replace
those requirements or grant permission to provision resources.
