"""Generate a fresh, script-free provider admission review. Never dispatch."""

import argparse
import html
import json
import os
import re
import stat
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from labrepair.candidate_review import digest
from labrepair.paths import ROOT
from labrepair.provider_admission import MAX_EVIDENCE_BYTES, evaluate_admission
from labrepair.provider_envelope import prepare_request
from labrepair.q4_source import SourceUnavailable

SCHEMA = "LABREPAIR_ADMISSION_VIEW_V1"
REVIEW_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}\Z")
SOURCE_FILES = (
    "labrepair/admission_view.py", "labrepair/provider_admission.py",
    "labrepair/provider_envelope.py", "labrepair/candidate_review.py",
    "labrepair/q4_source.py", "labrepair/q4_pins.py", "requirements.txt",
)
BINDINGS = (
    "source_archive_sha256", "snapshot_sha256", "policy_sha256",
    "workspace_manifest_sha256", "suite_sha256",
)
CSP = (
    "default-src 'none'; script-src 'none'; connect-src 'none'; "
    "style-src 'unsafe-inline'; img-src 'none'; frame-src 'none'; "
    "object-src 'none'; base-uri 'none'; form-action 'none'"
)
REASONS = {
    "INVALID_REQUEST_DRAFT": "A valid fixed request is unavailable. Restore the reviewed source and regenerate.",
    "REQUEST_OR_SOURCE_UNAVAILABLE": "The fixed source could not be verified. Restore the reviewed pins and regenerate.",
    "REQUEST_BINDING_MISMATCH": "The request differs from the current pinned source. Rebuild the request before review.",
    "ADMISSION_EVIDENCE_MISSING": "No separate evidence claims were supplied. Pricing, credit coverage, cash controls and permissions remain unverified.",
    "INVALID_ADMISSION_EVIDENCE_TYPE": "Evidence must be bounded UTF-8 JSON bytes, supplied separately from a candidate response.",
    "ADMISSION_EVIDENCE_TOO_LARGE": "The evidence input exceeds the 16 KiB limit. It was not evaluated.",
    "INVALID_ADMISSION_EVIDENCE_JSON": "The input is not strict UTF-8 JSON. Check encoding, duplicate keys and JSON values.",
    "INVALID_ADMISSION_EVIDENCE_SCHEMA": "The input does not match the exact admission-claim schema. Saved verdicts are not evidence inputs.",
    "ADMISSION_SCOPE_MISMATCH": "Claims do not bind to this exact provider, model, request and account scope.",
    "SECTION_EVIDENCE_BINDING_MISMATCH": "Each claim section needs matching scope and source-evidence hashes.",
    "INVALID_EVIDENCE_TIME": "Verification and expiry must use valid UTC timestamps and an aware review clock.",
    "STALE_OR_FUTURE_ADMISSION_EVIDENCE": "Claims are expired, future-dated or have a validity window longer than 15 minutes. Obtain a fresh independent check.",
    "VERIFIED_PRICING_OR_REQUEST_BOUND_MISSING": "Exact covered USD prices, all fees and bounded input/output/request counts are not established.",
    "COVERED_FREE_CREDITS_UNVERIFIED": "Free-credit coverage for this exact request is not established.",
    "INSUFFICIENT_COVERED_FREE_CREDITS": "The claimed covered credit balance is below the calculated request bound.",
    "ENFORCEABLE_ZERO_CASH_CAP_UNVERIFIED": "A provider-enforced US$0 actual-cash hard stop, including credit exhaustion, is not established.",
    "AUTOMATIC_CHARGING_NOT_VERIFIED_DISABLED": "Automatic top-up, overage charging and pay-as-you-go must all be explicitly disabled.",
    "CREDENTIAL_USE_PERMISSION_MISSING": "Specific credential-use permission has not been established. This report never reads a key.",
    "MODEL_ENTITLEMENT_UNVERIFIED": "Access to the exact model has not been established.",
    "MODEL_SCHEMA_SUPPORT_UNVERIFIED": "The exact model's required response-schema support has not been established.",
    "ISOLATED_BACKEND_UNVERIFIED": "An actual isolated backend and its protected-test boundary have not been established.",
    "INDEPENDENT_ACCOUNT_EVIDENCE_NOT_AUTHENTICATED": "Claims and hashes do not authenticate an account, billing controls or permission. A trusted verification boundary is still missing.",
    "LIVE_HTTP_TRANSPORT_NOT_IMPLEMENTED": "There is no live transport or runtime admission path in this prototype. A consistent claim document cannot enable one.",
}
CSS = """
*{box-sizing:border-box}body{margin:0;background:#f2f5f4;color:#19343b;
font:16px/1.55 system-ui,sans-serif}header{background:#19343b;color:#eff7f6;
padding:20px max(24px,calc((100vw - 1120px)/2));display:flex;justify-content:space-between;
gap:16px;font:700 12px/1.5 ui-monospace,monospace;letter-spacing:.04em}
main{max-width:1120px;margin:auto;padding:38px 24px}h1{font-size:40px;line-height:1.15;
margin:8px 0 18px;max-width:850px}h2{font-size:21px;margin:0 0 12px}
h3{font-size:15px;margin:0 0 8px}p{margin:8px 0 16px}.intro{max-width:810px;color:#4a666d}
.eyebrow{font:700 12px/1.4 ui-monospace,monospace;color:#527178;letter-spacing:.06em}
.boundary{border-left:5px solid #9a6117;background:#fff0d4;padding:18px 22px;margin:24px 0}
.boundary p{margin:5px 0;font-size:14px}.grid{display:grid;grid-template-columns:1fr 1fr;
gap:18px}.panel{background:#fff;border:1px solid #d4e1e1;padding:22px;margin-bottom:18px;
min-width:0}.badge{display:inline-block;background:#ffe5b6;color:#714108;
font:750 12px/1.5 ui-monospace,monospace;padding:6px 10px;margin-bottom:10px}
.neutral{background:#e6eeee;color:#34565f}.small{font-size:13px;color:#526d73}
.metrics{display:grid;grid-template-columns:repeat(3,1fr);border:1px solid #d4e1e1;
background:white;margin:22px 0}.metrics div{padding:16px;border-right:1px solid #d4e1e1}
.metrics span{display:block;font-size:12px;color:#526d73}.metrics b{font:700 17px/1.6 ui-monospace,monospace}
ol,ul{padding-left:22px}li{padding:6px 0}li p{margin:3px 0 7px}code,dd{
font:12px/1.55 ui-monospace,monospace;overflow-wrap:anywhere}code{color:#31565e}
dl{margin:0}dt{font-size:12px;font-weight:700;color:#526d73;margin-top:13px}
dd{margin:3px 0 12px}a{color:#125c68}a:focus-visible,summary:focus-visible{
outline:3px solid #137d84;outline-offset:4px}nav{display:flex;flex-wrap:wrap;gap:20px;
font-size:14px;margin:24px 0}details{background:white;border:1px solid #d4e1e1;margin-bottom:18px}
summary{padding:18px 22px;font-weight:650;cursor:pointer}.details-body{padding:0 22px 20px}
footer{font-size:12px;color:#526d73;margin-top:24px}.download{display:inline-block;
border:1px solid #65888e;padding:10px 14px;font-weight:650;margin:8px 0 12px}
@media(max-width:700px){main{padding:26px 16px}h1{font-size:31px}.grid{grid-template-columns:1fr}
.panel{padding:18px}.metrics{grid-template-columns:1fr}.metrics div{border-right:0;
border-bottom:1px solid #d4e1e1}header{flex-wrap:wrap;padding:16px}.boundary{padding:14px 16px}}
"""


