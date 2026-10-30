# Fresh offline handover reviewer

NEBIUS-009 adds `handover-workbench/`, separate from the archived NEBIUS-005
`workbench/`. It displays a fresh independent replay of NEBIUS-008 data, not a
blindly trusted saved verdict. The two fixed invoice proposals remain BLOCKED
(unverified isolation and spending cap) and REJECTED (protected runner change).

Generate from the reviewed workspace:

    .venv/Scripts/python.exe -m labrepair.handover_view

Serve only the generated directory on loopback, not the project root:

    .venv/Scripts/python.exe -m http.server 8767 --bind 127.0.0.1 --directory handover-workbench

This is a static local preview, not a cloud deployment or isolation sandbox.
No JavaScript, external asset, Run/Apply/Approve button or network transport exists.
Three exact allowlisted JSON downloads provide bundle, fresh replay and separately
pinned historical NEBIUS-008 synthetic science context. Input is bounded, output
paths refuse symlinks/unexpected files and every candidate string is HTML escaped.

A replay failure produces a neutral failure page with no stale success/download
links. Existing downloadable files are retained as historical data, not endorsed
by that failed generation. The rejected QA preview is separate from the normal
page. No original source or previous receipt is rewritten by the renderer.

The saved Maya claim stays BLOCK (submitted S=2.61; replay S=1.9625), separate from
the invoice fixture. A future repair cannot silently promote that original claim.
No scientific repair or physical experiment is demonstrated by this view.
Checksums detect changes, not authenticated identity.

Real NVIDIA/Nebius inference and isolated execution remain NOT_RUN; actual usage
is unknown. Before any real test, independently verify model entitlement, covered
free credit and enforceable monetary cap, then actual isolation/protected tests.
Token limits alone are not monetary limits. Latest shared source comparison is
still UNVERIFIED; the reviewed older snapshot is independently byte-pinned.
