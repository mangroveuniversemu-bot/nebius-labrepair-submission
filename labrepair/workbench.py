"""Build a script-free, read-only view of saved offline intake receipts.

No proposal is applied, imported or executed. Display values are always escaped.
The output directory contains only a static page and three allowlisted receipts;
it is safe to serve that directory, never the entire project or user workspace.
"""

import hashlib
import html
import json
from datetime import datetime, timezone

from labrepair.paths import ROOT

RUN_ID = "20261003T164615Z-nebius-005"
INPUTS = {
    "intake-receipt.json": "nebius_004_intake_demo.json",
    "local-gate-receipt.json": "review_cli_receipt.json",
    "domain-replay-receipt.json": "domain_baseline.json",
}
STATUSES = {"READY_FOR_ISOLATED_TEST", "REJECTED", "BLOCKED"}
LABELS = {
    "reviewable_diff": "Bounded candidate diff",
    "protected_test_change": "Protected test tampering",
    "stale_snapshot": "Stale source snapshot",
    "wrong_policy": "Wrong policy binding",
    "missing_external_gates": "Missing isolation & cost gates",
    "source_unavailable": "Unavailable verified source",
}


def text(value) -> str:
    return html.escape(str(value), quote=True)


def require_offline(receipt: dict) -> None:
    if (
        receipt.get("status") not in STATUSES
        or receipt.get("execution") != "NOT_RUN"
        or receipt.get("model") != "NOT_RUN_BY_REVIEWER"
        or receipt.get("source_written") is not False
        or receipt.get("network_requests") != 0
        or receipt.get("usage") != "unknown"
        or receipt.get("scientific_claim") != "UNCHANGED_NOT_EVALUATED_BY_THIS_GATE"
        or not isinstance(receipt.get("reasons"), list)
        or not isinstance(receipt.get("changes"), list)
    ):
        raise ValueError("not_a_supported_offline_intake_receipt")


