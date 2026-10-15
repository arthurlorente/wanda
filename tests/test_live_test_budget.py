"""Synthetic tests for the private, durable live-test spending guard."""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import os
from pathlib import Path
import stat
import tempfile
import threading
import unittest

from scripts.live_test_budget import DEFAULT_DEADLINE, TestBudget


class LiveTestBudgetTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="wanda-budget-test-")
        self.path = Path(self.temp.name) / "private" / "budget.sqlite3"
        self.now = [DEFAULT_DEADLINE - 100]

    def tearDown(self):
        self.temp.cleanup()

    def ledger(self, limit=100, deadline=DEFAULT_DEADLINE):
        return TestBudget(self.path, limit_microusd=limit, deadline=deadline, clock=lambda: self.now[0])

    def test_cutoff_literal_and_reservation_before_call(self):
        self.assertEqual(DEFAULT_DEADLINE,
                         int(datetime(2026, 10, 15, 15, 0, tzinfo=timezone.utc).timestamp()))
        with self.ledger() as budget:
            identifier = budget.reserve(60, "voice_handshake")
            self.assertEqual(budget.snapshot(), {
                "limit_microusd": 100, "deadline": DEFAULT_DEADLINE,
                "charged_microusd": 60, "available_microusd": 40,
                "reservations": 1, "over_limit": False,
            })
            self.assertEqual(budget.record_result(identifier, estimated_microusd=20, status="failed"), 60)
            self.assertEqual(budget.snapshot()["charged_microusd"], 60)
            with self.assertRaises(PermissionError):
                budget.reserve(41, "voice_audio")
            self.assertEqual(budget.reserve(40, "voice_audio") is not None, True)
            with self.assertRaises(PermissionError):
                budget.reserve(1, "voice_extra")

    def test_restart_keeps_policy_spend_and_no_silent_cap_or_cutoff_change(self):
        with self.ledger() as budget:
            identifier = budget.reserve(30, "synthetic_call")
            budget.record_result(identifier, status="unknown")
        with self.ledger() as reopened:
            self.assertEqual((reopened.snapshot()["charged_microusd"], reopened.snapshot()["reservations"]), (30, 1))
        for limit, deadline in ((101, DEFAULT_DEADLINE), (99, DEFAULT_DEADLINE),
                                (100, DEFAULT_DEADLINE + 1)):
            with self.subTest(limit=limit, deadline=deadline), self.assertRaises(ValueError):
                self.ledger(limit=limit, deadline=deadline)
        with self.ledger() as reopened:
            self.assertEqual(reopened.snapshot()["charged_microusd"], 30)

    def test_cutoff_blocks_new_reservations_but_allows_results_and_snapshot(self):
        with self.ledger() as budget:
            identifier = budget.reserve(20, "voice_smoke")
            self.now[0] = DEFAULT_DEADLINE
            with self.assertRaises(PermissionError):
                budget.reserve(1, "voice_smoke")
            self.assertEqual(budget.record_result(identifier, estimated_microusd=25, status="completed"), 25)
            self.assertEqual(budget.snapshot()["charged_microusd"], 25)

    def test_higher_actual_is_monotonic_and_flags_over_limit(self):
        with self.ledger() as budget:
            identifier = budget.reserve(80, "voice_audio")
            self.assertEqual(budget.record_result(identifier, estimated_microusd=120, status="completed"), 120)
            self.assertEqual(budget.record_result(identifier, estimated_microusd=10, status="completed"), 120)
            snapshot = budget.snapshot()
            self.assertEqual((snapshot["charged_microusd"], snapshot["available_microusd"], snapshot["over_limit"]),
                             (120, 0, True))
            with self.assertRaises(PermissionError):
                budget.reserve(1, "voice_extra")

    def test_second_attempt_requires_confirmed_prior_result_atomically(self):
        with self.ledger() as budget:
            first = budget.reserve(20, "voice_smoke", max_reservations=2, require_prior_completed=True)
            with self.assertRaises(PermissionError):
                budget.reserve(20, "voice_cancel", max_reservations=2, require_prior_completed=True)
            budget.record_result(first, status="unknown")
            with self.assertRaises(PermissionError):
                budget.reserve(20, "voice_cancel", max_reservations=2, require_prior_completed=True)
            with self.assertRaises(ValueError):
                budget.record_result(first, status="completed")
        other_path = Path(self.temp.name) / "private" / "confirmed.sqlite3"
        with TestBudget(other_path, limit_microusd=100, deadline=DEFAULT_DEADLINE,
                        clock=lambda: self.now[0]) as budget:
            first = budget.reserve(20, "voice_smoke", max_reservations=2, require_prior_completed=True)
            budget.record_result(first, status="completed")
            budget.reserve(20, "voice_cancel", max_reservations=2, require_prior_completed=True)
            with self.assertRaises(PermissionError):
                budget.reserve(20, "voice_extra", max_reservations=2, require_prior_completed=True)

    def test_evidenced_http_400_setup_reconciliation_retains_charge_and_one_attempt(self):
        path = Path(self.temp.name) / "private" / "reconciled.sqlite3"
        with TestBudget(path, limit_microusd=10_000_000, deadline=DEFAULT_DEADLINE,
                        clock=lambda: self.now[0]) as budget:
            first = budget.reserve(3_000_000, "voice_smoke", max_reservations=2,
                                   require_prior_completed=True)
            budget.record_result(first, status="unknown")
            with self.assertRaises(PermissionError):
                budget.reserve(3_000_000, "voice_cancel", max_reservations=2,
                               require_prior_completed=True)
            for evidence in (
                {"http_status": 401, "response_creates": 0, "received_sdp": False},
                {"http_status": True, "response_creates": 0, "received_sdp": False},
                {"http_status": 400, "response_creates": 1, "received_sdp": False},
                {"http_status": 400, "response_creates": False, "received_sdp": False},
                {"http_status": 400, "response_creates": 0, "received_sdp": True},
                {"http_status": 400, "response_creates": 0, "received_sdp": 0},
            ):
                with self.subTest(evidence=evidence), self.assertRaises(ValueError):
                    budget.reconcile_rejected_setup(first, **evidence)
            with self.assertRaises(ValueError):
                budget.record_result(first, status="setup_rejected")
            self.assertEqual(budget.snapshot()["charged_microusd"], 3_000_000)
            self.assertEqual(budget.reconcile_rejected_setup(
                first, http_status=400, response_creates=0, received_sdp=False), 3_000_000)
            self.assertEqual(budget.snapshot()["charged_microusd"], 3_000_000)
            with self.assertRaises(ValueError):
                budget.record_result(first, status="completed")
            with self.assertRaises(ValueError):
                budget.reconcile_rejected_setup(
                    first, http_status=400, response_creates=0, received_sdp=False)
            budget.reserve(3_000_000, "voice_cancel", max_reservations=2,
                           require_prior_completed=True)
            self.assertEqual((budget.snapshot()["charged_microusd"], budget.snapshot()["reservations"]),
                             (6_000_000, 2))
            with self.assertRaises(PermissionError):
                budget.reserve(1, "voice_extra", max_reservations=2,
                               require_prior_completed=True)

    def test_setup_reconciliation_rejects_usage_estimate_even_with_http_400(self):
        with self.ledger() as budget:
            identifier = budget.reserve(20, "voice_smoke")
            budget.record_result(identifier, estimated_microusd=1, status="unknown")
            with self.assertRaises(ValueError):
                budget.reconcile_rejected_setup(
                    identifier, http_status=400, response_creates=0, received_sdp=False)

    def test_rejects_noninteger_negative_zero_and_unbounded_values(self):
        with self.ledger() as budget:
            for invalid in (True, False, None, 0, -1, 1.5, "1", 1_000_000_000_001):
                with self.subTest(amount=invalid), self.assertRaises(ValueError):
                    budget.reserve(invalid, "voice_smoke")
            for purpose in ("", "Voice Test", "a" * 65, "api-key:secret", "foo/bar", 123):
                with self.subTest(purpose=purpose), self.assertRaises(ValueError):
                    budget.reserve(1, purpose)
            identifier = budget.reserve(10, "voice_smoke")
            for invalid in (True, -1, 1.5, "5", 1_000_000_000_001):
                with self.subTest(estimated=invalid), self.assertRaises(ValueError):
                    budget.record_result(identifier, estimated_microusd=invalid)
            for status in ("paid $10", "success; key=secret", [], 1, None):
                with self.subTest(status=status), self.assertRaises(ValueError):
                    budget.record_result(identifier, status=status)
            with self.assertRaises(ValueError):
                budget.record_result("not-an-id", status="failed")
            self.assertEqual(budget.snapshot()["charged_microusd"], 10)
        for limit, deadline in ((True, DEFAULT_DEADLINE), (0, DEFAULT_DEADLINE),
                                (100, True), (100, -1)):
            with self.subTest(limit=limit, deadline=deadline), self.assertRaises(ValueError):
                self.ledger(limit=limit, deadline=deadline)

    def test_atomic_concurrent_reservations_across_connections(self):
        first, second = self.ledger(limit=50), self.ledger(limit=50)
        start = threading.Barrier(2)

        def reserve_many(ledger):
            start.wait(timeout=5)
            accepted = []
            for _ in range(40):
                try:
                    accepted.append(ledger.reserve(1, "voice_parallel"))
                except PermissionError:
                    pass
            return accepted

        try:
            with ThreadPoolExecutor(max_workers=2) as pool:
                ids = [identifier for result in pool.map(reserve_many, (first, second)) for identifier in result]
            self.assertEqual(len(ids), 50)
            self.assertEqual(len(set(ids)), 50)
            self.assertEqual(first.snapshot()["charged_microusd"], 50)
            self.assertEqual(second.snapshot()["reservations"], 50)
        finally:
            first.close()
            second.close()

    def test_private_path_symlinks_modes_and_closed_ledger(self):
        with self.ledger() as budget:
            budget.reserve(1, "voice_smoke")
            if os.name != "nt":
                self.assertEqual(stat.S_IMODE(self.path.parent.stat().st_mode), 0o700)
                self.assertEqual(stat.S_IMODE(self.path.stat().st_mode), 0o600)
        for action in (lambda: budget.reserve(1, "voice_smoke"), budget.snapshot,
                       lambda: budget.record_result("00000000-0000-4000-8000-000000000000")):
            with self.assertRaises(RuntimeError):
                action()
        checkout = Path(__file__).resolve().parent.parent
        with self.assertRaises(ValueError):
            TestBudget(checkout / "private-budget.sqlite3", limit_microusd=100,
                       clock=lambda: self.now[0])
        if hasattr(os, "symlink"):
            link = Path(self.temp.name) / "budget-link.sqlite3"
            try:
                link.symlink_to(self.path)
            except OSError:
                pass
            else:
                with self.assertRaises(ValueError):
                    TestBudget(link, limit_microusd=100, clock=lambda: self.now[0])
            parent_link = Path(self.temp.name) / "parent-link"
            try:
                parent_link.symlink_to(self.path.parent, target_is_directory=True)
            except OSError:
                pass
            else:
                with self.assertRaises(ValueError):
                    TestBudget(parent_link / "another.sqlite3", limit_microusd=100,
                               clock=lambda: self.now[0])
        if os.name != "nt":
            permissive = Path(self.temp.name) / "permissive"
            permissive.mkdir(mode=0o755)
            permissive.chmod(0o755)
            with self.assertRaises(ValueError):
                TestBudget(permissive / "budget.sqlite3", limit_microusd=100,
                           clock=lambda: self.now[0])


if __name__ == "__main__":
    unittest.main()
