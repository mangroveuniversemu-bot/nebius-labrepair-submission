# Portable offline handover — NEBIUS-008

This round delivers a useful review artifact: one bounded data file carrying the
request, exact three frozen fixture files, two response fixtures, original
source bindings, human-readable replay instructions and independently replayed
receipts. A recipient can verify it with the reviewed code in the full Coding
ZIP. No new account, network request, sandbox or candidate execution occurs.

## Reproduce

From the workspace root with its existing Python environment:

```
python -m labrepair.handover --replay evidence/nebius_008_handover.json --output evidence/nebius_008_my_replay.json
```

The receipt path must be new. Exit 0 means **matched offline replay**, not a
repair approval. The normal literal proposal stays BLOCKED on unverified
isolated execution and spending gates. The runner-edit proposal is REJECTED.
The code does not extract, import, execute or apply anything from the bundle.
All source text, including candidate Python, is data only.

`--export` creates a new bundle only from the operator-pinned NEBIUS-007 files.
Export also checks their historical saved receipts against fresh review. The
replay uses current operator source pins, NOT source authorization in the file.
Its manifest is a consistency check, not an authenticated signature. Rehashing a
forged live status, result, request, source or receipt does not open any gate.
Member names are exactly allowlisted; missing/extra entries, duplicate JSON,
invalid encoding and byte-limit violations are rejected. No overwrite of an
existing receipt, key handling, provider transport or live flag is exposed.

## Exact historical serialization

NEBIUS-007's protected-change check reviewed an 838-byte canonical JSON object.
The separately saved readable fixture is 925 bytes. Their SHA-256 values differ:
the receipt describes the canonical input, not the readable file on disk. This
handover explicitly stores the actual canonical reviewed bytes and records both
hashes and the normalization rule in origin.json. The normal case carries its
original 925 bytes. Original NEBIUS-007 files and receipts are unchanged.

## Observed account/source gates this round

On 2026-10-03 around 19:51 UTC, Token Factory displayed Log in. No authenticated
account, free-credit coverage, spending cap or exact-model entitlement could be
verified. No login/account/key/card/endpoint creation or model call was attempted.
This is a browser-session observation, not a conclusion that no account exists.
The shared Drive ZIP remains 107 KB, modified 02:54 Taipei; its latest bytes are
UNVERIFIED after the prior standard-download HTTP error. The older imported
snapshot remains pinned, byte-checked and explicitly not certified latest.

## Boundaries and next step

NVIDIA/Nebius inference, Sandbox/OpenShell, candidate execution, Tavily, AWS and
hardware remain NOT_RUN. Actual provider usage is unknown, not zero. Fixed-case
host tests verify the intake/export, not an isolated backend. The independent
invoice fixture is not a Bell/CHSH program repair or physical certificate; the
original EvidencePilot source and scientific decisions remain untouched.

Next build a read-only reviewer view of this handover's fresh normal/refusal
receipts, separate from the archived NEBIUS-005 source-unavailable workbench.
After the user provisions an account, verify entitlement, credits and a real
enforceable spend limit before any inference; verify actual isolation separately
before code execution. Do not repeatedly ask for keys or present the local
handover as completed hackathon technical compliance.
