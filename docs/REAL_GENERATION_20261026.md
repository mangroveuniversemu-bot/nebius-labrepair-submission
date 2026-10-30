# One real Nebius-hosted NVIDIA parameter suggestion

Run `nebius-nano-repair-20261026-1` sent exactly one authorized request at
2026-10-26T15:14:43Z. It used the saved credential through the managed cloud
proxy with TLS verification. No credential, account identifier, private research,
hardware measurement or source history is included in this evidence.

## Observed result

- Endpoint: `https://api.tokenfactory.nebius.com/v1/chat/completions`
- Model: `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B`
- HTTP 200; finish reason `stop`; latency 826.48 ms.
- Provider usage: 121 prompt + 38 completion = 159 tokens.
- Request: one completion, maximum 64 completion tokens including reasoning;
  reasoning disabled, no streaming/tools/retries/redirects, 30-second timeout.
- Response: 795 bytes, SHA-256
  `ed0c2272968d84c4844a1305ca0ad68560451615d147c7eaa9f4f41231419920`.

The model returned `channel_signs=[1,1,-1,-1]` and `offsets=[0,0,0,0]`.
The operator-owned adapter accepts only these two bounded integer arrays. It
constructs an in-memory proposal bound to the pinned source and policy; it never
imports, executes or writes candidate Python. Trusted rational arithmetic
independently produces `[0.70,0.65,0.75,-0.50]`, matching every registered pair,
and S=2.60. The original 3.40 claim remains **NOT_REPRODUCED**, unchanged.
This is a new synthetic analysis, not evidence from a missing original notebook.

## Replay without calling a model

```sh
python scripts/review_model_response.py evidence/nebius-nano-repair-20261026-1/response.json
python -m unittest tests.test_model_parameters tests.test_scientific_workflow -v
```

The archived request/response bytes and cloud transport receipt are separate
from the local review. Offline replay can check content and hashes; it cannot
authenticate a provider's identity. No saved response can authorize payment,
candidate execution or a scientific conclusion. Negative controls reject code,
extra keys, duplicate keys, booleans, nonfinite values, tool calls and truncated
responses. Well-formed incorrect parameters fail the independent pair check.

## Cost and remaining boundaries

The authenticated account showed US$25.00. Current account Prices showed
uncached input US$0.06/M and output US$0.24/M (non-batch, eu-north1, excluding
applicable tax). The official pinned NVIDIA tokenizer and chat template measured
121 full prompt tokens; returned provider usage independently matched.

The conservative 512-input/64-output estimate was US$0.00004608. Applying the
same rates to reported usage yields **US$0.00001638 before tax**, an estimate,
not an invoice. Actual billed money is **unknown**; a rounded balance cannot
prove zero charges. No top-up, new plan, card change or paid resource was created.
An account-wide no-overdraft cap is **NOT_ESTABLISHED**.

Sandbox execution and OpenShell are **NOT_RUN**. Sandbox pricing and credit
coverage remain unverified. The automatic admission gate was not changed or
enabled, no scheduled inference loop was enabled, and no arbitrary model code
was executed. This run proves hosted inference plus local parameter verification,
not a complete Coding-track isolated write/run/test workflow. The repository
remains private; no main merge, public release or submission occurred.

Primary references:

- [Nebius chat completion API](https://docs.tokenfactory.nebius.com/api-reference/inference/create-chat-completion)
- [NVIDIA tokenizer and reasoning configuration](https://huggingface.co/nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-BF16)
- [Nebius billing](https://docs.tokenfactory.nebius.com/other-capabilities/billing-new)