def _escape(value) -> str:
    return html.escape(str(value), quote=True)


def _reason_list(reasons: list[str]) -> str:
    if not reasons:
        return "<p>No claim-consistency blockers at this review time. Runtime stays blocked.</p>"
    return "<ol>" + "".join(
        f"<li><code>{_escape(reason)}</code><p>{_escape(REASONS.get(reason, 'Unknown gate; no admission can be inferred.'))}</p></li>"
        for reason in reasons
    ) + "</ol>"


def _hash_rows(values: dict) -> str:
    return "<dl>" + "".join(
        f"<dt>{_escape(name)}</dt><dd>{_escape(value if value is not None else 'not recorded')}</dd>"
        for name, value in values.items()
    ) + "</dl>"


def _render(report: dict, report_raw: bytes) -> bytes:
    admission = report["admission"]
    claims = admission["policy_evaluation"]
    kind = admission["evidence_kind"]
    cost = admission["claimed_request_cost_upper_bound_usd"]
    body = (
        "<div class='eyebrow'>FRESH OFFLINE EVIDENCE REVIEW</div>"
        "<h1>Provider access stays blocked.</h1>"
        "<p class='intro'>A readable review of separate provider and cost claims, rebuilt from the pinned synthetic invoice request. "
        "No model call, candidate execution or account verification has taken place.</p>"
        "<section class='boundary' aria-label='Authorization boundary'><strong>US$0 maximum authorized actual cash</strong>"
        "<p>A US$25 credit balance is not a US$25 cash allowance. The zero-cash policy is not proof of provider enforcement.</p>"
        "<p>Synthetic fixtures and operator assertions are unauthenticated. Even complete claims never authorize dispatch.</p></section>"
        f"<p class='small'>Reviewed at <time>{_escape(report['generated_at_utc'])}</time>. "
        "Point-in-time snapshot only. Regenerate after any input or source change and before relying on claim freshness.</p>"
        "<nav aria-label='Report sections'><a href='#blockers'>Blockers</a><a href='#provenance'>Provenance</a>"
        "<a href='#report'>Sanitized report</a></nav>"
        "<div class='grid' id='blockers'><section class='panel'><h2>01 · Claim consistency</h2>"
        f"<span class='badge neutral'>{_escape(claims)}</span>"
        "<p class='small'>Only the supplied claims are checked against offline policy. This is not verified provider evidence.</p>"
        f"{_reason_list(admission['policy_reasons'])}</section>"
        "<section class='panel'><h2>02 · Runtime admission</h2><span class='badge'>BLOCKED</span>"
        "<p class='small'>These independent blockers remain even when claim consistency passes.</p>"
        f"{_reason_list(admission['runtime_reasons'])}</section></div>"
        "<div class='metrics' aria-label='Unmeasured provider activity'>"
        "<div><span>Actual provider usage</span><b>unknown</b></div>"
        "<div><span>Actual provider cost</span><b>unknown</b></div>"
        "<div><span>Actual provider latency</span><b>unknown</b></div></div>"
        "<section class='panel'><h2>What this review establishes</h2>"
        f"<p>Evidence kind: <code>{_escape(kind)}</code>. Claimed request-cost upper bound (USD): <code>{_escape(cost)}</code>.</p>"
        "<p class='small'>Any numeric bound is calculated from supplied claims; it is not a current quote, measured cost or cash control. "
        "Missing evidence never means zero cost.</p>"
        "<p class='small'>Model: NOT_RUN · Isolated candidate execution: NOT_RUN · Provider requests made by this review: 0 · Credentials accessed: false.</p>"
        "<p class='small'>Next: independently establish exact pricing and credit coverage, provider-enforced zero-cash controls, disabled automatic charging, "
        "specific credential-use permission, model/schema access and isolation. This page cannot collect or authenticate that evidence.</p></section>"
        "<details id='provenance'><summary>Inspect evidence, request and pinned-source provenance</summary><div class='details-body'>"
        "<p class='small'>Hashes bind exact bytes and detect changes. They do not authenticate accounts, evidence authors or provider controls. "
        "The request uses a pinned older synthetic fixture; latest remote fixture match remains UNVERIFIED.</p>"
        f"{_hash_rows({'Request body SHA-256': admission['request_body_sha256'], 'Evidence input SHA-256': admission['evidence_sha256']})}"
        f"<h3>Fixed request source</h3>{_hash_rows(report['source_bindings'])}"
        f"<h3>Review implementation SHA-256</h3>{_hash_rows(report['implementation_sha256'])}"
        "</div></details><section class='panel' id='report'><h2>Keep the review record</h2>"
        "<p class='small'>This download contains sanitized reasons, states, time and hashes. It excludes raw claims, account identifiers, "
        "credentials, request text and candidate code. A saved report is not an admission token.</p>"
        "<a class='download' href='report.json' download>Download sanitized JSON</a>"
        f"{_hash_rows({'report.json SHA-256': digest(report_raw), 'report.json bytes': len(report_raw)})}</section>"
        "<footer>Read-only static report. No scripts, external assets, dispatch controls or patch-apply actions. "
        "The historical handover and scientific claim are unchanged.</footer>"
    )
    return (
        "<!doctype html><html lang='en'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        f'<meta http-equiv="Content-Security-Policy" content="{_escape(CSP)}">'
        "<meta name='referrer' content='no-referrer'><title>LabRepair · Admission review</title>"
        f"<style>{CSS}</style></head><body><header><span>LABREPAIR / ADMISSION</span>"
        f"<span>READ-ONLY · NO DISPATCH</span></header><main>{body}</main></body></html>"
    ).encode("utf-8")


