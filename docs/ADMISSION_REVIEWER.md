# Read-only provider admission report

The admission reviewer makes the existing offline provider/cost gate readable.
It rebuilds the fixed request from the pinned synthetic invoice source and calls
the evaluator again. It does not import a saved verdict, authenticate account
evidence, inspect credentials, contact a provider, or execute a candidate patch.

## Generate and open

Use Python 3.12 with the unchanged pinned `requirements.txt`. The filesystem
boundary requires POSIX directory descriptors and no-follow flags, verified on
the cloud Linux workspace. Unsupported platforms fail closed rather than fall
back to check-then-open paths:

```sh
python -m labrepair.admission_view --review-name review-001
```

Open `admission-workbench/review-001/index.html` directly in a browser. The page
has no scripts, external assets, forms or dispatch controls. Its only download
is the adjacent sanitized `report.json`. If serving locally, serve only that
one review directory on loopback; never serve the repository or user workspace.

The command returns 0 when report generation succeeds, including when claims
are missing or rejected. This is not an admission success: runtime admission is
always `BLOCKED`, and model/candidate execution are always `NOT_RUN`. Exit 2 means
the input file, pinned source or fresh output could not be used; no current report
was created. Errors do not echo paths, raw input or exception text.

Each review name is 1–64 ASCII letters, digits, underscores or hyphens, starting
with a letter or digit. Output is restricted to a new direct child of
`admission-workbench/`. Existing review folders are never overwritten, including
partial output from an interrupted write. Choose another name after an
interruption. JSON is written before HTML. If a write fails, any partial folder
is not a completed review. There is no latest/current alias that could silently
show an older successful generation as a new result.

An explicitly supplied claims document may be reviewed:

```sh
python -m labrepair.admission_view --review-name review-002 --admission-evidence evidence/claims.json
```

The file must stay inside this workspace's `evidence/` directory. Input and output
paths, including ancestors, use pinned directory handles and no-follow opens.
The tested input/output symlink swaps cannot redirect reads or writes. Reads stop
at the 16 KiB limit plus one overflow byte. Oversized input is rejected without a digest being recorded.
No file is loaded implicitly. The CLI has no clock override, live mode, model
selection or credential option. Argument errors are sanitized rather than echoing
unknown argument values. These checks do not establish host isolation or stop an
actor with local write access from moving or altering files after generation.

## Read the two outcomes

1. **Claim consistency:** `BLOCKED` or `CLAIMS_SATISFY_POLICY`. The latter says only
   that supplied claims meet the offline contract at the recorded review time.
2. **Runtime admission:** always `BLOCKED`. Independent account evidence is not
   authenticated and no live transport/runtime admission path exists.

Every emitted gate has a plain-English explanation. Missing claims do not mean
free inference. Pricing, free-credit coverage, a provider-enforced US$0 actual
cash cap, disabled automatic charging, specific credential-use permission,
model/schema access and real isolation must all be established independently.
A US$25 credit balance is not a US$25 cash allowance. The displayed US$0 policy
does not prove that the provider enforces a zero-cash hard stop.

`SYNTHETIC_FIXTURE` and `OPERATOR_ASSERTION` are both unauthenticated. A numeric
request-cost upper bound is a calculation over claims, not a current price,
measured bill or monetary control. Actual provider usage, cost and latency remain
`unknown`. The UI has no approval button or action to remove these blockers.

## Provenance and freshness

The JSON and HTML record the exact review time, request-body digest, input-evidence
digest when bounded, five pinned source/policy/suite bindings, and implementation
file hashes. The HTML includes the exact downloadable JSON byte count and digest.
It does not export raw claims, account-scope identifiers, keys, request contents,
candidate code or arbitrary metadata. An absent evidence digest is explicitly
shown as not recorded, not as proof that a document was authenticated.

Hashes establish byte integrity and binding only. They are not signatures or
authentication. Implementation hashes describe the local files at generation;
they do not attest that the host is trusted. The underlying invoice fixture is
a pinned older synthetic source; its latest remote match remains `UNVERIFIED`.

This static page is a point-in-time snapshot. It cannot notice expired claims or
later file changes. Regenerate before relying on freshness or after changing any
input/source. A complete synthetic example evaluated at a fixed test clock must
never be presented as fresh account evidence. The
[saved missing-evidence example](../admission-workbench/review-20261011T1855Z/index.html)
was generated without any claim document and remains a historical snapshot when
viewed later. Its HTML structure was checked offline; desktop/mobile visual QA
could not run because this cloud executor denied Chromium's local process socket.

The existing handover pages, historical scientific claim and vendor files are
unchanged. The new report does not re-evaluate or repair the Bell/CHSH example.

## Fixed offline checks

```sh
PYTHONPATH=tests python -m unittest test_admission_view -v
python -m unittest discover -s tests -v
```

The tests cover missing, malformed, oversized, expired, future-dated, synthetic
and operator claims; saved-verdict rejection; raw-data redaction; exact JSON/hash
links; static HTML/CSP; bounded path/symlink checks; fresh-directory reservation;
and repeated or failed generation. None is a live provider or isolation test.
