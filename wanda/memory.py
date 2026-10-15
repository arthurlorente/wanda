"""Local opt-in memory and explicit, scoped cloud disclosure permissions.

This module never opens a network connection, archives chat transcripts, or treats
conversation text as authorization. Callers must authenticate owner identifiers
and obtain ``approved=True`` only from a separate explicit review action.
"""

from contextlib import contextmanager
import json
import math
import os
from pathlib import Path
import re
import sqlite3
import stat
import threading
import time
import uuid


CATEGORIES = frozenset({"preference", "project", "temporary", "sensitive"})
MAX_MEMORY_CHARS = 1000
MAX_INPUT_CHARS = 8000
MAX_DISCLOSURE_ITEMS = 8
MAX_DISCLOSURE_CHARS = 4000
MAX_MEMORIES_PER_OWNER = 1000
MAX_BACKUP_BYTES = 8 * 1024 * 1024
BACKUP_FORMAT = "wanda-memory-backup"
BACKUP_VERSION = 1
TEMPORARY_TTL_SECONDS = 24 * 60 * 60

# Full utterance matches only. Never extract a safe-looking substring from a
# sentence that also includes a diagnosis, third party, uncertainty, or address.
_COLORS = {
    "blue": "blue", "red": "red", "green": "green", "yellow": "yellow",
    "purple": "purple", "orange": "orange", "pink": "pink", "black": "black",
    "white": "white", "azul": "blue", "vermelho": "red", "verde": "green",
    "amarelo": "yellow", "roxo": "purple", "laranja": "orange", "rosa": "pink",
    "preto": "black", "branco": "white", "rojo": "red", "amarillo": "yellow",
    "morado": "purple", "naranja": "orange", "negro": "black", "blanco": "white",
}
_DRINKS = {
    "tea": "tea", "coffee": "coffee", "water": "water", "chá": "tea",
    "café": "coffee", "água": "water", "té": "tea", "agua": "water",
}
_COLOR_PATTERN = re.compile(
    r"(?:my favou?rite colou?r is|minha cor favorita é|mi color favorito es) "
    r"(" + "|".join(_COLORS) + r")\.?", re.IGNORECASE
)
_DRINK_PATTERN = re.compile(
    r"(?:i prefer|i like|prefiro|eu prefiro|prefiero) "
    r"(" + "|".join(_DRINKS) + r")\.?", re.IGNORECASE
)
_PERSONAL_CUES = re.compile(
    r"\b(my|mine|i|me|remember|prefer|likes?|meu|minha|meus|minhas|eu|lembrar|"
    r"lembre|prefiro|mi|mis|yo|recuerda|recordar|prefiero|family|partner|friend|"
    r"wife|husband|child|sister|brother|mom|dad|mother|father|neighbor|vizinho|"
    r"amig[oa]|esposa|marido|filh[oa]|madre|padre|vecin[oa])\b", re.IGNORECASE
)
_SENSITIVE_CUES = re.compile(
    r"\b(health|medical|diagnos\w*|cancer|diabet\w*|allerg\w*|medic\w*|"
    r"pregnan\w*|depress\w*|anxiety|therapy|password|secret|token|api.?key|"
    r"address|email|phone|income|salary|bank|account|credit|debt|ssn|passport|"
    r"social.security|religion|politic\w*|sex\w*|partner|wife|husband|child|"
    r"family|friend|sister|brother|mother|father|mom|dad|neighbor|"
    r"saúde|doença|doenca|senha|endereço|endereco|telefone|salário|salario|"
    r"conta|banco|família|familia|amig[oa]|esposa|marido|filh[oa]|"
    r"salud|enfermedad|contraseña|dirección|direccion|teléfono|"
    r"madre|padre|vecin[oa])\b|@|\d{3}", re.IGNORECASE
)


def _ordinary_preference(text):
    """Return a closed-vocabulary canonical fact, or None for any uncertainty."""
    match = _COLOR_PATTERN.fullmatch(text)
    if match:
        color = _COLORS.get(match.group(1).lower())
        return "My favorite color is " + color + "." if color else None
    match = _DRINK_PATTERN.fullmatch(text)
    if match:
        drink = _DRINKS.get(match.group(1).lower())
        return "I prefer " + drink + "." if drink else None
    return None