def create_view(evidence_raw: bytes | None = None, *, now: datetime | None = None) -> dict[str, bytes]:
    """Re-evaluate input claims; never accept or render a caller-supplied verdict."""
    current = datetime.now(timezone.utc) if now is None else now
    if type(current) is not datetime or current.utcoffset() is None:
        raise ValueError("INVALID_REVIEW_CLOCK")
    draft = prepare_request()  # Raises on unverified source; no stale report is copied.
    admission = evaluate_admission(draft, evidence_raw, now=current)
    if any(admission[name] != value for name, value in {
        "status": "BLOCKED", "runtime_admission": "BLOCKED", "model": "NOT_RUN",
        "candidate_execution": "NOT_RUN", "actual_network_requests": 0,
        "credentials_accessed": False,
    }.items()):
        raise ValueError("OFFLINE_BOUNDARY_CHANGED")
    bindings = json.loads(json.loads(draft.body)["messages"][1]["content"])["bindings"]
    implementation = {}
    for name in SOURCE_FILES:
        raw_source = _read_under(ROOT, Path(name), 1_048_576)
        if len(raw_source) > 1_048_576:
            raise ValueError("IMPLEMENTATION_SOURCE_TOO_LARGE")
        implementation[name] = digest(raw_source)
    report = {
        "schema": SCHEMA,
        "mode": "FRESH_OFFLINE_ADMISSION_REVIEW",
        "generated_at_utc": current.astimezone(timezone.utc).isoformat(),
        "point_in_time_only": True,
        "evidence_authentication": "NOT_IMPLEMENTED",
        "hash_meaning": "INTEGRITY_AND_BINDING_ONLY_NOT_AUTHENTICITY",
        "source_kind": "PINNED_OLDER_SYNTHETIC_INVOICE_FIXTURE",
        "latest_remote_fixture_match": "UNVERIFIED",
        "source_bindings": {name: bindings[name] for name in BINDINGS},
        "implementation_sha256": implementation,
        "admission": admission,
    }
    raw = (json.dumps(report, indent=2, sort_keys=True) + "\n").encode("utf-8")
    return {"report.json": raw, "index.html": _render(report, raw)}


