"""Private, durable spending guard for explicitly authorized live API tests.

This module never reads API credentials or makes a network request. A caller
must reserve a conservative upper bound *before* each external call. A failed
or uncertain call retains its reservation; recording a higher observed cost
only increases the charged total. Money is represented as integer USD micros.
"""

from contextlib import contextmanager
import os
from pathlib import Path
import re
import sqlite3
import stat
import threading
import time
import uuid

from wanda.config import private_path


DEFAULT_DEADLINE = 1792076400  # 2026-10-15 15:00:00 UTC
MAX_MICROUSD = 1_000_000_000_000  # Bound inputs and SQLite arithmetic.
_PURPOSE = re.compile(r"[a-z][a-z0-9_-]{0,63}\Z")
_STATUSES = frozenset({"completed", "failed", "unknown"})


def _microusd(value, *, positive):
    if type(value) is not int or value < (1 if positive else 0) or value > MAX_MICROUSD:
        raise ValueError("Amount must be a bounded integer number of USD micros.")
    return value


def _deadline(value):
    if type(value) is not int or value <= 0:
        raise ValueError("Deadline must be a positive Unix timestamp in seconds.")
    return value


def _identifier(value):
    if not isinstance(value, str):
        raise ValueError("Invalid reservation identifier.")
    try:
        identifier = uuid.UUID(value)
    except (ValueError, AttributeError):
        raise ValueError("Invalid reservation identifier.") from None
    if str(identifier) != value:
        raise ValueError("Invalid reservation identifier.")
    return value