def render_workbench(demo: dict, local: dict, domain: dict, hashes: dict) -> str:
    """Render measured receipt values; synthetic readiness never enables actions."""
    if set(hashes) != set(INPUTS):
        raise ValueError("unexpected_receipt_download_target")
    require_offline(local)
    if local["status"] != "BLOCKED" or local["reasons"] != [
        "VERIFIED_SOURCE_UNAVAILABLE"
    ]:
        raise ValueError("local_source_gate_requires_a_new_reviewed_renderer")
    if (
        demo.get("provider") != "NOT_RUN"
        or demo.get("sandbox") != "NOT_RUN"
        or demo.get("patch_applied_or_executed") is not False
        or demo.get("usage") != "unknown"
        or len(demo.get("cases", [])) != 6
    ):
        raise ValueError("not_a_supported_synthetic_demo")
    cases = demo["cases"]
    if [case.get("case") for case in cases] != list(LABELS) or [
        case.get("result", {}).get("status") for case in cases
    ] != demo.get("expected_statuses"):
        raise ValueError("case_identity_or_status_mismatch")
    for case in cases:
        if case.get("contract_and_operator_gates") != (
            "LABELED_SYNTHETIC_FIXTURES_NOT_REAL_ENTITLEMENTS"
        ):
            raise ValueError("synthetic_entitlement_label_missing")
        require_offline(case["result"])
    maya_cases = [
        case for case in domain.get("cases", []) if case.get("case") == "maya"
    ]
    if len(maya_cases) != 1:
        raise ValueError("maya_receipt_missing_or_duplicated")
    maya = maya_cases[0]
    if (
        maya.get("data_origin") != "bundled_synthetic_fixture"
        or maya.get("verdict") != "BLOCK"
        or maya.get("code_repair") != "NOT_RUN"
        or maya.get("physical_interpretation") != "NOT_ESTABLISHED"
    ):
        raise ValueError("scientific_context_requires_a_new_reviewed_renderer")

    summaries = []
    details = []
    for number, case in enumerate(cases, start=1):
        name, receipt = case["case"], case["result"]
        label, status = LABELS[name], receipt["status"]
        tone = "ready" if status == "READY_FOR_ISOLATED_TEST" else status.lower()
        status_label = (
            "Eligible for isolated test only"
            if status == "READY_FOR_ISOLATED_TEST"
            else status.title()
        )
        summaries.append(
            f'<li><a href="#case-{number}"><span class="number">0{number}</span>'
            f"{text(label)} <span class='badge {tone}'>{text(status_label)}</span></a></li>"
        )
        reasons = "".join(
            f"<li><code>{text(reason)}</code></li>" for reason in receipt["reasons"]
        )
        if not reasons:
            reasons = "<li>Intake checks matched this synthetic fixture. Tests were not run.</li>"
        changes = []
        for change in receipt["changes"]:
            changes.append(
                f"<h4>{text(change['path'])} · untrusted candidate text</h4>"
                f"<pre class='diff'>{text(change['diff'])}</pre>"
                "<dl class='hashes'><dt>Before SHA-256</dt>"
                f"<dd>{text(change['before_sha256'])}</dd><dt>After SHA-256</dt>"
                f"<dd>{text(change['after_sha256'])}</dd></dl>"
            )
        preview = "".join(changes) or (
            "<p class='muted'>No valid diff released by the intake gate. "
            "The rejected proposal is not applied or executed.</p>"
        )
        details.append(
            f'<details id="case-{number}" {"open" if number == 1 else ""}>'
            f"<summary><span class='number'>0{number}</span>{text(label)}"
            f"<span class='badge {tone}'>{text(status_label)}</span></summary>"
            "<div class='case-body'><p class='fixture'>SYNTHETIC CONTRACT + GATES · NOT REAL ACCESS</p>"
            f"<ul class='reasons'>{reasons}</ul>{preview}"
            "<dl class='hashes'><dt>Proposal SHA-256</dt>"
            f"<dd>{text(receipt['proposal_sha256'])}</dd><dt>Source snapshot SHA-256</dt>"
            f"<dd>{text(receipt.get('snapshot_sha256', 'unknown'))}</dd>"
            f"<dt>Policy SHA-256</dt><dd>{text(receipt.get('policy_sha256', 'unknown'))}</dd></dl>"
            "<p class='boundary'>Execution: NOT_RUN · source written: false · scientific claim: unchanged</p>"
            "</div></details>"
        )
    provenance = "".join(
        f"<tr><td><a href='{text(name)}' download>{text(name)}</a></td><td><code>{text(sha)}</code></td></tr>"
        for name, sha in sorted(hashes.items())
    )
    return (
        "<!doctype html><html lang='en'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        "<meta http-equiv='Content-Security-Policy' content=\"default-src 'none'; "
        "style-src 'unsafe-inline'; script-src 'none'; connect-src 'none'; img-src 'none'; "
        "frame-src 'none'; object-src 'none'; base-uri 'none'; form-action 'none'\">"
        "<meta name='referrer' content='no-referrer'>"
        "<title>LabRepair · Candidate review</title><style>"
        "*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:#f3f5f5;"
        "color:#182b32;font:16px/1.55 system-ui,sans-serif}a{color:#125e65}"
        "a:focus-visible,summary:focus-visible{outline:3px solid #0d858a;outline-offset:4px}"
        "header{background:#182b32;color:#eaf3f3;padding:17px 4vw;display:flex;justify-content:space-between;gap:20px}"
        ".brand{font-weight:700;letter-spacing:.08em}.topnote{font-size:13px;color:#c8d6d8}"
        "main{max-width:1180px;margin:auto;padding:32px 24px}h1{font-size:36px;line-height:1.15;margin:4px 0 14px}"
        "h2{font-size:22px;margin:0 0 12px}h3{font-size:16px;margin:0 0 10px}h4{margin:20px 0 8px}"
        ".eyebrow,.fixture{font-size:11px;font-weight:700;letter-spacing:.12em}.eyebrow{color:#477178}"
        ".intro{max-width:710px;color:#4b626a;margin:0 0 24px}.banner{border-left:5px solid #b16616;"
        "padding:17px 20px;background:#fff4e2;margin-bottom:22px}.banner strong{font-size:20px}"
        ".banner p{margin:5px 0}.badge{display:inline-block;font-size:11px;line-height:1.3;font-weight:700;"
        "padding:5px 9px;letter-spacing:.025em;background:#e7edf0;color:#425660}"
        ".badge.blocked{background:#ffe8bc;color:#7c480d}.badge.rejected{background:#f6dfe0;color:#872f3d}"
        ".badge.ready{background:#deedf1;color:#225966}.metrics{display:grid;grid-template-columns:repeat(4,1fr);"
        "gap:1px;background:#d5e0e3;border:1px solid #d5e0e3;margin-bottom:24px}"
        ".metrics div{background:white;padding:16px}.metrics span{display:block;font-size:12px;color:#5f737b}"
        ".metrics b{font:600 16px/1.5 ui-monospace,monospace}.columns{display:grid;grid-template-columns:1fr 310px;gap:24px}"
        ".panel{background:#fff;border:1px solid #d8e2e5;padding:23px}.muted{color:#566b74;font-size:14px}"
        ".case-list{list-style:none;padding:0;margin:0 0 20px}.case-list a{display:flex;align-items:center;gap:12px;"
        "padding:12px 0;text-decoration:none;border-bottom:1px solid #e6edef;font-size:14px}"
        ".case-list .badge{margin-left:auto;text-align:right}.number{font:12px ui-monospace,monospace;color:#719099}"
        "details{border:1px solid #d8e2e5;background:white;margin-bottom:12px;scroll-margin-top:20px}"
        "summary{cursor:pointer;padding:16px;font-weight:600;display:flex;gap:12px;align-items:center}"
        "summary .badge{margin-left:auto;max-width:190px}summary:before{content:'+';color:#4e737a}"
        "details[open] summary:before{content:'−'}details[open] summary{border-bottom:1px solid #d8e2e5}"
        ".case-body{padding:18px}.fixture{color:#607680;margin:0 0 12px}.reasons{padding-left:21px;font-size:14px}"
        ".diff{background:#162a32;color:#e1eded;padding:18px;font:13px/1.7 ui-monospace,monospace;overflow:auto;"
        "white-space:pre;max-width:100%}.hashes{font-size:11px;margin:14px 0}.hashes dt{font-weight:700;color:#536e76}"
        ".hashes dd{margin:3px 0 10px;font-family:ui-monospace,monospace;overflow-wrap:anywhere}"
        ".boundary{font-size:12px;border-top:1px solid #e4ecef;padding-top:12px;color:#506971}"
        ".aside-number{display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid #e7edef}"
        ".aside-number b{font-family:ui-monospace,monospace}.small{font-size:12px;color:#60727b}"
        "aside section+section{margin-top:18px}aside code{overflow-wrap:anywhere;font-size:12px}"
        ".provenance{margin-top:24px}.provenance table{width:100%;border-collapse:collapse;font-size:12px}"
        "td,th{text-align:left;vertical-align:top;padding:10px;border-bottom:1px solid #dce5e8}"
        "td code{overflow-wrap:anywhere}footer{margin:24px 0 0;color:#60727b;font-size:12px}"
        "@media(max-width:800px){.columns{grid-template-columns:1fr}.metrics{grid-template-columns:repeat(2,1fr)}"
        "main{padding:24px 15px}h1{font-size:30px}header{flex-wrap:wrap}.provenance table{table-layout:fixed}"
        "summary{font-size:13px}.case-list a{flex-wrap:wrap}.case-list .badge{margin-left:0}}"
        "</style></head><body><header><div class='brand'>LABREPAIR / REVIEW</div>"
        "<div class='topnote'>OFFLINE EVIDENCE · READ-ONLY · NO MODEL OR CODE EXECUTION</div></header><main>"
        "<div class='eyebrow'>NEBIUS-005 · REVIEW WORKBENCH</div><h1>Inspect the repair. Keep the boundary.</h1>"
        "<p class='intro'>A candidate diff is a proposal, not a result. Inspect its source binding, "
        "protected files and refusal reasons before any isolated test.</p>"
        "<section class='banner' aria-label='Actual local source gate'><strong>Actual local gate: BLOCKED</strong>"
        "<p><code>VERIFIED_SOURCE_UNAVAILABLE</code> — shared Q4 source has not been imported.</p>"
        "<p class='small'>This is the saved NEBIUS-004 CLI receipt, not a fresh cloud check. "
        "No Run, Approve or Apply action is available in this workbench.</p></section>"
        "<div class='metrics'><div><span>NVIDIA / Nebius inference</span><b>NOT_RUN</b></div>"
        "<div><span>Isolated execution</span><b>NOT_RUN</b></div><div><span>Provider usage</span><b>unknown</b></div>"
        "<div><span>Candidate source applied</span><b>false</b></div></div><div class='columns'><div>"
        "<section class='panel'><h2>Six intake scenarios</h2><p class='muted'>Synthetic arithmetic fixture. "
        "The ready case uses fixture gates, not real Nebius entitlement. None of these cases repairs the Bell/CHSH program.</p>"
        f"<ul class='case-list'>{''.join(summaries)}</ul></section><div style='height:18px'></div>"
        f"{''.join(details)}</div><aside><section class='panel'><h3>Scientific replay · separate record</h3>"
        "<p class='small'>Existing public synthetic Maya case. These are saved LAB-001 replay values, "
        "not a new execution or the arithmetic repair fixture.</p>"
        f"<div class='aside-number'><span>Submitted S</span><b>{text(maya['claimed_s'])}</b></div>"
        f"<div class='aside-number'><span>Registered replay S</span><b>{text(maya['replayed_s'])}</b></div>"
        f"<p><span class='badge blocked'>Original claim: {text(maya['verdict'])}</span></p>"
        f"<p class='small'>Claim state: {text(maya['claim_state'])}<br>Physical interpretation: "
        f"{text(maya['physical_interpretation'])}</p><p class='small'>Even a tested code repair cannot "
        "silently authorize the original scientific claim.</p></section>"
        "<section class='panel'><h3>Operator handover</h3><ol class='small'><li>Obtain and verify actual shared source bytes.</li>"
        "<li>Load the original three-file contract and protected policy.</li><li>Verify NVIDIA model, isolated backend "
        "and a spending cap before a real run.</li></ol><p class='small'>Candidate text is untrusted data. "
        "This static view cannot grant access or execute it.</p></section></aside></div>"
        "<section class='panel provenance'><h2>Replayable handover</h2>"
        f"<p class='small'>Input receipt run: {text(demo['run_id'])}. View increment: {RUN_ID}. "
        "Download links serve only the three unchanged public-safe JSON receipts below.</p>"
        "<table><thead><tr><th>Saved receipt</th><th>SHA-256 of exact downloaded bytes</th></tr></thead>"
        f"<tbody>{provenance}</tbody></table></section><footer>MIT-licensed public source retained unchanged. "
        "No private research data, cloud account IDs, credentials, approval writes or external page assets.</footer>"
        "</main></body></html>"
    )