def _owner(value):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:@-]{0,127}", value):
        raise ValueError("Invalid owner identifier.")
    return value


def _provider(value):
    if not isinstance(value, str) or not re.fullmatch(r"[a-z][a-z0-9_-]{0,63}", value):
        raise ValueError("Invalid provider identifier.")
    return value


def _category(value):
    if not isinstance(value, str) or value not in CATEGORIES:
        raise ValueError("Invalid memory category.")
    return value


def _boolean(value):
    if type(value) is not bool:
        raise ValueError("Expected a boolean choice.")
    return value


def _text(value, limit=MAX_MEMORY_CHARS):
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise ValueError("Memory text is empty or too long.")
    if any((ord(char) < 32 and char not in "\n\t") or 127 <= ord(char) <= 159 for char in value):
        raise ValueError("Memory text contains unsupported control characters.")
    # Leading/trailing whitespace is not meaningful. Internal text is never
    # silently truncated or rewritten for an explicitly reviewed manual save.
    return value.strip()


def _identifier(value):
    if not isinstance(value, str):
        raise ValueError("Invalid record identifier.")
    try:
        parsed = uuid.UUID(value)
    except (ValueError, AttributeError):
        raise ValueError("Invalid record identifier.") from None
    if str(parsed) != value:
        raise ValueError("Invalid record identifier.")
    return value


def _expiry(value, now, temporary=False):
    if value is None:
        return now + TEMPORARY_TTL_SECONDS if temporary else None
    if type(value) not in (int, float) or not math.isfinite(value) or value <= now:
        raise ValueError("Expiration must be a future Unix timestamp.")
    return float(value)


def _disclosure_categories(text, category):
    # Storage approval is NOT approval to disclose. An arbitrary sentence labeled
    # "preference" or "project" cannot evade the unknown/sensitive boundary.
    categories = {category}
    if _ordinary_preference(text) is None:
        categories.add("sensitive")
    return sorted(categories)


def _backup_timestamp(value):
    """Validate serialized time without exposing the value in an error."""
    if type(value) not in (int, float):
        raise ValueError("Backup timestamps must be finite positive Unix seconds.")
    try:
        finite = math.isfinite(value)
    except OverflowError:
        finite = False
    if not finite or value <= 0:
        raise ValueError("Backup timestamps must be finite positive Unix seconds.")
    return float(value)


