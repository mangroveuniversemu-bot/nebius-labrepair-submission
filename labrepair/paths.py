"""Resolve only the reviewed, bundled source snapshot."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "vendor" / "evidencepilot"


def enable_reviewed_source() -> Path:
    if not (SOURCE / "AGENTS.md").is_file() or not (SOURCE / "LICENSE").is_file():
        raise RuntimeError("reviewed_source_snapshot_missing")
    source_text = str(SOURCE)
    if source_text not in sys.path:
        sys.path.insert(0, source_text)
    return SOURCE
