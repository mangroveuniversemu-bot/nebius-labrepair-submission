"""Package an exact committed source tree and an existing verified review movie.

Uses local Git/Python only. Does not deploy a website or call any provider.
"""
import argparse
import hashlib
import json
import subprocess
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
MOVIE = "LabRepair_DEMO_Release_20261030.mp4"
SUBTITLE = "LabRepair_DEMO_Release_20261030.en.srt"
EXPECTED_MOVIE = "d7603453833c30b8a44c64d02cdbd855237a6e9a96c2f746491c91ad574b98a7"
MEDIA = {
    "release": (MOVIE, SUBTITLE, EXPECTED_MOVIE, "demo-20261030-release"),
    "live-review": ("LabRepair_DEMO_LiveReview_20261030.mp4",
                    "LabRepair_DEMO_LiveReview_20261030.en.srt",
                    "9ab36becebe9b4061e9ecc62e607cff88f0b84bc6c9065079d3df4ced56e531a",
                    "demo-20261030-live-review"),
}


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def make_zip(path, entries):
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, raw in sorted(entries.items()):
            info = zipfile.ZipInfo(name, (2026, 10, 30, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, raw)
    with zipfile.ZipFile(path) as archive:
        if archive.testzip() is not None:
            raise ValueError("ZIP_CRC_FAILURE")
        if set(archive.namelist()) != set(entries):
            raise ValueError("ZIP_ENTRY_MISMATCH")
        for name, raw in entries.items():
            if digest(archive.read(name)) != digest(raw):
                raise ValueError("ZIP_PAYLOAD_MISMATCH: " + name)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--media-dir", required=True, type=Path)
    parser.add_argument("--media-version", choices=MEDIA, default="release")
    args = parser.parse_args()
    commit = subprocess.check_output(
        ["git", "rev-parse", "--verify", args.commit + "^{commit}"], cwd=REPO, text=True
    ).strip()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    movie_name, subtitle_name, expected_movie, media_folder = MEDIA[args.media_version]
    movie = (args.media_dir / movie_name).read_bytes()
    if digest(movie) != expected_movie:
        raise ValueError("UNREVIEWED_MOVIE_BYTES")
    source_name = "LabRepair_Source_20261030.zip"
    subprocess.run(["git", "archive", "--format=zip", "--prefix=LabRepair/",
                    "--output=" + str(output / source_name), commit], cwd=REPO, check=True)
    with zipfile.ZipFile(output / source_name) as archive:
        if archive.testzip() is not None:
            raise ValueError("SOURCE_ZIP_CRC_FAILURE")
        source = {n.removeprefix("LabRepair/"): archive.read(n)
                  for n in archive.namelist() if not n.endswith("/")}
    instructions = f"""LabRepair private release review / 30 October 2026
Source commit: {commit}

Extract LabRepair_Interactive_TestBuild_20261030.zip and open index.html in a
current browser. No account, API key, installation or cloud job is required.
Try the wrong-pair repair, then the declared repair and missing-pair case.
Direct-file browser layout/download QA remains NOT_RUN by the automation tool;
the engine passed 12 offline checks. Unsupported browser cryptography fails
closed. For the verified Python workbench, extract the source archive and run:
    python -m labrepair.serve --port 8770
Then open http://127.0.0.1:8770/ . Python 3.12 standard library only.

The movie is 123 seconds with natural local English male narration. Its cloud
records are saved historical executions. This delivery makes no provider call.
The example is synthetic; original claim 3.40 remains NOT_REPRODUCED.

The source archive is a full committed application snapshot, with licenses and
evidence. Film edit sources depend on the prior raw-production Drive package,
local Kokoro model cache and Windows fonts documented in source_reference.json;
this bundle is a review package, not a self-contained film-render environment.

This repository and Release remain PRIVATE. GitHub login and repository read
access are required. A downloaded test build is not a hosted public demo or a
completed Devpost submission. SHA256SUMS.txt verifies delivery bytes, not provider
signatures. See docs/GITHUB_DEPLOYMENT_20261030.md for verification scope.
""".encode()
    (output / "START_HERE.txt").write_bytes(instructions)
    test_name = "LabRepair_Interactive_TestBuild_20261030.zip"
    test_entries = {
        "index.html": source["judge-site/dist/index.html"],
        "START_HERE.txt": instructions,
        "LICENSE": source["LICENSE"],
        "BUILD_DETAILS.md": source["judge-site/README.md"],
        "build-result.json": source["judge-site/build-result.json"],
    }
    test_entries["SHA256SUMS.json"] = (json.dumps(
        {n: digest(v) for n, v in sorted(test_entries.items())}, indent=2) + "\n").encode()
    make_zip(output / test_name, test_entries)
    (output / movie_name).write_bytes(movie)
    (output / subtitle_name).write_bytes(source["media/" + media_folder + "/" + subtitle_name])
    bundle_name = ("LabRepair_LiveMode_Review_Bundle_20261030.zip" if args.media_version == "live-review"
                   else "LabRepair_GitHub_Review_Bundle_20261030.zip")
    bundle_entries = {n: (output / n).read_bytes()
                      for n in (source_name, test_name, movie_name, subtitle_name, "START_HERE.txt")}
    bundle_entries["LICENSE"] = source["LICENSE"]
    bundle_entries["DEPLOYMENT.md"] = source["docs/GITHUB_DEPLOYMENT_20261030.md"]
    if "docs/LIVE_MODE_20261030.md" in source:
        bundle_entries["LIVE_MODE.md"] = source["docs/LIVE_MODE_20261030.md"]
    make_zip(output / bundle_name, bundle_entries)
    names = (source_name, test_name, movie_name, subtitle_name, "START_HERE.txt", bundle_name)
    files = {n: {"bytes": (output / n).stat().st_size,
                 "sha256": digest((output / n).read_bytes())} for n in names}
    (output / "SHA256SUMS.txt").write_text(
        "".join(f"{v['sha256']}  {n}\n" for n, v in sorted(files.items())),
        encoding="utf-8", newline="\n")
    receipt = {"schema": "LABREPAIR_GITHUB_RELEASE_PACKAGE_V1", "commit": commit,
               "files": files, "zip_crc_and_payloads": "PASS", "provider_calls": 0,
               "cloud_resources_created": False, "hosted_site": "NOT_DEPLOYED"}
    (output / "package_verification.json").write_text(
        json.dumps(receipt, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
