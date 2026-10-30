"""Export the fixed, zero-key judge site using Python's standard library only.

Run from any directory. Reads the existing reviewed repository without changing
it. No provider calls, subprocesses, package installation or credentials.
"""
import base64
import hashlib
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
sys.path.insert(0, str(REPO))
from labrepair.scientific_workflow import (  # noqa: E402
    POLICY, SOURCE_PINS, load_fixture, run_scenario,
)
from labrepair.recorded_validation import load_recorded_validation  # noqa: E402


def encode(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def csp_hash(text):
    return "'sha256-" + base64.b64encode(hashlib.sha256(text.encode()).digest()).decode() + "'"


def standalone_html(dest):
    """Bundle local modules without a build dependency or file:// requests."""
    parts = []
    for name in ("integrity.js", "data.js", "engine.js", "app.js"):
        code = (dest / name).read_text(encoding="utf-8")
        code = re.sub(r"^import .*?;\s*$", "", code, flags=re.MULTILINE)
        code = re.sub(r"\bexport\s+(?=(?:async\s+)?(?:const|function))", "", code)
        parts.append(code)
    script = '\ndocument.addEventListener("DOMContentLoaded", () => {\n' + "\n".join(parts) + "\n});\n"
    script = re.sub(r"</script", r"<\\/script", script, flags=re.IGNORECASE)
    style = "\n" + (dest / "style.css").read_text(encoding="utf-8") + "\n"
    html = (HERE / "src/index.html").read_text(encoding="utf-8")
    html = html.replace('<link rel="stylesheet" href="./style.css">', "<style>" + style + "</style>")
    html = html.replace('<script type="module" src="./app.js"></script>', "<script>" + script + "</script>")
    policy = ("default-src 'none'; script-src " + csp_hash(script) + "; style-src " + csp_hash(style)
              + "; connect-src 'none'; object-src 'none'; base-uri 'none'; form-action 'none'")
    html = re.sub(r'<meta http-equiv="Content-Security-Policy" content="[^"]*">',
                  '<meta http-equiv="Content-Security-Policy" content="' + policy + '">', html)
    (dest / "index.html").write_text(html, encoding="utf-8", newline="\n")


def build():
    files, counts, contract = load_fixture()
    cases = ["channel-fix", "same-total", "missing-pair"]
    references = {case: run_scenario(case) for case in cases}
    source = {
        "schema": "LABREPAIR_FIXED_BROWSER_SOURCE_V1",
        "counts": counts,
        "policy": POLICY,
        "policy_sha256": contract.policy_sha256,
        "snapshot_sha256": contract.snapshot_sha256,
        "files": {name: raw.decode("utf-8") for name, raw in files.items()},
        "reference_receipts": {case: references[case]["receipt_sha256"] for case in cases},
    }
    recorded = load_recorded_validation()  # Revalidates archived receipt pins.
    source_text, recorded_text = encode(source), encode(recorded)
    pins = {
        "source_sha256": sha(source_text),
        "recorded_sha256": sha(recorded_text),
        "snapshot_sha256": contract.snapshot_sha256,
        "policy_sha256": contract.policy_sha256,
        "source_files": SOURCE_PINS,
    }
    dest = HERE / "dist"
    dest.mkdir(exist_ok=True)
    for name in ("index.html", "style.css", "engine.js", "app.js"):
        (dest / name).write_text((HERE / "src" / name).read_text(encoding="utf-8"),
                                 encoding="utf-8", newline="\n")
    (dest / "integrity.js").write_text(
        "// Build-time pins from independently verified source and saved receipts.\n"
        "export const PINS = Object.freeze(" + encode(pins) + ");\n", encoding="utf-8", newline="\n"
    )
    (dest / "data.js").write_text(
        "// Safe, fixed synthetic inputs and sanitized saved execution summary.\n"
        "export const sourceText = " + json.dumps(source_text) + ";\n"
        "export const recordedText = " + json.dumps(recorded_text) + ";\n", encoding="utf-8", newline="\n"
    )
    # A semantic parity oracle for offline tests, not a browser result table.
    (HERE / "tests" / "python-reference.json").write_text(
        encode(references) + "\n", encoding="utf-8", newline="\n"
    )
    standalone_html(dest)
    summary = {
        "schema": "LABREPAIR_STATIC_BUILD_V1", "pins": pins,
        "files": {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                  for p in sorted(dest.iterdir()) if p.is_file()},
        "mode": "BROWSER_FIXED_CASE_RECOMPUTATION_AND_SAVED_CLOUD_PLAYBACK",
        "provider_calls": 0, "candidate_execution": False,
        "public_deployment": "NOT_PERFORMED",
    }
    (HERE / "build-result.json").write_text(encode(summary) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"output": str(dest), "source_sha256": pins["source_sha256"],
                      "files": len(summary["files"]), "provider_calls": 0}))


if __name__ == "__main__":
    build()