def _validate_backup(payload):
    """Return a bounded independent copy of an untrusted recovery archive.

    This validates data, not encryption/authenticity. The transport must decrypt
    and authenticate the archive before calling the memory recovery interface.
    Only approved restoration, never an archive flag, permits storing its text.
    """
    fields = {"format", "version", "created_at", "memories"}
    if type(payload) is not dict or set(payload) != fields:
        raise ValueError("Backup has missing or unsupported fields.")
    if payload["format"] != BACKUP_FORMAT or type(payload["version"]) is not int or payload["version"] != BACKUP_VERSION:
        raise ValueError("Unsupported memory backup format or version.")
    archived_at = _backup_timestamp(payload["created_at"])
    source = payload["memories"]
    if type(source) is not list or len(source) > MAX_MEMORIES_PER_OWNER:
        raise ValueError("Backup must contain at most 1000 memory records.")
    record_fields = {"id", "text", "category", "created_at", "expires_at"}
    records, original_ids = [], {}
    for record in source:
        if type(record) is not dict or set(record) != record_fields:
            raise ValueError("Backup memory has missing or unsupported fields.")
        identifier = _identifier(record["id"])
        text, category = _text(record["text"]), _category(record["category"])
        if text != record["text"]:
            raise ValueError("Backup memory text must not contain surrounding whitespace.")
        try:
            text.encode("utf-8")
        except UnicodeError:
            raise ValueError("Backup memory contains unsupported text.") from None
        created = _backup_timestamp(record["created_at"])
        expiry = None if record["expires_at"] is None else _backup_timestamp(record["expires_at"])
        # Wall clocks can move backward between creation, editing and backup.
        # Preserve valid absolute timestamps rather than imposing chronology
        # that could make Wanda's own previously saved records unrecoverable.
        clean = {"id": identifier, "text": text, "category": category,
                 "created_at": created, "expires_at": expiry}
        previous = original_ids.get(identifier)
        if previous is not None and previous != clean:
            raise ValueError("Backup reuses a record identifier with inconsistent data.")
        original_ids[identifier] = clean
        records.append(clean)
    validated = {"format": BACKUP_FORMAT, "version": BACKUP_VERSION,
                 "created_at": archived_at, "memories": records}
    # No uncontrolled nested objects remain at this point. Bound the exact UTF-8
    # plaintext that the encryption layer is permitted to serialize.
    if len(json.dumps(validated, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")) > MAX_BACKUP_BYTES:
        raise ValueError("Backup exceeds the maximum size.")
    return validated


class MemoryStore:
    """SQLite store for authenticated owners; safe for threaded HTTP handlers.

    Inspecting/exporting/deleting remains possible when disabled. Saving,
    extraction, and disclosure do not. Use recall() for atomic consented local
    recall; list_memories() is the management/review interface.
    """

    def __init__(self, path):
        self._lock = threading.RLock()
        self._closed = False
        self.path = self._prepare_path(path)
        self._connection = sqlite3.connect(
            str(self.path), timeout=10, isolation_level=None, check_same_thread=False
        )
        self._connection.row_factory = sqlite3.Row
        try:
            self._connection.execute("PRAGMA foreign_keys = ON")
            self._connection.execute("PRAGMA secure_delete = ON")
            self._connection.execute("PRAGMA journal_mode = DELETE")
            self._connection.execute("PRAGMA synchronous = FULL")
            self._connection.execute("PRAGMA trusted_schema = OFF")
            self._migrate()
        except Exception:
            self._connection.close()
            raise

    @staticmethod
    def _prepare_path(path):
        if not isinstance(path, (str, os.PathLike)) or str(path) == ":memory:":
            raise ValueError("Provide a private database path outside the repository.")
        supplied = Path(path).expanduser()
        if supplied.is_symlink():
            raise ValueError("Database file must not be a symbolic link.")
        resolved = supplied.resolve()
        repo_root = Path(__file__).resolve().parent.parent
        if resolved == repo_root or repo_root in resolved.parents:
            raise ValueError("Private memory must be stored outside the repository.")
        resolved.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        flags = os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0)
        descriptor = os.open(str(resolved), flags, 0o600)
        try:
            if not stat.S_ISREG(os.fstat(descriptor).st_mode):
                raise ValueError("Database must be a regular private file.")
            if hasattr(os, "fchmod"):
                os.fchmod(descriptor, 0o600)
        finally:
            os.close(descriptor)
        return resolved

    @contextmanager
    def _transaction(self):
        with self._lock:
            if self._closed:
                raise ValueError("Memory store is closed.")
            self._connection.execute("BEGIN IMMEDIATE")
            try:
                yield
                self._connection.commit()
            except BaseException:
                self._connection.rollback()
                raise

    def _migrate(self):
        with self._transaction():
            version = self._connection.execute("PRAGMA user_version").fetchone()[0]
            if version not in (0, 1):
                raise ValueError("Unsupported memory database version.")
            if version == 0:
                self._connection.execute("""
                    CREATE TABLE owners (
                        owner TEXT PRIMARY KEY,
                        enabled INTEGER NOT NULL DEFAULT 0 CHECK(enabled IN (0, 1))
                    )
                """)
                self._connection.execute("""
                    CREATE TABLE memories (
                        id TEXT PRIMARY KEY,
                        owner TEXT NOT NULL REFERENCES owners(owner),
                        text TEXT NOT NULL,
                        category TEXT NOT NULL CHECK(category IN
                            ('preference', 'project', 'temporary', 'sensitive')),
                        created_at REAL NOT NULL,
                        expires_at REAL
                    )
                """)
                self._connection.execute("CREATE INDEX memories_owner ON memories(owner)")
                self._connection.execute("""
                    CREATE TABLE disclosure_grants (
                        id TEXT PRIMARY KEY,
                        owner TEXT NOT NULL REFERENCES owners(owner),
                        provider TEXT NOT NULL,
                        category TEXT NOT NULL CHECK(category IN
                            ('preference', 'project', 'temporary', 'sensitive')),
                        allowed INTEGER NOT NULL CHECK(allowed IN (0, 1)),
                        one_time INTEGER NOT NULL CHECK(one_time IN (0, 1)),
                        created_at REAL NOT NULL,
                        expires_at REAL,
                        consumed_at REAL,
                        UNIQUE(owner, provider, category)
                    )
                """)
                self._connection.execute("PRAGMA user_version = 1")

    def _enabled(self, owner):
        row = self._connection.execute(
            "SELECT enabled FROM owners WHERE owner = ?", (owner,)
        ).fetchone()
        return bool(row and row["enabled"])

    def _require_enabled(self, owner):
        if not self._enabled(owner):
            raise PermissionError("Memory is disabled. Enable it in privacy settings first.")

    def _prune(self, owner, now):
        self._connection.execute(
            "DELETE FROM memories WHERE owner = ? AND expires_at IS NOT NULL AND expires_at <= ?",
            (owner, now),
        )
        self._connection.execute(
            "DELETE FROM disclosure_grants WHERE owner = ? AND expires_at IS NOT NULL AND expires_at <= ?",
            (owner, now),
        )

    @staticmethod
    def _memory_record(row):
        return {
            "id": row["id"], "text": row["text"], "category": row["category"],
            "created_at": row["created_at"], "expires_at": row["expires_at"],
            "disclosure_categories": _disclosure_categories(row["text"], row["category"]),
        }

    @staticmethod
    def _grant_record(row):
        return {
            "id": row["id"], "provider": row["provider"], "category": row["category"],
            "allowed": bool(row["allowed"]), "one_time": bool(row["one_time"]),
            "created_at": row["created_at"], "expires_at": row["expires_at"],
            "consumed_at": row["consumed_at"],
        }

    def _rows(self, owner):
        return self._connection.execute(
            "SELECT id, text, category, created_at, expires_at FROM memories "
            "WHERE owner = ? ORDER BY created_at, id", (owner,)
        ).fetchall()

    def is_enabled(self, owner):
        owner = _owner(owner)
        with self._transaction():
            return self._enabled(owner)

    def set_enabled(self, owner, enabled):
        owner, enabled = _owner(owner), _boolean(enabled)
        with self._transaction():
            self._connection.execute(
                "INSERT INTO owners(owner, enabled) VALUES (?, ?) "
                "ON CONFLICT(owner) DO UPDATE SET enabled = excluded.enabled",
                (owner, int(enabled)),
            )
        return enabled

    def list_memories(self, owner):
        owner = _owner(owner)
        with self._transaction():
            self._prune(owner, time.time())
            return [self._memory_record(row) for row in self._rows(owner)]

    def recall(self, owner):
        """Return bounded local recall with consent and read in one transaction.

        The management list remains usable while disabled, so consumers must not
        perform separate is_enabled()/list_memories() calls for conversation.
        This method performs no cloud disclosure and consumes no cloud grant.
        """
        owner = _owner(owner)
        with self._transaction():
            if not self._enabled(owner):
                return []
            self._prune(owner, time.time())
            selected, characters = [], 0
            for row in self._rows(owner):
                if len(selected) >= MAX_DISCLOSURE_ITEMS:
                    break
                if characters + len(row["text"]) > MAX_DISCLOSURE_CHARS:
                    break
                selected.append(self._memory_record(row))
                characters += len(row["text"])
            return selected

    def _validate_save(self, text, category, approved, expires_at, now):
        text, category = _text(text), _category(category)
        approved = _boolean(approved)
        if not approved and (category != "preference" or _ordinary_preference(text) is None):
            raise PermissionError("This memory requires explicit approval in the review controls.")
        return text, category, _expiry(expires_at, now, category == "temporary")

    def save(self, owner, text, category="preference", approved=False, expires_at=None):
        owner = _owner(owner)
        now = time.time()
        text, category, expiry = self._validate_save(text, category, approved, expires_at, now)
        with self._transaction():
            self._require_enabled(owner)
            self._prune(owner, now)
            count = self._connection.execute(
                "SELECT count(*) FROM memories WHERE owner = ?", (owner,)
            ).fetchone()[0]
            if count >= MAX_MEMORIES_PER_OWNER:
                raise ValueError("Memory capacity reached; delete some items before saving more.")
            identifier = str(uuid.uuid4())
            self._connection.execute(
                "INSERT INTO memories(id, owner, text, category, created_at, expires_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (identifier, owner, text, category, now, expiry),
            )
            return self._memory_record({
                "id": identifier, "text": text, "category": category,
                "created_at": now, "expires_at": expiry,
            })

    def update(self, owner, id, text, category, approved=False, expires_at=None):
        owner, identifier = _owner(owner), _identifier(id)
        now = time.time()
        text, category, expiry = self._validate_save(text, category, approved, expires_at, now)
        with self._transaction():
            self._require_enabled(owner)
            self._prune(owner, now)
            row = self._connection.execute(
                "SELECT created_at FROM memories WHERE owner = ? AND id = ?", (owner, identifier)
            ).fetchone()
            if row is None:
                raise PermissionError("Memory is unavailable for this owner.")
            self._connection.execute(
                "UPDATE memories SET text = ?, category = ?, expires_at = ? WHERE owner = ? AND id = ?",
                (text, category, expiry, owner, identifier),
            )
            return self._memory_record({
                "id": identifier, "text": text, "category": category,
                "created_at": row["created_at"], "expires_at": expiry,
            })

    def delete(self, owner, id):
        owner, identifier = _owner(owner), _identifier(id)
        with self._transaction():
            cursor = self._connection.execute(
                "DELETE FROM memories WHERE owner = ? AND id = ?", (owner, identifier)
            )
            return cursor.rowcount == 1

    def clear(self, owner):
        owner = _owner(owner)
        with self._transaction():
            cursor = self._connection.execute("DELETE FROM memories WHERE owner = ?", (owner,))
            return cursor.rowcount

    def export(self, owner):
        owner = _owner(owner)
        with self._transaction():
            now = time.time()
            self._prune(owner, now)
            grants = self._connection.execute(
                "SELECT * FROM disclosure_grants WHERE owner = ? ORDER BY created_at, id", (owner,)
            ).fetchall()
            return {
                "version": 1, "exported_at": now, "enabled": self._enabled(owner),
                "memories": [self._memory_record(row) for row in self._rows(owner)],
                "grants": [self._grant_record(row) for row in grants],
            }

    def backup(self, owner):
        """Snapshot this owner's unexpired facts for local encrypted recovery.

        The result exists in memory only. It deliberately excludes identity,
        credentials, opt-in state and grants. The caller encrypts before saving.
        This management action remains available when capture is disabled.
        """
        owner = _owner(owner)
        with self._transaction():
            now = time.time()
            rows = self._connection.execute(
                "SELECT id, text, category, created_at, expires_at FROM memories "
                "WHERE owner = ? AND (expires_at IS NULL OR expires_at > ?) "
                "ORDER BY created_at, id", (owner, now)
            ).fetchall()
            payload = {"format": BACKUP_FORMAT, "version": BACKUP_VERSION,
                       "created_at": now, "memories": [dict(row) for row in rows]}
            return _validate_backup(payload)

    def _restore_plan(self, owner, payload, now):
        archive = _validate_backup(payload)
        existing = self._connection.execute(
            "SELECT id, text, category, created_at, expires_at FROM memories "
            "WHERE owner = ? AND (expires_at IS NULL OR expires_at > ?)",
            (owner, now),
        ).fetchall()
        seen = {(row["text"], row["category"], row["expires_at"]) for row in existing}
        selected, expired, duplicates = [], 0, 0
        for record in archive["memories"]:
            if record["expires_at"] is not None and record["expires_at"] <= now:
                expired += 1
                continue
            identity = (record["text"], record["category"], record["expires_at"])
            if identity in seen:
                duplicates += 1
                continue
            selected.append(record)
            seen.add(identity)
        available = max(0, MAX_MEMORIES_PER_OWNER - len(existing))
        counts = {
            "total": len(archive["memories"]), "restorable": len(selected),
            "skipped_expired": expired, "duplicates": duplicates,
            "existing": len(existing), "capacity": MAX_MEMORIES_PER_OWNER,
            "available": available, "exceeds_capacity": len(selected) > available,
        }
        return selected, counts

    def restore_preview(self, owner, payload):
        """Validate and count a proposed merge without changing any stored row."""
        owner = _owner(owner)
        with self._transaction():
            _, counts = self._restore_plan(owner, payload, time.time())
            return counts

    def restore(self, owner, payload, approved=False):
        """Explicitly approved, atomic merge into the currently enabled owner.

        Revalidates on every call; preview is not authorization. No archive may
        enable memory, restore permissions, replace live data, or select an
        owner. Expired memories of this owner are pruned as normal retention
        maintenance in the same transaction. Imported records receive new IDs.
        """
        owner = _owner(owner)
        if not _boolean(approved):
            raise PermissionError("Restoring memories requires explicit approval.")
        with self._transaction():
            self._require_enabled(owner)
            now = time.time()
            selected, counts = self._restore_plan(owner, payload, now)
            if counts["exceeds_capacity"]:
                raise ValueError("Restore exceeds memory capacity. Review existing memories first.")
            # Do not use _prune(): restoring memory must not change any grant.
            # This retention maintenance rolls back if any later insert fails.
            self._connection.execute(
                "DELETE FROM memories WHERE owner = ? AND expires_at IS NOT NULL AND expires_at <= ?",
                (owner, now),
            )
            for record in selected:
                self._connection.execute(
                    "INSERT INTO memories(id, owner, text, category, created_at, expires_at) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (str(uuid.uuid4()), owner, record["text"], record["category"],
                     record["created_at"], record["expires_at"]),
                )
            return {**counts, "restored": len(selected)}

    def extract(self, owner, text):
        owner, text = _owner(owner), _text(text, MAX_INPUT_CHARS)
        with self._transaction():
            if not self._enabled(owner):
                return {"saved": [], "candidates": []}
            self._prune(owner, time.time())
            ordinary = _ordinary_preference(text)
            if ordinary is not None:
                # Do not call save() here: this extraction and its consent check
                # must stay inside one transaction, including cross-process use.
                existing = self._connection.execute(
                    "SELECT id FROM memories WHERE owner = ? AND text = ? AND category = 'preference'",
                    (owner, ordinary),
                ).fetchone()
                if existing:
                    return {"saved": [], "candidates": []}
                count = self._connection.execute(
                    "SELECT count(*) FROM memories WHERE owner = ?", (owner,)
                ).fetchone()[0]
                if count >= MAX_MEMORIES_PER_OWNER:
                    return {"saved": [], "candidates": []}
                identifier, now = str(uuid.uuid4()), time.time()
                self._connection.execute(
                    "INSERT INTO memories(id, owner, text, category, created_at, expires_at) "
                    "VALUES (?, ?, ?, 'preference', ?, NULL)", (identifier, owner, ordinary, now),
                )
                return {"saved": [self._memory_record({
                    "id": identifier, "text": ordinary, "category": "preference",
                    "created_at": now, "expires_at": None,
                })], "candidates": []}
            # Pending candidates exist only in this return value / browser tab.
            # No transcript, approval request, or denied fact is written to disk.
            if len(text) <= MAX_MEMORY_CHARS and (_PERSONAL_CUES.search(text) or _SENSITIVE_CUES.search(text)):
                return {"saved": [], "candidates": [{
                    "text": text, "category": "sensitive", "expires_at": None,
                    "reason": "This may be personal, sensitive, or uncertain. Review before saving locally.",
                    "disclosure_categories": ["sensitive"],
                }]}
            return {"saved": [], "candidates": []}

    def list_grants(self, owner):
        owner = _owner(owner)
        with self._transaction():
            self._prune(owner, time.time())
            rows = self._connection.execute(
                "SELECT * FROM disclosure_grants WHERE owner = ? ORDER BY created_at, id", (owner,)
            ).fetchall()
            return [self._grant_record(row) for row in rows]

    def set_grant(self, owner, provider, category, allowed, one_time=False, expires_at=None):
        owner, provider, category = _owner(owner), _provider(provider), _category(category)
        allowed, one_time = _boolean(allowed), _boolean(one_time)
        now = time.time()
        expiry = _expiry(expires_at, now)
        with self._transaction():
            if allowed:
                self._require_enabled(owner)
            self._connection.execute(
                "INSERT OR IGNORE INTO owners(owner, enabled) VALUES (?, 0)", (owner,)
            )
            identifier = str(uuid.uuid4())
            self._connection.execute(
                "DELETE FROM disclosure_grants WHERE owner = ? AND provider = ? AND category = ?",
                (owner, provider, category),
            )
            self._connection.execute(
                "INSERT INTO disclosure_grants(id, owner, provider, category, allowed, one_time, "
                "created_at, expires_at, consumed_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL)",
                (identifier, owner, provider, category, int(allowed), int(one_time), now, expiry),
            )
            return self._grant_record({
                "id": identifier, "provider": provider, "category": category, "allowed": allowed,
                "one_time": one_time, "created_at": now, "expires_at": expiry, "consumed_at": None,
            })

    def revoke_grant(self, owner, id):
        owner, identifier = _owner(owner), _identifier(id)
        with self._transaction():
            cursor = self._connection.execute(
                "DELETE FROM disclosure_grants WHERE owner = ? AND id = ?", (owner, identifier)
            )
            return cursor.rowcount == 1

    def disclose(self, owner, provider, memory_ids):
        owner, provider = _owner(owner), _provider(provider)
        if not isinstance(memory_ids, list) or len(memory_ids) > MAX_DISCLOSURE_ITEMS:
            raise ValueError("Select at most eight memories for disclosure.")
        identifiers = [_identifier(value) for value in memory_ids]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("Memory selection contains duplicates.")
        with self._transaction():
            self._require_enabled(owner)
            now = time.time()
            self._prune(owner, now)
            selected, categories = [], set()
            for identifier in identifiers:
                row = self._connection.execute(
                    "SELECT id, text, category FROM memories WHERE owner = ? AND id = ?", (owner, identifier)
                ).fetchone()
                if row is None:
                    raise PermissionError("Selected memory is unavailable for this owner.")
                selected.append({"id": row["id"], "text": row["text"], "category": row["category"]})
                categories.update(_disclosure_categories(row["text"], row["category"]))
            if sum(len(record["text"]) for record in selected) > MAX_DISCLOSURE_CHARS:
                raise ValueError("Selected memory context exceeds the disclosure size limit.")
            grants = []
            for category in sorted(categories):
                grant = self._connection.execute(
                    "SELECT id, allowed, one_time, consumed_at FROM disclosure_grants "
                    "WHERE owner = ? AND provider = ? AND category = ?", (owner, provider, category)
                ).fetchone()
                if grant is None or not grant["allowed"] or grant["consumed_at"] is not None:
                    raise PermissionError("Cloud disclosure is not authorized for every selected category.")
                grants.append(grant)
            # Every item and category passed before consuming any permission.
            # BEGIN IMMEDIATE serializes other connections as well as HTTP threads.
            for grant in grants:
                if grant["one_time"]:
                    self._connection.execute(
                        "UPDATE disclosure_grants SET allowed = 0, consumed_at = ? "
                        "WHERE owner = ? AND id = ?", (now, owner, grant["id"])
                    )
            return selected

    def close(self):
        with self._lock:
            if not self._closed:
                self._connection.close()
                self._closed = True