def main() -> int:
    data = {}
    hashes = {}
    for target, source in INPUTS.items():
        path = (ROOT / "evidence" / source).resolve()
        if not path.is_relative_to((ROOT / "evidence").resolve()):
            raise ValueError("receipt_path_outside_evidence")
        with path.open("rb") as stream:
            raw = stream.read(524289)
        if len(raw) > 524288:
            raise ValueError("receipt_too_large")
        data[target] = raw
        hashes[target] = hashlib.sha256(raw).hexdigest()
    page = render_workbench(
        json.loads(data["intake-receipt.json"]),
        json.loads(data["local-gate-receipt.json"]),
        json.loads(data["domain-replay-receipt.json"]),
        hashes,
    ).encode("utf-8")
    output = ROOT / "workbench"
    if output.is_symlink() or not output.resolve().is_relative_to(ROOT.resolve()):
        raise ValueError("output_directory_outside_workspace")
    if output.exists() and any(
        item.name not in {*INPUTS, "index.html"} for item in output.iterdir()
    ):
        raise ValueError("unexpected_file_in_static_output")
    output.mkdir(exist_ok=True)
    for name, raw in data.items():
        if (output / name).is_symlink():
            raise ValueError("symlink_output_forbidden")
        (output / name).write_bytes(raw)
    if (output / "index.html").is_symlink():
        raise ValueError("symlink_output_forbidden")
    (output / "index.html").write_bytes(page)
    receipt = {
        "run_id": RUN_ID,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "command": ".venv/Scripts/python.exe -m labrepair.workbench",
        "output": "workbench/index.html",
        "html_sha256": hashlib.sha256(page).hexdigest(),
        "html_bytes": len(page),
        "input_sha256": hashes,
        "input_runs": ["LAB-001", "NEBIUS-004"],
        "input_receipts_rerun": False,
        "page_mode": "STATIC_READ_ONLY_NO_SCRIPT_NO_EXTERNAL_ASSETS",
        "receipt_readback": all(
            (output / name).read_bytes() == raw for name, raw in data.items()
        ),
        "provider": "NOT_RUN",
        "candidate_execution": "NOT_RUN",
        "sandbox": "NOT_RUN",
        "provider_usage": "unknown",
    }
    (ROOT / "evidence" / "nebius_005_workbench.json").write_text(
        json.dumps(receipt, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(receipt))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
