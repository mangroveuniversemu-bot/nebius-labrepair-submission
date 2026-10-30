# Archived recording draft: current evidence check

`scripts/verify_demo.py` checks the existing NEBIUS-010 English narration and
caption draft against its original, unchanged six source pins. It reports the
available evidence and every blocking gap as bounded JSON. It does not generate
a new demo, replay candidate code, verify a browser, record a video, package a
release, contact a provider or submit anything.

## Run on the reviewed cloud Linux checkout

From the repository root using Python 3.12:

```sh
python scripts/verify_demo.py
```

This default writes only to standard output. To save a new receipt explicitly:

```sh
python scripts/verify_demo.py --output evidence/demo-evidence-review-001.json
```

The parent directory must already exist. The receipt filename must be new.
Existing files, symlinks and symlinked ancestors are refused, with no overwrite.
The complete JSON is staged in an anonymous file on the same filesystem and
published atomically from its still-open inode, without clobbering a name created
by another writer. No mutable staging filename exists. A failed partial write is
discarded before any final receipt becomes visible.
Every source, draft, implementation, helper and archive input path is reserved:
it cannot be used as a receipt destination, even when the input is missing.
`source_inputs_modified: false` refers to these inspected inputs.
Reading requires Unix descriptor operations. Saving additionally requires Linux
anonymous temporary files and `/proc/self/fd` hard-link publication on the target
filesystem. Unsupported operations block rather than following a less-safe
path; standard-output inspection remains available when safe reads work.
No credential or model configuration is read.

## What the clean repository can establish

- Four included handover files match their original SHA-256 pins exactly.
- The included historical-domain JSON matches its original pin only after the
  reviewed, exact LF-to-historical-CRLF restoration. The report gives both
  observed and pinned-representation hashes and byte counts. It never modifies
  the stored file, repins it, reserializes JSON or accepts mixed-line-ending
  changes.
- The available pinned replay and domain records match the archived structured
  facts. This is a check of static evidence, not a fresh replay.
- The draft has six continuous scenes over a planned 165 seconds, with bounded
  caption timing and narration/caption equality. This does not prove free-text
  truth, manual content review, visual quality or an actual recorded duration.

The required `ops/nebius_009_checkpoint_final.json` is absent from the clean
repository. Its original pin remains required. The report therefore returns
`BLOCKED_EVIDENCE_GAPS`, `success: false`, and exit 2 even when the draft structure
matches. A fabricated replacement or a new hash cannot satisfy that requirement.

The archived draft document says that six pinned files were included in its
historical package. That statement is not evidence that all six are present in
this clean repository. The historical document, draft JSON and subtitles remain
unchanged; this current check makes the difference explicit.

The old verifier also tried to hash `scripts/package_checkpoint.py`, which is
absent here. Its absence is reported separately as historical packaging metadata
that is unavailable. That helper was never one of the six source pins and is not
made a requirement for checking narration. Packaging is not verified by this
command. The old source ZIP is optional historical context: absent bytes are
reported as missing, while a present but mismatched archive blocks the check.

## Status and exit codes

- Exit 2 and `BLOCKED_EVIDENCE_GAPS`: the report was produced, but required source
  evidence, input safety or draft structure failed. Review `blockers` and each
  artifact's status. Missing, mismatched, oversized, non-regular and unsafe paths
  are distinguished without echoing file contents or exception details.
- Exit 0 and `OFFLINE_DRAFT_CHECKS_MATCHED`: required static source pins and draft
  checks matched. This is still only a draft consistency result. `recording_ready`
  and `submission_ready` remain false, and manual review and recording are
  NOT_RUN. The current clean repository cannot reach this result without the
  authentic missing historical checkpoint.
- Exit 2 and `AUDIT_NOT_SAVED`: invalid arguments or the requested new receipt
  could not be used. An existing receipt is never replaced. This is not a
  complete audit result.

Every report retains live provider, isolated runtime, candidate execution,
recording and submission as NOT_RUN, and actual provider usage and cost as
unknown. The timestamp belongs to this inspection; the historical draft keeps
its original run identity. Checksums are not authenticated signatures.

## Resume condition

Recover the original checkpoint from an authorized historical artifact and
verify that its bytes match the unchanged operator pin before filling the gap.
Do not invent the checkpoint, silently remove its pin or treat the five present
files as all six. A separately authorized decision to create a new source-bound
recording draft would be a new artifact, with its own provenance and manual
review. Browser/recording work and live integration have separate unsatisfied
gates; this check does not clear them.
