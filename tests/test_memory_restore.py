"""Synthetic local backup/recovery tests; no plaintext fixtures or network I/O."""

from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import json
import math
from pathlib import Path
import sqlite3
import tempfile
import threading
import unittest
from unittest.mock import patch
import uuid

from wanda.memory import MemoryStore, BACKUP_FORMAT, BACKUP_VERSION


class MemoryRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="wanda-recovery-test-")
        self.path = Path(self.temp.name) / "memory.sqlite3"
        self.store = MemoryStore(self.path)
        self.now = 1_800_000_000.0
        self.clock = patch("wanda.memory.time.time", return_value=self.now)
        self.clock.start()
        self.owner, self.other = "synthetic-owner", "synthetic-other"
        self.store.set_enabled(self.owner, True)
        self.store.set_enabled(self.other, True)

    def tearDown(self):
        self.store.close()
        self.clock.stop()
        self.temp.cleanup()

    def record(self, text="Synthetic reviewed project", category="project", *, expires_at=None):
        return {"id": str(uuid.uuid4()), "text": text, "category": category,
                "created_at": self.now - 100, "expires_at": expires_at}

    def archive(self, *records):
        return {"format": BACKUP_FORMAT, "version": BACKUP_VERSION,
                "created_at": self.now, "memories": list(records)}

    def snapshot(self):
        # Direct reads deliberately avoid expiry-pruning management APIs.
        return {table: [tuple(row) for row in self.store._connection.execute(
            f"SELECT * FROM {table} ORDER BY rowid"
        ).fetchall()] for table in ("owners", "memories", "disclosure_grants")}

    def test_backup_is_owner_scoped_minimal_and_available_while_disabled(self):
        saved = self.store.save(self.owner, "Synthetic local project", "project", approved=True)
        self.store.save(self.other, "OTHER_OWNER_SENTINEL", "sensitive", approved=True)
        self.store.set_grant(self.owner, "openai", "project", True)
        self.store.set_enabled(self.owner, False)
        before = self.snapshot()
        archive = self.store.backup(self.owner)
        self.assertEqual(set(archive), {"format", "version", "created_at", "memories"})
        self.assertEqual((archive["format"], archive["version"]), (BACKUP_FORMAT, BACKUP_VERSION))
        self.assertEqual(len(archive["memories"]), 1)
        self.assertEqual(set(archive["memories"][0]), {"id", "text", "category", "created_at", "expires_at"})
        self.assertEqual(archive["memories"][0]["id"], saved["id"])
        serialized = json.dumps(archive)
        for hidden in (self.owner, self.other, "OTHER_OWNER_SENTINEL", "grants", "enabled", "provider", "openai", "disclosure_categories"):
            self.assertNotIn(hidden, serialized)
        self.assertEqual(before, self.snapshot())

    def test_backup_excludes_expired_without_deleting_existing_rows_or_grants(self):
        expired = self.store.save(self.owner, "Synthetic short-lived note", "temporary", approved=True, expires_at=self.now + 1)
        self.store.set_grant(self.owner, "openai", "temporary", True, expires_at=self.now + 1)
        with patch("wanda.memory.time.time", return_value=self.now + 2):
            before = self.snapshot()
            backup = self.store.backup(self.owner)
            self.assertEqual(backup["memories"], [])
            self.assertIn(expired["id"], str(before))
            self.assertEqual(self.snapshot(), before)

    def test_round_trip_merges_new_ids_and_preserves_timestamps_and_expiration(self):
        first = self.store.save(self.owner, "Synthetic ongoing garden", "project", approved=True)
        second = self.store.save(self.owner, "Synthetic temporary task", "temporary", approved=True, expires_at=self.now + 900)
        archive = json.loads(json.dumps(self.store.backup(self.owner)))
        other_existing = self.store.save(self.other, "I prefer water.")
        preview = self.store.restore_preview(self.other, archive)
        self.assertEqual(preview, {"total": 2, "restorable": 2, "skipped_expired": 0,
                                  "duplicates": 0, "existing": 1, "capacity": 1000,
                                  "available": 999, "exceeds_capacity": False})
        result = self.store.restore(self.other, archive, approved=True)
        self.assertEqual(result, {**preview, "restored": 2})
        restored = self.store.list_memories(self.other)
        self.assertEqual(len(restored), 3)
        self.assertIn(other_existing, restored)
        imported = {row["text"]: row for row in restored if row["id"] != other_existing["id"]}
        for source in (first, second):
            actual = imported[source["text"]]
            self.assertNotEqual(actual["id"], source["id"])
            for key in ("text", "category", "created_at", "expires_at"):
                self.assertEqual(actual[key], source[key])
        self.assertEqual({row["id"] for row in self.store.list_memories(self.owner)}, {first["id"], second["id"]})
        self.store.close()
        self.store = MemoryStore(self.path)
        self.assertEqual(len(self.store.list_memories(self.other)), 3)

    def test_preview_is_read_only_even_with_expired_rows_and_disabled_owner(self):
        self.store.save(self.owner, "Synthetic expired item", "temporary", approved=True, expires_at=self.now + 1)
        self.store.set_grant(self.owner, "openai", "temporary", True, expires_at=self.now + 1)
        self.store.set_enabled(self.owner, False)
        archive = self.archive(self.record())
        with patch("wanda.memory.time.time", return_value=self.now + 2):
            before = self.snapshot()
            preview = self.store.restore_preview(self.owner, archive)
            self.assertEqual(preview["existing"], 0)
            self.assertEqual(preview["available"], 1000)
            self.assertEqual(preview["restorable"], 1)
            self.assertEqual(before, self.snapshot())

    def test_restore_requires_enabled_current_owner_and_actual_explicit_approval(self):
        archive = self.archive(self.record())
        before = self.snapshot()
        with self.assertRaises(PermissionError):
            self.store.restore(self.owner, archive)
        with self.assertRaises(PermissionError):
            self.store.restore(self.owner, archive, approved=False)
        for invalid in (None, 1, 0, "true", "false", [], {}):
            with self.subTest(approval=invalid), self.assertRaises(ValueError):
                self.store.restore(self.owner, archive, approved=invalid)
        self.assertEqual(before, self.snapshot())
        self.store.set_enabled(self.owner, False)
        before = self.snapshot()
        with self.assertRaises(PermissionError):
            self.store.restore(self.owner, archive, approved=True)
        self.assertEqual(before, self.snapshot())
        self.assertFalse(self.store.is_enabled(self.owner))
        with self.assertRaises(PermissionError):
            self.store.restore("unknown-owner", archive, approved=True)
        self.assertEqual(before, self.snapshot())

    def test_restore_never_changes_existing_memory_consent_or_grants_for_any_owner(self):
        existing = self.store.save(self.owner, "Existing synthetic private note", "sensitive", approved=True)
        other = self.store.save(self.other, "Synthetic other account", "project", approved=True)
        for owner in (self.owner, self.other):
            self.store.set_grant(owner, "openai", "sensitive", True, one_time=True, expires_at=self.now + 1)
            self.store.set_grant(owner, "other-provider", "project", False)
        before = self.snapshot()
        with patch("wanda.memory.time.time", return_value=self.now + 2):
            self.store.restore(self.owner, self.archive(self.record()), approved=True)
        after = self.snapshot()
        self.assertEqual(before["owners"], after["owners"])
        self.assertEqual(before["disclosure_grants"], after["disclosure_grants"])
        for record in before["memories"]:
            self.assertIn(record, after["memories"])
        self.assertEqual(len(after["memories"]), len(before["memories"]) + 1)
        self.assertIn(existing["id"], str(after))
        self.assertIn(other["id"], str(after))

    def test_archive_cannot_select_owner_restore_consent_grants_or_credentials(self):
        for field, value in (("owner", self.other), ("enabled", True), ("approved", True),
                             ("grants", []), ("token", "SYNTHETIC_SECRET"), ("credentials", {})):
            with self.subTest(field=field):
                archive = self.archive(self.record())
                archive[field] = value
                before = self.snapshot()
                with self.assertRaises(ValueError):
                    self.store.restore_preview(self.owner, archive)
                with self.assertRaises(ValueError):
                    self.store.restore(self.owner, archive, approved=True)
                self.assertEqual(self.snapshot(), before)
                archive = self.archive(self.record())
                archive["memories"][0][field] = value
                with self.assertRaises(ValueError):
                    self.store.restore(self.owner, archive, approved=True)
                self.assertEqual(self.snapshot(), before)

    def test_wrong_owner_archive_ids_do_not_modify_or_replace_that_owners_records(self):
        source = self.store.save(self.other, "Synthetic other owner source", "project", approved=True)
        archive = self.store.backup(self.other)
        self.store.restore(self.owner, archive, approved=True)
        imported = self.store.list_memories(self.owner)[0]
        self.assertNotEqual(source["id"], imported["id"])
        self.assertEqual(self.store.list_memories(self.other), [source])
        # A portable archive has no original-owner identity. It can be explicitly
        # imported only into the caller-selected authenticated account, not a
        # target selected by an archive's identifier or metadata.
        self.assertFalse(self.store.delete(self.owner, source["id"]))

    def test_duplicates_within_archive_and_current_owner_are_skipped(self):
        existing = self.store.save(self.owner, "Synthetic existing project", "project", approved=True)
        prior = {key: existing[key] for key in ("id", "text", "category", "created_at", "expires_at")}
        first = self.record("Synthetic new project")
        duplicate_new_id = dict(first, id=str(uuid.uuid4()))
        duplicate_prior = dict(prior, id=str(uuid.uuid4()))
        archive = self.archive(prior, duplicate_prior, first, deepcopy(first), duplicate_new_id)
        preview = self.store.restore_preview(self.owner, archive)
        self.assertEqual((preview["total"], preview["restorable"], preview["duplicates"]), (5, 1, 4))
        result = self.store.restore(self.owner, archive, approved=True)
        self.assertEqual(result["restored"], 1)
        again = self.store.restore(self.owner, archive, approved=True)
        self.assertEqual((again["restored"], again["duplicates"]), (0, 5))
        self.assertEqual(len(self.store.list_memories(self.owner)), 2)

    def test_dedupe_preserves_distinct_categories_and_expirations(self):
        text = "Synthetic same text, distinct purpose"
        records = [self.record(text), self.record(text, "sensitive"),
                   self.record(text, expires_at=self.now + 50), self.record(text, expires_at=self.now + 100)]
        result = self.store.restore(self.owner, self.archive(*records), approved=True)
        self.assertEqual((result["restored"], result["duplicates"]), (4, 0))

    def test_expired_records_skipped_without_reviving_deadlines(self):
        expired = self.record("Synthetic expired note", "temporary", expires_at=self.now - 1)
        boundary = self.record("Synthetic expires now", "temporary", expires_at=self.now)
        future = self.record("Synthetic still active", "temporary", expires_at=self.now + 1)
        archive = self.archive(expired, boundary, future)
        preview = self.store.restore_preview(self.owner, archive)
        self.assertEqual((preview["restorable"], preview["skipped_expired"]), (1, 2))
        self.assertEqual(self.store.restore(self.owner, archive, approved=True)["restored"], 1)
        stored = self.store.list_memories(self.owner)[0]
        self.assertEqual(stored["expires_at"], self.now + 1)
        with patch("wanda.memory.time.time", return_value=self.now + 1):
            self.assertEqual(self.store.list_memories(self.owner), [])

    def test_restore_revalidates_expiry_and_payload_after_preview(self):
        archive = self.archive(self.record(expires_at=self.now + 1))
        self.assertEqual(self.store.restore_preview(self.owner, archive)["restorable"], 1)
        with patch("wanda.memory.time.time", return_value=self.now + 2):
            result = self.store.restore(self.owner, archive, approved=True)
        self.assertEqual((result["restored"], result["skipped_expired"]), (0, 1))
        archive = self.archive(self.record())
        self.store.restore_preview(self.owner, archive)
        archive["memories"][0]["owner"] = self.other
        with self.assertRaises(ValueError):
            self.store.restore(self.owner, archive, approved=True)
        self.assertEqual(self.store.list_memories(self.owner), [])

    def test_capacity_preview_and_commit_recheck_do_not_partially_import(self):
        archive = self.archive(self.record("Synthetic one"), self.record("Synthetic two"))
        with patch("wanda.memory.MAX_MEMORIES_PER_OWNER", 2):
            preview = self.store.restore_preview(self.owner, archive)
            self.assertFalse(preview["exceeds_capacity"])
            self.store.save(self.owner, "I prefer water.")
            before = self.snapshot()
            preview = self.store.restore_preview(self.owner, archive)
            self.assertEqual((preview["existing"], preview["available"], preview["restorable"]), (1, 1, 2))
            self.assertTrue(preview["exceeds_capacity"])
            with self.assertRaises(ValueError):
                self.store.restore(self.owner, archive, approved=True)
            self.assertEqual(before, self.snapshot())

    def test_capacity_uses_unique_unexpired_candidates_and_prunes_only_owners_expired_memories(self):
        self.store.save(self.owner, "Synthetic old temporary note", "temporary", approved=True, expires_at=self.now + 1)
        self.store.save(self.other, "Synthetic other expired note", "temporary", approved=True, expires_at=self.now + 1)
        self.store.set_grant(self.owner, "openai", "temporary", True, expires_at=self.now + 1)
        new = self.record("Synthetic single new note")
        expired = self.record("Synthetic expired archive note", "temporary", expires_at=self.now - 1)
        archive = self.archive(new, deepcopy(new), expired)
        with patch("wanda.memory.MAX_MEMORIES_PER_OWNER", 3), patch("wanda.memory.time.time", return_value=self.now + 2):
            before = self.snapshot()
            result = self.store.restore(self.owner, archive, approved=True)
            self.assertEqual((result["restored"], result["duplicates"], result["skipped_expired"]), (1, 1, 1))
            self.assertEqual((result["existing"], result["available"]), (0, 3))
            self.assertEqual(len(self.snapshot()["memories"]), 2)
            self.assertNotIn(before["memories"][0], self.snapshot()["memories"])
            self.assertIn(before["memories"][1], self.snapshot()["memories"])
            self.assertEqual(before["owners"], self.snapshot()["owners"])
            self.assertEqual(before["disclosure_grants"], self.snapshot()["disclosure_grants"])

    def test_expired_local_records_do_not_cause_false_full_capacity_failure(self):
        with patch("wanda.memory.MAX_MEMORIES_PER_OWNER", 2):
            self.store.save(self.owner, "Synthetic old one", "temporary", approved=True, expires_at=self.now + 1)
            self.store.save(self.owner, "Synthetic old two", "temporary", approved=True, expires_at=self.now + 1)
            archive = self.archive(self.record("Synthetic restored one"), self.record("Synthetic restored two"))
            with patch("wanda.memory.time.time", return_value=self.now + 2):
                before = self.snapshot()
                preview = self.store.restore_preview(self.owner, archive)
                self.assertEqual((preview["existing"], preview["available"], preview["exceeds_capacity"]), (0, 2, False))
                self.assertEqual(before, self.snapshot())
                result = self.store.restore(self.owner, archive, approved=True)
                self.assertEqual(result["restored"], 2)
                records = self.store.list_memories(self.owner)
                self.assertEqual({row["text"] for row in records}, {"Synthetic restored one", "Synthetic restored two"})
                self.assertEqual(len(self.snapshot()["memories"]), 2)

    def test_invalid_later_record_rolls_back_whole_archive(self):
        first, second = self.record("Synthetic valid first"), self.record("Synthetic invalid second")
        second["category"] = "unsupported"
        before = self.snapshot()
        with self.assertRaises(ValueError):
            self.store.restore(self.owner, self.archive(first, second), approved=True)
        self.assertEqual(before, self.snapshot())

    def test_database_failure_after_first_insert_rolls_back_every_insert(self):
        records = [self.record("Synthetic first insert"), self.record("FAIL_SYNTHETIC_INSERT")]
        self.store._connection.execute("""
            CREATE TEMP TRIGGER fail_second_restore BEFORE INSERT ON memories
            WHEN NEW.text = 'FAIL_SYNTHETIC_INSERT'
            BEGIN SELECT RAISE(ABORT, 'synthetic database failure'); END
        """)
        before = self.snapshot()
        with self.assertRaises(sqlite3.IntegrityError):
            self.store.restore(self.owner, self.archive(*records), approved=True)
        self.assertEqual(before, self.snapshot())
        self.store._connection.execute("DROP TRIGGER fail_second_restore")
        self.assertEqual(self.store.restore(self.owner, self.archive(*records), approved=True)["restored"], 2)

    def test_failed_later_insert_rolls_back_expired_memory_pruning_too(self):
        self.store.save(self.owner, "Synthetic expired local note", "temporary", approved=True, expires_at=self.now + 1)
        self.store.set_grant(self.owner, "openai", "temporary", True, expires_at=self.now + 1)
        self.store._connection.execute("""
            CREATE TEMP TRIGGER fail_after_prune BEFORE INSERT ON memories
            WHEN NEW.text = 'FAIL_SYNTHETIC_RESTORE_AFTER_PRUNE'
            BEGIN SELECT RAISE(ABORT, 'synthetic failure after pruning'); END
        """)
        archive = self.archive(self.record("Synthetic first restored note"), self.record("FAIL_SYNTHETIC_RESTORE_AFTER_PRUNE"))
        with patch("wanda.memory.time.time", return_value=self.now + 2):
            before = self.snapshot()
            with self.assertRaises(sqlite3.IntegrityError):
                self.store.restore(self.owner, archive, approved=True)
            self.assertEqual(before, self.snapshot())
            self.store._connection.execute("DROP TRIGGER fail_after_prune")
            self.assertEqual(self.store.restore(self.owner, archive, approved=True)["restored"], 2)
            after = self.snapshot()
            self.assertNotIn(before["memories"][0], after["memories"])
            self.assertEqual(before["owners"], after["owners"])
            self.assertEqual(before["disclosure_grants"], after["disclosure_grants"])

    def test_concurrent_restore_connections_do_not_duplicate_or_exceed_capacity(self):
        other_store = MemoryStore(self.path)
        archive = self.archive(self.record("Synthetic concurrent one"), self.record("Synthetic concurrent two"))
        start = threading.Barrier(2)

        def restore(store):
            start.wait(timeout=5)
            return store.restore(self.owner, archive, approved=True)

        try:
            with patch("wanda.memory.MAX_MEMORIES_PER_OWNER", 2):
                with ThreadPoolExecutor(max_workers=2) as pool:
                    results = list(pool.map(restore, [self.store, other_store]))
            self.assertEqual(sorted(result["restored"] for result in results), [0, 2])
            self.assertEqual(len(self.store.list_memories(self.owner)), 2)
        finally:
            other_store.close()

    def test_missing_extra_format_and_version_fields_are_rejected(self):
        for field, value in (("format", "unknown"), ("version", 2), ("version", True), ("version", 1.0), ("version", "1")):
            with self.subTest(field=field, value=value):
                archive = self.archive(self.record())
                archive[field] = value
                with self.assertRaises(ValueError):
                    self.store.restore_preview(self.owner, archive)
        for field in ("format", "version", "created_at", "memories"):
            archive = self.archive(self.record())
            del archive[field]
            with self.subTest(missing=field), self.assertRaises(ValueError):
                self.store.restore(self.owner, archive, approved=True)
        for field in ("id", "text", "category", "created_at", "expires_at"):
            archive = self.archive(self.record())
            del archive["memories"][0][field]
            with self.subTest(missing_record=field), self.assertRaises(ValueError):
                self.store.restore(self.owner, archive, approved=True)
        self.assertEqual(self.store.list_memories(self.owner), [])

    def test_nonfinite_boolean_and_huge_times_rejected_in_every_timestamp(self):
        invalid = (math.nan, math.inf, -math.inf, 1e9999, 10 ** 1000, True, False, 0, -1, "tomorrow", None)
        for key in ("archive", "created_at", "expires_at"):
            for value in invalid:
                if key == "expires_at" and value is None:
                    continue
                archive = self.archive(self.record())
                target = archive if key == "archive" else archive["memories"][0]
                target["created_at" if key == "archive" else key] = value
                with self.subTest(key=key, value=str(value)[:25]), self.assertRaises(ValueError):
                    self.store.restore(self.owner, archive, approved=True)
        self.assertEqual(self.store.list_memories(self.owner), [])

    def test_clock_rollback_preserves_creation_later_than_backup_time(self):
        original = self.store.save(self.owner, "Synthetic project before clock correction", "project", approved=True)
        with patch("wanda.memory.time.time", return_value=self.now - 60):
            archive = self.store.backup(self.owner)
            self.assertGreater(archive["memories"][0]["created_at"], archive["created_at"])
            self.assertEqual(self.store.restore_preview(self.other, archive)["restorable"], 1)
            self.assertEqual(self.store.restore(self.other, archive, approved=True)["restored"], 1)
            imported = self.store.list_memories(self.other)[0]
            self.assertEqual(imported["created_at"], original["created_at"])
            self.assertEqual(imported["text"], original["text"])

    def test_clock_rollback_edit_preserves_expiration_before_original_creation(self):
        original = self.store.save(self.owner, "Synthetic original project", "project", approved=True)
        with patch("wanda.memory.time.time", return_value=self.now - 100):
            edited = self.store.update(self.owner, original["id"], "Synthetic temporary project", "temporary", approved=True, expires_at=self.now - 50)
            self.assertLess(edited["expires_at"], edited["created_at"])
            archive = self.store.backup(self.owner)
            self.assertEqual(self.store.restore(self.other, archive, approved=True)["restored"], 1)
            imported = self.store.list_memories(self.other)[0]
            self.assertEqual(imported["created_at"], edited["created_at"])
            self.assertEqual(imported["expires_at"], edited["expires_at"])
        with patch("wanda.memory.time.time", return_value=self.now - 50):
            preview = self.store.restore_preview(self.other, archive)
            self.assertEqual((preview["restorable"], preview["skipped_expired"]), (0, 1))

    def test_reused_ids_with_conflicting_data_are_rejected(self):
        first = self.record("Synthetic original ID")
        second = dict(first, text="Synthetic conflicting ID")
        with self.assertRaises(ValueError):
            self.store.restore(self.owner, self.archive(first, second), approved=True)

    def test_control_characters_invalid_identifiers_and_oversized_text_are_rejected(self):
        bad_text = ("", " ", " synthetic whitespace ", "\x00synthetic", "synthetic\rnote",
                    "synthetic\x7fnote", "synthetic\x85note", "synthetic\ud800", "x" * 1001)
        for text in bad_text:
            with self.subTest(text=repr(text)[:30]), self.assertRaises(ValueError):
                self.store.restore(self.owner, self.archive(self.record(text)), approved=True)
        for identifier in ("not-a-uuid", "' OR 1=1 --", None, 5, str(uuid.uuid4()).upper()):
            record = self.record()
            record["id"] = identifier
            with self.subTest(identifier=identifier), self.assertRaises(ValueError):
                self.store.restore_preview(self.owner, self.archive(record))
        self.assertEqual(self.store.list_memories(self.owner), [])

    def test_valid_unicode_multiline_and_sql_like_text_survive_round_trip(self):
        text = "Synthetic café project\nSecond line\t'); DROP TABLE memories; --"
        saved = self.store.save(self.owner, text, "project", approved=True)
        archive = self.store.backup(self.owner)
        self.store.restore(self.other, archive, approved=True)
        self.assertEqual(self.store.list_memories(self.other)[0]["text"], saved["text"])
        self.assertEqual(len(self.store.list_memories(self.owner)), 1)

    def test_record_count_plaintext_size_and_invalid_containers_are_bounded(self):
        archive = self.archive(*[self.record() for _ in range(1001)])
        with self.assertRaises(ValueError):
            self.store.restore_preview(self.owner, archive)
        with patch("wanda.memory.MAX_BACKUP_BYTES", 32):
            with self.assertRaises(ValueError):
                self.store.restore(self.owner, self.archive(self.record()), approved=True)
        for payload in (None, [], "{}", 1, True):
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                self.store.restore_preview(self.owner, payload)
        for records in (None, {}, "[]", [None], [[]]):
            archive = self.archive()
            archive["memories"] = records
            with self.subTest(records=records), self.assertRaises(ValueError):
                self.store.restore_preview(self.owner, archive)

    def test_errors_and_preview_do_not_echo_private_archive_text(self):
        text = "PRIVATE_SYNTHETIC_SENTINEL"
        archive = self.archive(self.record(text))
        preview = self.store.restore_preview(self.owner, archive)
        self.assertNotIn(text, json.dumps(preview))
        for field, value in (("category", text), ("id", text), ("created_at", text), ("text", text + "\x00")):
            archive = self.archive(self.record(text))
            archive["memories"][0][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError) as caught:
                self.store.restore(self.owner, archive, approved=True)
            self.assertNotIn(text, str(caught.exception))

    def test_empty_archive_is_safe_and_backup_of_unknown_owner_does_not_enroll_it(self):
        before = self.snapshot()
        archive = self.store.backup("unknown-owner")
        self.assertEqual(archive["memories"], [])
        self.assertEqual(self.store.restore_preview("unknown-owner", archive)["restorable"], 0)
        self.assertEqual(before, self.snapshot())
        result = self.store.restore(self.owner, archive, approved=True)
        self.assertEqual(result["restored"], 0)
        self.assertEqual(before, self.snapshot())


if __name__ == "__main__":
    unittest.main()
