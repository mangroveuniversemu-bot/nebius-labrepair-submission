# Read-only review workbench

NEBIUS-005 adds a product-facing handover view over the saved intake receipts.
It is not an agent execution UI, a shared-source import or a deployment.

```powershell
.\.venv\Scripts\python.exe -m labrepair.workbench
.\.venv\Scripts\python.exe -m http.server 8766 --bind 127.0.0.1 --directory workbench
```

Open `http://127.0.0.1:8766/`. Serve only `workbench/`, not the project root.
Stop the preview server with Ctrl+C when finished. No login, remote assets,
JavaScript, approvals or code execution are involved. Receipt downloads are the
three fixed, public-safe JSON inputs copied byte-for-byte; their SHA-256 values
are displayed for replay. SHA-256 is not an authenticated identity attestation.

## Two records, deliberately separate

- Actual local intake: saved NEBIUS-004 CLI `BLOCKED` because source is absent.
- Six arithmetic intake scenarios: synthetic contracts and synthetic gates;
  `READY_FOR_ISOLATED_TEST` means only eligibility for a later isolated test.
- Scientific context: the unchanged saved LAB-001 synthetic Maya replay, whose
  original claim is `BLOCK`. This is not the arithmetic candidate's verdict.

The page does not refresh cloud access or rerun input receipts. It shows their
origin and retains `NOT_RUN` / `unknown`. A successful intake cannot promote a
scientific conclusion. No Run, Apply or Approve action exists; implementing
approval persistence or execution requires another reviewed increment.

## Display boundary

All receipt values, paths, hashes, reasons and diffs are HTML-escaped. Candidate
HTML is visible text, not page markup. Content Security Policy disables scripts,
connections, images, frames, objects, base changes and form actions. The builder
refuses contradictory execution or entitlement labels, unexpected case identities
and a changed local/scientific gate instead of rendering them as accepted.

Negative tests include script/image injection in the diff, path, reason and hash,
forged provider/execution success and altered scientific/actual intake verdicts.
These test renderer contracts, not a claim of general browser or VM isolation.

## Source limitation

The first browser download event timed out. Later a successful workbench receipt
download revealed the browser's actual D-drive download directory. The earlier
shared ZIP download was there: 106,493 bytes, SHA-256
`b05e56d9c553ecd7ec19b159501cd966d55eab5b0c43a3c34399e3dbf7ef0b5f`.
All 36 manifested entries passed; a read-only copy is retained locally in inputs/.
AGENTS, README and the actual state/results/CODING-003 records were read/parsed.
The original contract receipt names cases.json, ledger.py and runner.py. No shared
source behavior was imported or executed. The latest remote version changed again
to 01:53 Taipei; matching it to this older snapshot is still UNVERIFIED. See
evidence/nebius_005_source_recovery.json. This UI remains an independent extension,
not a replacement for the original adapter or an OpenShell deployment.
