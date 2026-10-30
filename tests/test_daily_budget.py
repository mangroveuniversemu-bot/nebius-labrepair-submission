"""Offline daily ledger checks, including independent process reservations."""
import datetime as dt
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from labrepair.daily_budget import (
    DailyBudgetError, DailyLimitExceeded, reserve, status, taipei_day,
)


class DailyBudgetTests(unittest.TestCase):
    def setUp(self):
        # The desktop sandbox's OS temp directory can forbid SQLite/cleanup.
        # Keep disposable fixtures inside this authorized workspace instead.
        self.directory = tempfile.TemporaryDirectory(
            prefix=".budget-tests-", dir=Path(__file__).resolve().parents[1])
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "budget.sqlite"
        self.day = taipei_day()

    def take(self, run_id="test-1", **kwargs):
        return reserve(self.path, run_id, self.day, **kwargs)

    def count(self):
        with closing(sqlite3.connect(self.path)) as connection:
            return connection.execute("SELECT COUNT(*) FROM reservations").fetchone()[0]

    def test_first_reservation_creates_persistent_non_provider_cap_receipt(self):
        r = self.take()
        self.assertTrue(r["request_slot_granted"])
        self.assertFalse(r["duplicate"])
        self.assertEqual(r["daily_reserved_calls"], 1)
        self.assertEqual(r["daily_reserved_usd"], "0.010000")
        self.assertEqual(r["provider_charge_usd"], "unknown")
        self.assertIn("NOT_PROVIDER_ACCOUNT_CAP", r["control_scope"])
        self.assertEqual(self.count(), 1)

    def test_sixth_unique_run_is_blocked_and_no_reservation_is_deleted(self):
        for n in range(5):
            self.take(f"run-{n}")
        with self.assertRaisesRegex(DailyLimitExceeded, "DAILY_CALL_LIMIT_REACHED"):
            self.take("run-6")
        self.assertEqual(self.count(), 5)

    def test_larger_envelope_hits_currency_cap_before_call_cap(self):
        self.take("a", reserve_usd="0.02")
        r = self.take("b", reserve_usd="0.02")
        self.assertEqual(r["daily_reserved_usd"], "0.040000")
        with self.assertRaisesRegex(DailyLimitExceeded, "DAILY_USD_ENVELOPE_REACHED"):
            self.take("c", reserve_usd="0.02")
        self.assertEqual(self.count(), 2)

    def test_duplicate_never_grants_a_second_dispatch_or_consumes_another_slot(self):
        first = self.take("same-id")
        again = self.take("same-id")
        self.assertFalse(again["request_slot_granted"])
        self.assertTrue(again["duplicate"])
        self.assertEqual(first["reservation_id"], again["reservation_id"])
        self.assertEqual(again["daily_reserved_calls"], 1)
        self.assertEqual(self.count(), 1)

    def test_unknown_provider_failure_does_not_refund_a_reservation(self):
        self.take("failed-call")
        # No real provider: simulate the caller observing an unknown failure.
        try:
            raise TimeoutError("simulated unknown outcome")
        except TimeoutError:
            pass
        r = self.take("next-call")
        self.assertEqual(r["daily_reserved_calls"], 2)
        self.assertEqual(r["daily_reserved_usd"], "0.020000")
        self.assertFalse(self.take("failed-call")["request_slot_granted"])

    def test_eight_independent_processes_cannot_exceed_shared_five_call_cap(self):
        self.take("bootstrap")
        self.assertEqual(self.process_reservations(), 4)
        self.assertEqual(self.count(), 5)

    def test_concurrent_first_initialization_cannot_create_separate_ledgers(self):
        self.assertEqual(self.process_reservations(), 5)
        self.assertEqual(self.count(), 5)

    def process_reservations(self):
        code = """import json,sys
from labrepair.daily_budget import reserve,DailyLimitExceeded
try:
 r=reserve(sys.argv[1],sys.argv[2],sys.argv[3]);print(json.dumps({'granted':r['request_slot_granted']}))
except DailyLimitExceeded:
 print(json.dumps({'granted':False,'limited':True}))
"""
        processes = [subprocess.Popen([sys.executable, "-c", code, str(self.path), f"process-{n}", self.day],
                                      cwd=Path(__file__).resolve().parents[1],
                                      stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                     for n in range(8)]
        results = []
        try:
            for process in processes:
                out, err = process.communicate(timeout=20)
                self.assertEqual(process.returncode, 0, err)
                results.append(json.loads(out))
        finally:
            for process in processes:
                if process.poll() is None:
                    process.kill()
                    process.communicate()
        return sum(r["granted"] for r in results)

    def test_deleted_database_with_surviving_marker_is_not_recreated(self):
        self.take()
        self.path.unlink()
        with self.assertRaisesRegex(DailyBudgetError, "BUDGET_STATE_MISSING"):
            self.take("next")
        self.assertFalse(self.path.exists())

    def test_missing_anchor_and_existing_database_fail_closed(self):
        self.take()
        self.path.with_name(self.path.name + ".state.json").unlink()
        with self.assertRaisesRegex(DailyBudgetError, "BUDGET_STATE_ANCHOR_MISSING"):
            self.take("next")
        self.assertEqual(self.count(), 1)

    def test_corrupt_database_is_not_reset(self):
        self.take()
        self.path.write_bytes(b"not a sqlite database")
        with self.assertRaises(DailyBudgetError):
            self.take("next")
        self.assertEqual(self.path.read_bytes(), b"not a sqlite database")

    def test_zeroed_database_is_not_treated_as_a_first_run(self):
        self.take()
        self.path.write_bytes(b"")
        with self.assertRaisesRegex(DailyBudgetError, "BUDGET_STATE_INVALID"):
            self.take("next")

    def test_ledger_replacement_with_wrong_identity_fails_closed(self):
        self.take()
        other = self.path.with_name("other.sqlite")
        reserve(other, "other", self.day)
        self.path.write_bytes(other.read_bytes())
        with self.assertRaisesRegex(DailyBudgetError, "BUDGET_LEDGER_IDENTITY_MISMATCH"):
            self.take("next")

    def test_same_day_policy_cannot_be_relaxed_after_first_reservation(self):
        self.take(daily_max_calls=2)
        with self.assertRaisesRegex(DailyBudgetError, "DAILY_POLICY_MISMATCH"):
            self.take("next", daily_max_calls=5)
        self.assertEqual(self.count(), 1)

    def test_invalid_or_oversized_config_never_creates_a_ledger(self):
        for config in ({"reserve_usd": "NaN"}, {"reserve_usd": "1e9999999"}, {"reserve_usd": "0.001"},
                       {"daily_max_usd": "0.06"}, {"daily_max_calls": 6},
                       {"daily_max_calls": True}, {"reserve_usd": 0.01}):
            with self.subTest(config=config), self.assertRaises(DailyBudgetError):
                self.take(**config)
        self.assertFalse(self.path.exists())

    def test_backdating_or_future_dating_cannot_reset_today(self):
        with self.assertRaisesRegex(DailyBudgetError, "BUDGET_DAY_NOT_CURRENT_TAIPEI"):
            reserve(self.path, "test", "2000-01-01")
        self.assertFalse(self.path.exists())

    def test_taipei_day_boundary_is_explicit(self):
        self.assertEqual(taipei_day(dt.datetime(2026, 10, 30, 15, 59, 59, tzinfo=dt.timezone.utc)), "2026-10-30")
        self.assertEqual(taipei_day(dt.datetime(2026, 10, 30, 16, 0, 0, tzinfo=dt.timezone.utc)), "2026-10-31")

    def test_new_day_allows_new_id_but_old_id_cannot_be_replayed(self):
        first = self.take("old-id")
        tomorrow = (dt.date.fromisoformat(self.day) + dt.timedelta(days=1)).isoformat()
        with patch("labrepair.daily_budget.taipei_day", return_value=tomorrow):
            duplicate = reserve(self.path, "old-id", tomorrow)
            fresh = reserve(self.path, "new-id", tomorrow)
        self.assertFalse(duplicate["request_slot_granted"])
        self.assertEqual(duplicate["reservation_id"], first["reservation_id"])
        self.assertEqual(duplicate["reservation_day"], self.day)
        self.assertEqual(fresh["daily_reserved_calls"], 1)
        self.assertEqual(self.count(), 2)

    def test_reusing_run_id_with_a_different_envelope_is_not_a_new_request(self):
        self.take("same-id")
        with self.assertRaisesRegex(DailyBudgetError, "RUN_ID_RESERVATION_CONFLICT"):
            self.take("same-id", reserve_usd="0.02")
        self.assertEqual(self.count(), 1)

    def test_status_missing_first_run_is_unknown_and_creates_nothing(self):
        r = status(self.path, self.day)
        self.assertEqual(r["status"], "NOT_INITIALIZED")
        self.assertIsNone(r["daily_reserved_calls"])
        self.assertEqual(r["daily_reserved_usd"], "unknown")
        self.assertFalse(self.path.exists())

    def test_status_warns_at_four_of_five_and_never_grants_a_dispatch(self):
        for n in range(4):
            self.take(f"warn-{n}")
        r = status(self.path, self.day)
        self.assertEqual(r["daily_reserved_calls"], 4)
        self.assertEqual(r["warning"], "DAILY_LIMIT_NEAR")
        self.assertEqual(r["available_minimum_envelope_slots"], 1)
        self.assertFalse(r["request_slot_granted"])
        self.take("last")
        self.assertEqual(status(self.path)["warning"], "DAILY_LIMIT_REACHED")

    def test_status_does_not_change_database_or_anchor_bytes(self):
        self.take()
        marker = self.path.with_name(self.path.name + ".state.json")
        before = (self.path.read_bytes(), marker.read_bytes())
        status(self.path)
        self.assertEqual((self.path.read_bytes(), marker.read_bytes()), before)

    def test_status_corruption_or_deleted_state_fails_closed(self):
        self.take()
        original = self.path.read_bytes()
        self.path.write_bytes(b"corrupt")
        with self.assertRaises(DailyBudgetError):
            status(self.path)
        self.path.write_bytes(original)
        self.path.unlink()
        with self.assertRaisesRegex(DailyBudgetError, "BUDGET_STATE_MISSING"):
            status(self.path)

    def test_tampered_reservation_below_envelope_floor_fails_closed(self):
        self.take()
        with closing(sqlite3.connect(self.path)) as connection:
            connection.execute("UPDATE reservations SET micro_usd=1")
            connection.commit()
        with self.assertRaisesRegex(DailyBudgetError, "BUDGET_STATE_INVALID"):
            self.take("next")
        with self.assertRaisesRegex(DailyBudgetError, "BUDGET_STATE_INVALID"):
            status(self.path)


if __name__ == "__main__":
    unittest.main()