class TestBudget:
    """Atomic local ledger with an immutable authorization cap and cutoff.

    ``snapshot`` contains aggregate totals only. Purposes are short machine
    labels, never request payloads, transcripts, tokens or error text.
    """

    def __init__(self, path, limit_microusd=10_000_000, deadline=DEFAULT_DEADLINE, clock=time.time):
        limit_microusd = _microusd(limit_microusd, positive=True)
        deadline = _deadline(deadline)
        if not callable(clock):
            raise ValueError("Clock must be callable.")
        supplied = Path(path).expanduser()
        if supplied.is_symlink() or supplied.parent.is_symlink():
            raise ValueError("Budget path and its parent must not be symbolic links.")
        resolved = private_path(supplied)
        parent = resolved.parent
        parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        if os.name != "nt" and stat.S_IMODE(parent.stat().st_mode) != 0o700:
            raise ValueError("Budget parent directory must have mode 0700.")
        flags = os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0)
        descriptor = os.open(str(resolved), flags, 0o600)
        try:
            if not stat.S_ISREG(os.fstat(descriptor).st_mode):
                raise ValueError("Budget database must be a regular private file.")
            if hasattr(os, "fchmod"):
                os.fchmod(descriptor, 0o600)
        finally:
            os.close(descriptor)
        self.path = resolved
        self._clock = clock
        self._lock = threading.RLock()
        self._closed = False
        self._connection = sqlite3.connect(str(resolved), timeout=30, isolation_level=None, check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        try:
            self._connection.execute("PRAGMA journal_mode = DELETE")
            self._connection.execute("PRAGMA synchronous = FULL")
            self._connection.execute("PRAGMA trusted_schema = OFF")
            with self._transaction():
                self._connection.execute("""
                    CREATE TABLE IF NOT EXISTS policy (
                        id INTEGER PRIMARY KEY CHECK(id = 1),
                        limit_microusd INTEGER NOT NULL,
                        deadline INTEGER NOT NULL,
                        charged_microusd INTEGER NOT NULL DEFAULT 0
                    )
                """)
                self._connection.execute("""
                    CREATE TABLE IF NOT EXISTS reservations (
                        id TEXT PRIMARY KEY,
                        amount_microusd INTEGER NOT NULL,
                        estimated_microusd INTEGER,
                        purpose TEXT NOT NULL,
                        status TEXT NOT NULL,
                        reserved_at INTEGER NOT NULL,
                        recorded_at INTEGER
                    )
                """)
                row = self._connection.execute("SELECT * FROM policy WHERE id = 1").fetchone()
                if row is None:
                    self._connection.execute(
                        "INSERT INTO policy(id, limit_microusd, deadline, charged_microusd) VALUES (1, ?, ?, 0)",
                        (limit_microusd, deadline),
                    )
                elif row["limit_microusd"] != limit_microusd or row["deadline"] != deadline:
                    raise ValueError("Existing budget policy differs; do not silently change its cap or cutoff.")
        except BaseException:
            self._connection.close()
            self._closed = True
            raise

    @contextmanager
    def _transaction(self):
        with self._lock:
            if self._closed:
                raise RuntimeError("Budget ledger is closed.")
            self._connection.execute("BEGIN IMMEDIATE")
            try:
                yield
                self._connection.commit()
            except BaseException:
                self._connection.rollback()
                raise

    def _now(self):
        value = self._clock()
        if type(value) not in (int, float) or value < 0:
            raise ValueError("Clock returned an invalid Unix timestamp.")
        try:
            return int(value)
        except (OverflowError, ValueError):
            raise ValueError("Clock returned an invalid Unix timestamp.") from None

    def reserve(self, amount_microusd, purpose, *, max_reservations=None, require_prior_completed=False):
        """Reserve a maximum estimated cost before an external call."""
        amount = _microusd(amount_microusd, positive=True)
        if not isinstance(purpose, str) or not _PURPOSE.fullmatch(purpose):
            raise ValueError("Purpose must be a short lowercase machine label.")
        if max_reservations is not None and (type(max_reservations) is not int or max_reservations < 1):
            raise ValueError("Maximum reservations must be a positive integer.")
        if type(require_prior_completed) is not bool:
            raise ValueError("Prior-completion requirement must be boolean.")
        with self._transaction():
            row = self._connection.execute("SELECT * FROM policy WHERE id = 1").fetchone()
            now = self._now()
            if now >= row["deadline"]:
                raise PermissionError("Live test budget cutoff has passed.")
            if max_reservations is not None:
                count = self._connection.execute("SELECT COUNT(*) FROM reservations").fetchone()[0]
                if count >= max_reservations:
                    raise PermissionError("Live test attempt limit has been reached.")
            if require_prior_completed:
                unresolved = self._connection.execute(
                    "SELECT 1 FROM reservations WHERE status NOT IN ('completed', 'setup_rejected') LIMIT 1"
                ).fetchone()
                if unresolved is not None:
                    raise PermissionError("A previous live test needs review before another attempt.")
            if amount > row["limit_microusd"] - row["charged_microusd"]:
                raise PermissionError("Live test budget is exhausted.")
            identifier = str(uuid.uuid4())
            self._connection.execute(
                "INSERT INTO reservations(id, amount_microusd, estimated_microusd, purpose, status, reserved_at) "
                "VALUES (?, ?, NULL, ?, 'reserved', ?)",
                (identifier, amount, purpose, now),
            )
            self._connection.execute("UPDATE policy SET charged_microusd = charged_microusd + ? WHERE id = 1", (amount,))
            return identifier

    def record_result(self, reservation_id, estimated_microusd=None, status="unknown"):
        """Record a safe outcome. This never refunds the original reservation."""
        identifier = _identifier(reservation_id)
        if estimated_microusd is not None:
            estimated_microusd = _microusd(estimated_microusd, positive=False)
        if type(status) is not str or status not in _STATUSES:
            raise ValueError("Status must be completed, failed or unknown.")
        with self._transaction():
            row = self._connection.execute("SELECT * FROM reservations WHERE id = ?", (identifier,)).fetchone()
            if row is None:
                raise KeyError("Unknown reservation identifier.")
            if row["status"] != "reserved" and row["status"] != status:
                raise ValueError("A recorded test outcome cannot be reclassified.")
            prior_estimate = row["estimated_microusd"] or 0
            estimate = max(prior_estimate, estimated_microusd or 0)
            previous_charge = max(row["amount_microusd"], prior_estimate)
            new_charge = max(row["amount_microusd"], estimate)
            delta = new_charge - previous_charge
            policy = self._connection.execute("SELECT charged_microusd FROM policy WHERE id = 1").fetchone()
            if policy["charged_microusd"] + delta > 2**63 - 1:
                raise ValueError("Budget ledger total exceeds its supported range.")
            self._connection.execute(
                "UPDATE reservations SET estimated_microusd = ?, status = ?, recorded_at = ? WHERE id = ?",
                (estimate if estimated_microusd is not None or row["estimated_microusd"] is not None else None,
                 status, self._now(), identifier),
            )
            if delta:
                self._connection.execute(
                    "UPDATE policy SET charged_microusd = charged_microusd + ? WHERE id = 1", (delta,)
                )
            return new_charge

    def reconcile_rejected_setup(self, reservation_id, *, http_status, response_creates, received_sdp):
        """Manually classify an evidenced pre-generation HTTP 400; retain its full charge.

        This explicit transition cannot be produced by ``record_result``. The caller
        must independently verify these facts from the safe local test evidence.
        """
        identifier = _identifier(reservation_id)
        if (type(http_status) is not int or http_status != 400 or
                type(response_creates) is not int or response_creates != 0 or
                type(received_sdp) is not bool or received_sdp is not False):
            raise ValueError("Setup rejection evidence is incomplete or invalid.")
        with self._transaction():
            row = self._connection.execute(
                "SELECT status, amount_microusd, estimated_microusd FROM reservations WHERE id = ?",
                (identifier,),
            ).fetchone()
            if row is None:
                raise KeyError("Unknown reservation identifier.")
            if row["status"] != "unknown" or row["estimated_microusd"] not in (None, 0):
                raise ValueError("Only an unestimated unknown setup attempt can be reconciled.")
            self._connection.execute(
                "UPDATE reservations SET status = 'setup_rejected', estimated_microusd = 0, "
                "recorded_at = ? WHERE id = ?",
                (self._now(), identifier),
            )
            return row["amount_microusd"]

    def snapshot(self):
        with self._transaction():
            row = self._connection.execute("SELECT * FROM policy WHERE id = 1").fetchone()
            count = self._connection.execute("SELECT COUNT(*) FROM reservations").fetchone()[0]
            charged = row["charged_microusd"]
            return {
                "limit_microusd": row["limit_microusd"], "deadline": row["deadline"],
                "charged_microusd": charged,
                "available_microusd": max(0, row["limit_microusd"] - charged),
                "reservations": count, "over_limit": charged > row["limit_microusd"],
            }

    def close(self):
        with self._lock:
            if not self._closed:
                self._connection.close()
                self._closed = True

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()