def _require_safe_descriptors() -> None:
    if (
        not all(hasattr(os, flag) for flag in ("O_NOFOLLOW", "O_DIRECTORY", "O_NONBLOCK"))
        or not all(operation in os.supports_dir_fd for operation in (os.open, os.mkdir))
    ):
        raise ValueError("SAFE_FILE_DESCRIPTORS_UNAVAILABLE")


@contextmanager
def _directory(path: Path):
    """Pin every directory component without following links, then keep its FD."""
    _require_safe_descriptors()
    absolute = path if path.is_absolute() else Path.cwd() / path
    if absolute.anchor != "/" or ".." in absolute.parts:
        raise ValueError("DIRECTORY_PATH_FORBIDDEN")
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    descriptor = os.open("/", flags)
    try:
        for component in absolute.parts[1:]:
            child = os.open(component, flags, dir_fd=descriptor)
            os.close(descriptor)
            descriptor = child
        yield descriptor
    finally:
        os.close(descriptor)


def _read_under(directory: Path, relative: Path, limit: int) -> bytes:
    if relative.is_absolute() or ".." in relative.parts or not relative.name:
        raise ValueError("INPUT_PATH_FORBIDDEN")
    with _directory(directory / relative.parent) as parent:
        descriptor = os.open(relative.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
        with os.fdopen(descriptor, "rb") as stream:
            if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
                raise ValueError("REGULAR_INPUT_REQUIRED")
            return stream.read(limit + 1)


def _read_claims(path: Path) -> bytes:
    evidence = ROOT / "evidence"
    absolute = path if path.is_absolute() else Path.cwd() / path
    try:
        relative = absolute.relative_to(evidence)
    except ValueError:
        raise ValueError("EVIDENCE_PATH_FORBIDDEN")
    return _read_under(evidence, relative, MAX_EVIDENCE_BYTES)


def write_view(name: str, files: dict[str, bytes]) -> Path:
    """Reserve a fresh review directory; publish HTML only after the JSON exists."""
    if not REVIEW_NAME.fullmatch(name) or set(files) != {"report.json", "index.html"}:
        raise ValueError("INVALID_REVIEW_OUTPUT")
    _require_safe_descriptors()
    output = ROOT / "admission-workbench"
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    with _directory(ROOT) as root:
        try:
            os.mkdir("admission-workbench", dir_fd=root)
        except FileExistsError:
            pass
        output_fd = os.open("admission-workbench", flags, dir_fd=root)
        try:
            os.mkdir(name, dir_fd=output_fd)  # Exclusive reservation; no overwrite.
            target_fd = os.open(name, flags, dir_fd=output_fd)
            try:
                for filename in ("report.json", "index.html"):
                    descriptor = os.open(filename, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                                         0o600, dir_fd=target_fd)
                    with os.fdopen(descriptor, "wb") as stream:
                        stream.write(files[filename])
            finally:
                os.close(target_fd)
        finally:
            os.close(output_fd)
    return output / name


class _SafeParser(argparse.ArgumentParser):
    def error(self, message):
        # argparse's default includes unknown argument text, which may be private.
        raise ValueError("INVALID_COMMAND_LINE")


def main() -> int:
    parser = _SafeParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--review-name", required=True, help="new review name; letters, digits, underscores or hyphens")
    parser.add_argument("--admission-evidence", type=Path, help="explicit UTF-8 claims file inside evidence/")
    try:
        args = parser.parse_args()
        if not REVIEW_NAME.fullmatch(args.review_name):
            raise ValueError("INVALID_REVIEW_NAME")
        raw = _read_claims(args.admission_evidence) if args.admission_evidence else None
        files = create_view(raw)
        write_view(args.review_name, files)
    except (SourceUnavailable, ValueError, OSError, RuntimeError):
        # No raw evidence, paths, account data or exception text in errors.
        print(json.dumps({"view": "NOT_CREATED", "runtime_admission": "BLOCKED",
                          "reason": "INPUT_SOURCE_OR_NEW_OUTPUT_UNAVAILABLE", "model": "NOT_RUN"}))
        return 2
    print(json.dumps({"view": "CREATED_OFFLINE_REPORT", "review_name": args.review_name,
                      "runtime_admission": "BLOCKED", "model": "NOT_RUN"}))
    return 0  # Report generation only, never provider or repair admission.


if __name__ == "__main__":
    raise SystemExit(main())
