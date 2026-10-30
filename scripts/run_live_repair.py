"""Preview by default; explicitly opt in to ONE bounded Token Factory request."""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from labrepair.live_repair import LiveRepairError, budget_path, live_status, preview, run_live
from labrepair.daily_budget import DailyBudgetError


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--confirm-provider-billing", action="store_true",
                        help="Operator confirms their account/credits/billing controls; not an enforced cap")
    parser.add_argument("--run-id", default="manual-repair-1")
    parser.add_argument("--budget-status", action="store_true")
    parser.add_argument("--disable-live", action="store_true")
    args = parser.parse_args()
    if sum([args.live, args.budget_status, args.disable_live]) > 1:
        parser.error("choose only one operation")
    try:
        if args.budget_status:
            print(json.dumps(live_status(), indent=2))
            return 0
        if args.disable_live:
            path = budget_path().parent
            if any(p.is_symlink() for p in (path, *path.parents)):
                raise LiveRepairError("SYMLINK_STATE_FORBIDDEN")
            path.mkdir(parents=True, exist_ok=True)
            (path / "DISABLED").touch(exist_ok=True)
            print(json.dumps({"status": "LIVE_DISABLED", "network_requests": 0}))
            return 0
        result = (run_live(confirm_provider_billing=args.confirm_provider_billing,
                           run_id=args.run_id) if args.live else preview())
    except (LiveRepairError, DailyBudgetError) as exc:
        print(json.dumps({"status": "BLOCKED", "reason": str(exc), "network_requests": 0}))
        return 2
    except OSError:
        # Persistence may fail AFTER an HTTP request. Never report zero calls.
        print(json.dumps({"status": "LOCAL_IO_FAILURE", "network_requests": "unknown",
                          "request_may_have_been_sent": True, "retry": "FORBIDDEN_CHECK_LEDGER_AND_RECEIPTS"}))
        return 2
    print(json.dumps(result, indent=2))
    return 0 if result.get("mode") == "PREVIEW" or result["status"] == "MODEL_REPAIR_VERIFIED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
