"""Replay a saved response as data; makes no provider call or code execution."""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from labrepair.model_parameters import review_chat_response
from labrepair.scientific_workflow import ScienceReviewError


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("response", type=Path)
    args = parser.parse_args()
    try:
        with args.response.open("rb") as stream:
            raw = stream.read(65537)
        report = review_chat_response(raw)
    except (OSError, ScienceReviewError) as exc:
        print(json.dumps({"status": "REJECTED", "reason": str(exc) if isinstance(exc, ScienceReviewError) else "RESPONSE_UNAVAILABLE", "network_requests": 0}))
        return 2
    print(json.dumps(report, indent=2))
    return 0 if report["local_review"]["local_result"] == "LOCAL_SEMANTIC_MATCH" else 2


if __name__ == "__main__":
    raise SystemExit(main())
