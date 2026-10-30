# Daily request limits and Nebius overage / 30 October 2026

Every direct LabRepair call must reserve one slot in a shared SQLite ledger before
HTTP dispatch. Defaults and maximum permitted configuration: **five attempts and
USD 0.05 reserved per Taipei calendar day**, at least **USD 0.01 per attempt**.
Requests over the limit are refused before transport. This envelope deliberately
reserves much more than this tiny fixed request's estimated token cost.

```sh
python scripts/run_live_repair.py --budget-status
python scripts/run_live_repair.py --disable-live
```

The fourth slot raises a near-limit warning; the fifth exhausts the allowance.
An HTTP error, timeout or unknown result keeps its reservation. Duplicate run IDs
never grant another request. Database transactions serialize concurrent workers.
Corrupt, deleted or mismatched state fails closed instead of resetting to zero.
Read-only status never grants dispatch or initializes missing state.

Use ONE installation-wide path for every checkout/process, configured through
`LABREPAIR_BUDGET_STATE`. The default is `.live-runs/budget.sqlite`; the existing
DOT work uses `/workspace/.labrepair-setup/central-budget/budget.sqlite3` outside
source checkouts. Keep its companion state marker and initialization state with
it. Do not delete state on deployment. Cross-environment rebuild durability still
requires a persistent volume; it has not been demonstrated merely by choosing a
path. Deleting the ledger and its marker, changing deployments or using the key
outside LabRepair can bypass any application-only counter.

The `DISABLED` file beside the shared ledger blocks all live calls. It is a manual
emergency stop with no automatic resume. An operator can inspect the ledger,
account usage and billing, then remove that file explicitly to resume. No key is
required for status or stop. Keys, local run outputs and budget state stay ignored
by Git; they are never included in source/review archives.

## Provider billing is a separate boundary

[Current Token Factory billing](https://docs.tokenfactory.nebius.com/other-capabilities/billing-new)
allows negative account balance and automatic bank-card collection at a billing
threshold or the start of the month. Promotional credits cannot pay outstanding
invoices. A USD 25 balance, RPM/TPM setting or disabled legacy auto-top-up is not
proof of an account-wide hard stop. The current documentation does not establish
a project/key monetary hard cap or a way to disable all card collection.

The authenticated account UI showed USD 25 available on 30 October. The existing
bank-card method remains configured; no top-up, payment, card or plan change is
part of this work. Published Nano pricing is USD 0.06 per million input tokens
and USD 0.24 per million output tokens; its source is saved in the billing audit.
The unchanged fixed request previously used 121 input / 38 output tokens, with
64 total completion tokens requested. Estimates are not invoice receipts or an
enforced global monetary cap. Actual billed money remains unknown until observed.

For this fixed input/model, verify current rates and credit headroom before a real
call, use only one attempt, and retain its usage/transport record. Keep prepaid
headroom for other workloads. If account usage, prices, access or balance cannot
be verified, stop new live calls and inspect them rather than enabling paid
fallbacks. Recheck provider consumption after the test; UI balance rounding or
delayed usage must be recorded honestly, not interpreted as zero cost.

These limits apply to direct inference through LabRepair. A new Sandbox spawn,
dedicated endpoint, training job, other app or direct use of the same key has its
own costs and is not covered by this ledger. No such resource is started here.

The first real direct-CLI run on 30 October observed HTTP 200 and a verified
repair, with a 1/5 shared reservation count and USD 0.01/0.05 reserved. Its exact
budget status is saved separately from the live ledger; checking out the repo
does not restore or reset that production ledger. The actual call used the
existing key, made no retry and did not start another resource.
