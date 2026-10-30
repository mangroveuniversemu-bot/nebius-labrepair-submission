# GitHub release delivery / 30 October 2026

The release candidate is a private, versioned application delivery. Its tag pins
the exact source commit; the Release assets contain the self-contained interactive
test build, source archive, verified 123-second movie, subtitles, review bundle
and SHA-256 checksums. Repository readers can download these without a Drive link.

## Review

Extract the interactive ZIP and open `index.html` in a current browser. Choose the
wrong-pair repair: its total is 2.60, but all four correlations disagree. Compare
the declared repair, then missing evidence. No provider key or cloud job is used.
The browser build passed 12 offline engine, tamper and binding checks; its direct
file layout/download QA is still NOT_RUN because the browser tool rejects local
file URLs. Unsupported cryptography disables calculation and download.

The source archive includes the original Python workbench. With Python 3.12:

```sh
python -m labrepair.serve --port 8770
```

Open `http://127.0.0.1:8770/`. The server remains loopback-only. This original
workbench and its protected source fixture are preserved.

## Actual verification

- 29 Windows product, recorded-evidence and loopback HTTP checks passed on
  30 October. The first restricted attempt could not use local sockets/temp files;
  its failed receipt is retained beside the successful run.
- The portable engine passed 12 offline parity/negative-control checks. The
  asynchronous UI regression suite passed 3 checks. These are separate suites.
- Generated browser assets use LF on all operating systems, preserving exact
  build hashes and inline content security policy.
- Release ZIP CRCs and every packaged payload hash are checked locally. Uploaded
  asset sizes/digests are read back separately after the upload.
- No fresh model/Sandbox request or GitHub Actions job is part of packaging.
  CI/cloud free-minute availability is unverified, so paid compute is not enabled.
  Full legacy Linux security verification was not repeated on Windows.

The movie playback and decode were checked in the prior media increment. Movie
edit scripts depend on the prior raw-production Drive archive, local voice model
cache and Windows fonts in the media source reference. Application rebuilding
needs only Python's standard library and Node for offline JavaScript checks.

## Access boundaries

The repo remains PRIVATE. This Release is available to its existing readers,
not anonymous judges. There is no hosted website yet. GitHub Pages can expose a
website even when its source repository is private; private source also requires
an eligible existing plan. No plan upgrade, public exposure or paid hosting is
part of this private delivery. See [GitHub Pages documentation](https://docs.github.com/en/pages/getting-started-with-github-pages/creating-a-github-pages-site).

Public source/build access, a public YouTube upload, integration feedback and
Devpost submission remain separate publication steps. The synthetic example,
supplied channel convention and original 3.40 / NOT_REPRODUCED limits remain.
