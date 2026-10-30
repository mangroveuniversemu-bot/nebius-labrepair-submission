"""Read-only capability check; never prints keys or performs network requests."""

import json
import os
import platform
import shutil
from datetime import datetime, timezone
from importlib import metadata

from labrepair.paths import ROOT, SOURCE


def inspect_environment() -> dict:
    try:
        pydantic_version = metadata.version("pydantic")
    except metadata.PackageNotFoundError:
        pydantic_version = None
    configured = json.loads(
        (ROOT / "config" / "providers.json").read_text(encoding="utf-8")
    )
    return {
        "run_utc": datetime.now(timezone.utc).isoformat(),
        "python_version": platform.python_version(),
        "pydantic_version": pydantic_version,
        "vendored_source_present": (SOURCE / "pyproject.toml").is_file(),
        "nebius_key_present": bool(os.environ.get("NEBIUS_API_KEY")),
        "live_configuration_enabled": configured["live_enabled"],
        "openshell_command_present": shutil.which("openshell") is not None,
        "docker_command_present": shutil.which("docker") is not None,
        "docker_daemon": "NOT_CHECKED",
        "nebius_credits": "UNVERIFIED",
        "model_authorization": "UNVERIFIED",
        "sandbox_beta_access": "UNVERIFIED",
        "network_requests": 0,
        "credentials_read_from_files": False,
        "aws_operations": 0,
    }


def main() -> int:
    report = inspect_environment()
    destination = ROOT / "evidence" / "environment.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report))
    return 0 if report["pydantic_version"] and report["vendored_source_present"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
