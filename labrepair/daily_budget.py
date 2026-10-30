"""Persistent local request reservations; never a provider/account billing cap.

The default and maximum envelope is five reservations / USD 0.05 per Taipei
calendar day. Every slot reserves at least USD 0.01. This is an application
envelope, NOT a model-price estimate: the caller must verify current pricing and
that its bounded request fits before dispatch. Actual billed money is unknown.

Use one fixed shared ledger across processes. No refund/reset API is provided:
timeouts, errors and unknown outcomes keep their reservation. A duplicate run ID
never grants another dispatch. A companion state marker detects accidental
database deletion/replacement; partial initialization fails closed. A user able
to delete the entire ledger AND its marker can bypass any local-only control.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import time
import uuid
from decimal import Decimal, DecimalException

DEFAULT_STATE_PATH = Path(__file__).resolve().parents[1] / ".live-runs" / "budget.sqlite"
TAIPEI = dt.timezone(dt.timedelta(hours=8), "Asia/Taipei")
SCHEMA_VERSION = 1
APPLICATION_ID = 0x4C524231
MAX_CALLS = 5
MAX_MICRO_USD = 50_000
MIN_RESERVATION_MICRO_USD = 10_000
RUN_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}\Z")


class DailyBudgetError(RuntimeError):
    """Fixed, non-sensitive error code; callers must not dispatch on failure."""

    def __init__(self, code):
        self.code = code
        super().__init__(code)


class DailyLimitExceeded(DailyBudgetError):
    """No new request slot was granted."""


def taipei_day(moment=None):
    moment = moment or dt.datetime.now(dt.timezone.utc)
    if moment.tzinfo is None:
        raise DailyBudgetError("AWARE_CLOCK_REQUIRED")
    return moment.astimezone(TAIPEI).date().isoformat()


def _micros(value):
    if not isinstance(value, (str, Decimal)):
        raise DailyBudgetError("INVALID_BUDGET_CONFIG")
    try:
        amount = Decimal(value)
        scaled = amount * 1_000_000
        if not amount.is_finite() or amount <= 0 or scaled != scaled.to_integral_value():
            raise ValueError
        return int(scaled)
    except (DecimalException, ValueError, OverflowError):
        raise DailyBudgetError("INVALID_BUDGET_CONFIG") from None


def _usd(micro_usd):
    return format(Decimal(micro_usd) / 1_000_000, ".6f")


def _marker(path):
    return path.with_name(path.name + ".state.json")


def _reject_symlinks(path):
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise DailyBudgetError("BUDGET_SYMLINK_FORBIDDEN")


def _connect(path, read_only=False):
    # mode=rw forbids silent recreation if the database disappears after init.
    connection = sqlite3.connect(path.as_uri() + ("?mode=ro" if read_only else "?mode=rw"), uri=True,
                                 timeout=5, isolation_level=None)
    try:
        connection.execute("PRAGMA busy_timeout=5000")
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA trusted_schema=OFF")
    except sqlite3.Error:
        connection.close()
        raise
    return connection


def _initialize(path):
    marker = _marker(path)
    lock = path.with_name(path.name + ".initializing")
    _reject_symlinks(path)
    _reject_symlinks(marker)
    _reject_symlinks(lock)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and marker.exists():
        return
    if marker.exists() and not path.exists():
        raise DailyBudgetError("BUDGET_STATE_MISSING")
    if path.exists() and not marker.exists() and not lock.exists():
        raise DailyBudgetError("BUDGET_STATE_ANCHOR_MISSING")
    try:
        lock.mkdir()
    except FileExistsError:
        # Local initialization coordination only; never a provider retry.
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            if path.exists() and marker.exists():
                return
            time.sleep(0.01)
        raise DailyBudgetError("BUDGET_INITIALIZATION_INCOMPLETE") from None
    if path.exists() or marker.exists():
        lock.rmdir()
        if path.exists() and marker.exists():
            return
        raise DailyBudgetError("BUDGET_STATE_INCOMPLETE")
    # On failure leave the lock/partial state for explicit review, never reset it.
    ledger_id = str(uuid.uuid4())
    connection = sqlite3.connect(path, isolation_level=None)
    try:
        os.chmod(path, 0o600)
        connection.execute("BEGIN IMMEDIATE")
        connection.execute(f"PRAGMA application_id={APPLICATION_ID}")
        connection.execute(f"PRAGMA user_version={SCHEMA_VERSION}")
        connection.execute("CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
        connection.executemany("INSERT INTO meta VALUES (?, ?)",
                               [("schema", str(SCHEMA_VERSION)), ("ledger_id", ledger_id)])
        connection.execute("CREATE TABLE days (day TEXT PRIMARY KEY, max_calls INTEGER NOT NULL CHECK(max_calls > 0), max_micro_usd INTEGER NOT NULL CHECK(max_micro_usd > 0))")
        connection.execute("CREATE TABLE reservations (run_id TEXT PRIMARY KEY, reservation_id TEXT UNIQUE NOT NULL, day TEXT NOT NULL REFERENCES days(day), micro_usd INTEGER NOT NULL CHECK(micro_usd > 0), created_utc TEXT NOT NULL)")
        connection.commit()
    finally:
        connection.close()
    anchor = {"schema": SCHEMA_VERSION, "ledger_id": ledger_id}
    temp = marker.with_name(marker.name + "." + ledger_id + ".tmp")
    fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(anchor, sort_keys=True) + "\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temp, marker)
    lock.rmdir()


def _verify(connection, path):
    marker = _marker(path)
    _reject_symlinks(path)
    _reject_symlinks(marker)
    try:
        with marker.open("rb") as stream:
            raw = stream.read(4097)
        if len(raw) > 4096:
            raise ValueError
        anchor = json.loads(raw)
        if set(anchor) != {"schema", "ledger_id"} or anchor["schema"] != SCHEMA_VERSION:
            raise ValueError
        uuid.UUID(anchor["ledger_id"])
    except (OSError, ValueError, TypeError, KeyError):
        raise DailyBudgetError("BUDGET_STATE_ANCHOR_INVALID") from None
    if (connection.execute("PRAGMA application_id").fetchone()[0] != APPLICATION_ID
            or connection.execute("PRAGMA user_version").fetchone()[0] != SCHEMA_VERSION
            or connection.execute("PRAGMA quick_check").fetchone()[0] != "ok"):
        raise DailyBudgetError("BUDGET_STATE_INVALID")
    tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    if tables != {"meta", "days", "reservations"}:
        raise DailyBudgetError("BUDGET_STATE_INVALID")
    if dict(connection.execute("SELECT key, value FROM meta")) != {
            "schema": str(SCHEMA_VERSION), "ledger_id": anchor["ledger_id"]}:
        raise DailyBudgetError("BUDGET_LEDGER_IDENTITY_MISMATCH")
    if connection.execute("SELECT 1 FROM reservations WHERE typeof(micro_usd)!='integer' OR micro_usd<? OR micro_usd>? LIMIT 1",
                          (MIN_RESERVATION_MICRO_USD, MAX_MICRO_USD)).fetchone():
        raise DailyBudgetError("BUDGET_STATE_INVALID")
    return anchor["ledger_id"]


def _day(day):
    day = taipei_day() if day is None else day
    try:
        if not isinstance(day, str) or dt.date.fromisoformat(day).isoformat() != day:
            raise ValueError
    except (ValueError, TypeError):
        raise DailyBudgetError("INVALID_BUDGET_DAY") from None
    if day != taipei_day():
        raise DailyBudgetError("BUDGET_DAY_NOT_CURRENT_TAIPEI")
    return day


def reserve(statepath, run_id, day=None, *, daily_max_calls=5,
            daily_max_usd="0.05", reserve_usd="0.01"):
    """Atomically reserve one potential request, or return a non-dispatch duplicate.

    Limits may be tightened, never raised above the authorized default envelope.
    A day's policy is immutable once its first reservation is committed. Reserve
    BEFORE sending a request. Only request_slot_granted=True is a fresh slot;
    pricing, provider permission and overage verification are separate gates.
    """
    if not isinstance(run_id, str) or not RUN_ID.fullmatch(run_id):
        raise DailyBudgetError("INVALID_RUN_ID")
    day = _day(day)
    maximum, amount = _micros(daily_max_usd), _micros(reserve_usd)
    if (type(daily_max_calls) is not int or not 1 <= daily_max_calls <= MAX_CALLS
            or maximum > MAX_MICRO_USD or amount < MIN_RESERVATION_MICRO_USD
            or amount > maximum):
        raise DailyBudgetError("INVALID_BUDGET_CONFIG")
    path = Path(statepath).absolute()
    connection = None
    try:
        _initialize(path)
        connection = _connect(path)
        connection.execute("BEGIN IMMEDIATE")
        ledger_id = _verify(connection, path)
        policy = connection.execute("SELECT max_calls,max_micro_usd FROM days WHERE day=?", (day,)).fetchone()
        if policy and policy != (daily_max_calls, maximum):
            raise DailyBudgetError("DAILY_POLICY_MISMATCH")
        existing = connection.execute("SELECT reservation_id,day,micro_usd,created_utc FROM reservations WHERE run_id=?", (run_id,)).fetchone()
        count, used = connection.execute("SELECT COUNT(*),COALESCE(SUM(micro_usd),0) FROM reservations WHERE day=?", (day,)).fetchone()
        if existing:
            if existing[2] != amount:
                raise DailyBudgetError("RUN_ID_RESERVATION_CONFLICT")
            reservation_id, reservation_day, amount, created = existing
            granted = False
        else:
            if count >= daily_max_calls:
                raise DailyLimitExceeded("DAILY_CALL_LIMIT_REACHED")
            if used + amount > maximum:
                raise DailyLimitExceeded("DAILY_USD_ENVELOPE_REACHED")
            if not policy:
                connection.execute("INSERT INTO days VALUES (?,?,?)", (day, daily_max_calls, maximum))
            reservation_id, reservation_day = str(uuid.uuid4()), day
            created = dt.datetime.now(dt.timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
            connection.execute("INSERT INTO reservations VALUES (?,?,?,?,?)",
                               (run_id, reservation_id, day, amount, created))
            count, used, granted = count + 1, used + amount, True
        connection.commit()
        receipt = {
            "schema": "LABREPAIR_DAILY_BUDGET_RESERVATION_V1",
            "status": "RESERVED" if granted else "ALREADY_RESERVED",
            "ledger_id": ledger_id, "reservation_id": reservation_id,
            "run_id": run_id, "day": day, "reservation_day": reservation_day,
            "timezone": "Asia/Taipei (UTC+08:00)", "created_utc": created,
            "request_slot_granted": granted, "duplicate": not granted,
            "reserve_usd": _usd(amount), "daily_reserved_calls": count,
            "daily_reserved_usd": _usd(used), "daily_max_calls": daily_max_calls,
            "daily_max_usd": _usd(maximum), "reservation_retained_on_error": True,
            "provider_charge_usd": "unknown", "automatic_provider_retry": False,
            "control_scope": "LOCAL_APPLICATION_LEDGER_ONLY_NOT_PROVIDER_ACCOUNT_CAP",
            "pricing_and_provider_overage_verification": "CALLER_REQUIRED_BEFORE_DISPATCH",
        }
        receipt["receipt_sha256"] = hashlib.sha256(json.dumps(
            receipt, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        return receipt
    except DailyBudgetError:
        if connection and connection.in_transaction:
            connection.rollback()
        raise
    except (OSError, sqlite3.Error, ValueError, TypeError):
        if connection and connection.in_transaction:
            connection.rollback()
        raise DailyBudgetError("BUDGET_STATE_UNAVAILABLE_OR_CORRUPT") from None
    finally:
        if connection:
            connection.close()


def status(statepath, day=None):
    """Read a consistent ledger snapshot without creating or changing any state.

    Missing first-run state is unknown, not a reset to zero. Status never grants
    a dispatch: callers must still reserve atomically and verify provider gates.
    """
    day = _day(day)
    path = Path(statepath).absolute()
    marker = _marker(path)
    _reject_symlinks(path)
    _reject_symlinks(marker)
    if not path.exists():
        if marker.exists():
            raise DailyBudgetError("BUDGET_STATE_MISSING")
        if path.with_name(path.name + ".initializing").exists():
            raise DailyBudgetError("BUDGET_INITIALIZATION_INCOMPLETE")
        return {
            "schema": "LABREPAIR_DAILY_BUDGET_STATUS_V1", "status": "NOT_INITIALIZED",
            "day": day, "timezone": "Asia/Taipei (UTC+08:00)",
            "daily_reserved_calls": None, "daily_reserved_usd": "unknown",
            "daily_max_calls": MAX_CALLS, "daily_max_usd": _usd(MAX_MICRO_USD),
            "warning": "BUDGET_LEDGER_NOT_INITIALIZED", "request_slot_granted": False,
            "provider_charge_usd": "unknown",
            "control_scope": "LOCAL_APPLICATION_LEDGER_ONLY_NOT_PROVIDER_ACCOUNT_CAP",
        }
    if not marker.exists():
        raise DailyBudgetError("BUDGET_STATE_ANCHOR_MISSING")
    connection = None
    try:
        connection = _connect(path, read_only=True)
        connection.execute("BEGIN")
        ledger_id = _verify(connection, path)
        policy = connection.execute("SELECT max_calls,max_micro_usd FROM days WHERE day=?", (day,)).fetchone()
        max_calls, maximum = policy or (MAX_CALLS, MAX_MICRO_USD)
        if not (1 <= max_calls <= MAX_CALLS and 0 < maximum <= MAX_MICRO_USD):
            raise DailyBudgetError("BUDGET_STATE_INVALID")
        count, used = connection.execute("SELECT COUNT(*),COALESCE(SUM(micro_usd),0) FROM reservations WHERE day=?", (day,)).fetchone()
        slots = max(0, min(max_calls - count, (maximum - used) // MIN_RESERVATION_MICRO_USD))
        warning = ("DAILY_LIMIT_REACHED" if slots == 0 else
                   "DAILY_LIMIT_NEAR" if count >= max_calls - 1 or used >= maximum - MIN_RESERVATION_MICRO_USD else None)
        return {
            "schema": "LABREPAIR_DAILY_BUDGET_STATUS_V1", "status": "READY",
            "ledger_id": ledger_id, "day": day, "timezone": "Asia/Taipei (UTC+08:00)",
            "daily_reserved_calls": count, "daily_reserved_usd": _usd(used),
            "daily_max_calls": max_calls, "daily_max_usd": _usd(maximum),
            "available_minimum_envelope_slots": slots, "warning": warning,
            "request_slot_granted": False, "provider_charge_usd": "unknown",
            "control_scope": "LOCAL_APPLICATION_LEDGER_ONLY_NOT_PROVIDER_ACCOUNT_CAP",
            "pricing_and_provider_overage_verification": "CALLER_REQUIRED_BEFORE_DISPATCH",
        }
    except DailyBudgetError:
        raise
    except (OSError, sqlite3.Error, ValueError, TypeError):
        raise DailyBudgetError("BUDGET_STATE_UNAVAILABLE_OR_CORRUPT") from None
    finally:
        if connection:
            connection.close()
