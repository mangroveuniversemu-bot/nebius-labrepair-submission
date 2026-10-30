"""Prepare the existing zero-key browser demo for branch-based GitHub Pages.

Only copies the six reviewed static files. No network, credentials, dependencies,
provider dispatch, candidate execution or GitHub configuration is performed.
"""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
NAMES = ("app.js", "data.js", "engine.js", "index.html", "integrity.js", "style.css")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    if output == REPO or REPO in output.parents:
        parser.error("Output must be outside the source checkout")
    output.mkdir(parents=True, exist_ok=True)
    existing = {p.name for p in output.iterdir() if p.name != ".git"}
    allowed = set(NAMES) | {".nojekyll", "deployment.json"}
    if existing - allowed:
        parser.error("Refusing output directory containing unrelated files")
    build = json.loads((REPO / "judge-site/build-result.json").read_text())
    source_commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=REPO, text=True
    ).strip()
    files = {}
    for name in NAMES:
        raw = (REPO / "judge-site/dist" / name).read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        if digest != build["files"][name]:
            raise ValueError("UNVERIFIED_STATIC_FILE: " + name)
        (output / name).write_bytes(raw)
        files[name] = {"bytes": len(raw), "sha256": digest}
    (output / ".nojekyll").write_bytes(b"")
    manifest = {
        "schema": "LABREPAIR_PAGES_PACKAGE_V1",
        "source_commit": source_commit,
        "files": files,
        "source_pins": build["pins"],
        "mode": "FIXED_BROWSER_RECOMPUTATION_AND_HISTORICAL_CLOUD_EVIDENCE",
        "provider_calls": 0,
        "candidate_execution": False,
        "browser_credentials": False,
    }
    (output / "deployment.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    print(json.dumps({"source_commit": source_commit, "files": len(files),
                      "verified_hashes": len(files), "provider_calls": 0}))


if __name__ == "__main__":
    main()
