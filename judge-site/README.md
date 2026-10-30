# Portable judge demo

**`dist/index.html`** is designed to open directly in a current browser: the page
is self-contained and needs no server, Python installation, account or API key.
It makes no fetch or provider request. Direct local-file browser validation is
**NOT_RUN**: the available browser tool rejects `file://` URLs. That restriction
has not been bypassed. The actual checks completed are the offline Node engine,
standalone-script syntax and exact inline CSP hash checks described below.
The repository and build remain private; generating this export publishes nothing.

Start with **Check the wrong-pair repair**. The browser recomputes correlations
and the CHSH total from fixed synthetic counts using exact rational arithmetic:

| Sample | Candidate pairs | S | Browser outcome |
| --- | --- | ---: | --- |
| Declared repair | 0.70, 0.65, 0.75, -0.50 | 2.60 | PASS |
| Same-total control | 0.80, 0.75, 0.65, -0.40 | 2.60 | FAIL |
| Missing pair | No complete four-pair result | unknown | REVIEW |

The original claim remains 3.40 / NOT_REPRODUCED. A repair cannot establish a
physical quantum result. Candidate Python is displayed as text, never executed.
Only these three fixed candidates are supported; this is not a general Python
validator or an agent runner.

SHA-256 pins cover the raw source payload, the three protected source-file
bindings, source snapshot and policy before enabling calculation. Browser
receipts bind the exact computed values, candidate source and original claim.
They have a separate schema from the original Python receipts, whose reference
hashes are preserved. Hashes establish content integrity, not provider signatures
or reviewer identity. An owner who can replace the whole application can replace
its trust anchors; this is a portable demonstration, not remote attestation.

The saved real model/Sandbox summary is verified independently and displayed as
recorded evidence. Replaying it causes no cloud call. Its three real variants
are baseline, model fix and wrong-pair control; the missing-pair case is a browser
sample only. The prompt supplied the declared channel convention. Model output
was bounded parameter translation, not autonomous scientific discovery.

Review intent lives in the current page and can be downloaded together with its
bound receipt. It does not execute code, authorize payment or promote a claim.
There is no service persistence. Reloading clears the selection and intent.

## Rebuild and verify

Maintainers need Python 3.12 and the existing repository checkout. No packages are
installed. The builder reads existing trusted local functions, verifies source
pins and saved receipt bindings, and writes only this `judge-site/` directory:

```sh
python judge-site/build.py
node judge-site/tests/engine.test.mjs
node judge-site/tests/visibility.test.mjs
```

The offline tests compare actual JavaScript calculations with the current Python
reviewer; tamper a source input and saved result; reject unverified source, stale
receipts and cross-case intents; and verify the standalone CSP/build boundaries.
`build-result.json` records output hashes. `dist/` also contains modular assets
for inspection and tests, but only `index.html` is needed to open the demo.

The self-contained file requires WebCrypto. If unavailable, source checks fail
closed and calculation/download remain disabled. Direct local-file browser
behavior, download behavior and final layout remain pending manual validation.
The separate offline DOM-contract suite verifies result-focus/scroll ordering,
reduced-motion behavior, busy gating and fail-closed errors. It does not measure
actual browser pixels, speech output or download dialogs.
Hosting access control is a separate decision; an unlisted URL alone is not a
private deployment.

No changes to `review-app/`, `labrepair/serve.py`, provider adapters, original
EvidencePilot repositories, external sharing or deployment are part of this
demo export.
