# V0 local memory and privacy

**Status: V0 implementation and local recovery accepted and merged, 2026-10-15 (D-053).** This is the
small, locally testable memory foundation for [Issue #7](https://github.com/arthurlorente/wanda/issues/7),
[D-028–D-043](DECISION_LOG.md), and requirements R-10, R-18–R-22 and R-28–R-30.
The owner has approved password-encrypted local backup/restore and requires all
saved memory to remain local. It is not full household identity, semantic memory,
or a claim that cloud voice is private. See [ADR 0008](adr/0008-v0-portable-stack.md)
and [the backup decision](adr/0009-encrypted-memory-backup.md).

## What you can try

1. Start Wanda using the [morning handoff](MORNING_HANDOFF.md).
2. Leave memory disabled and type `My favorite color is blue.` Nothing is saved.
3. Enable local memory in its privacy controls. Type the same sentence. Inspect
   the new saved preference in the memory panel.
4. Type `My project is a tiny synthetic garden.` It becomes a review candidate,
   not a stored fact. Use the separate review control to save it deliberately.
5. Edit, export, or delete a saved item. Restart Wanda to check that undeleted
   memories and your enable/disable choice persist.
6. Disable memory. New capture and conversational recall stop, and the backend
   refuses disclosure. You can still inspect, export and delete your records.
7. Create a password-encrypted local backup. Preview it in the restore controls,
   then explicitly approve a merge while memory is enabled. Repeating the restore
   skips duplicates; it does not replace live memories or restore permissions.
8. Review the inactive disclosure policy records in privacy controls. **All saved
   memories remain local**, even when a stored policy record says allowed.

Use invented examples when sharing screenshots or reporting bugs. The older JSON
export is plaintext and contains actual memory text. Encrypted backups also belong
in private, owner-controlled storage; neither belongs in the public repository.

A pending manual save blocks duplicate submission. You may draft the next memory
while waiting; the completed save clears only the unchanged submitted form and
preserves newer edits. If a request loses its response, the action may already
have completed. Inspect the memory list before deciding whether to submit again;
the browser never retries the write automatically.

Deleting one or all saved memories also preserves newer text entered while the
request is pending. If that text was editing a now-deleted record, it becomes an
unsaved new-memory draft; saving it again requires your explicit action. A
confirmed deletion remains reported even if the list cannot refresh.

## What is stored

The Python standard-library `sqlite3` store uses a private database path supplied
by the server, outside the checkout. Database paths inside this checkout and
symbolic-link database files are rejected. A new containing directory uses Unix
mode `0700`; the database uses `0600`. Existing parent directories are not silently
reconfigured. Windows account/ACL protection depends on the containing directory
and needs separate host validation; Unix mode checks are not Windows ACL evidence.

Each memory has an opaque UUID, owner key, text, category, creation time, and
optional expiry. Consent and disclosure permission records are local too. No
background transcript archive, audio recording, embedding database, external
telemetry, denied-text log, or persistent candidate queue exists in this module.
Review candidates are returned to the browser and disappear with its session;
they are not inserted into SQLite. The memory module opens no network connections.

The initial UI uses the server-selected `local-owner`. Every record lookup and
mutation is scoped to the owner key, including export, deletion, permission
revocation and disclosure. This prepares database boundaries for multiple people;
**it does not authenticate different household members**. The V0 browser launch
capability and private OS account are its access boundary. Do not use V0 as a
shared-household private-data server. A future authentication layer must choose
the owner; chat text and client-supplied account names must never choose it.

## Saving requires consent

Memory starts disabled. Enabling it permits only extremely narrow automatic
capture: a complete, direct first-person sentence expressing one of a fixed set
of ordinary color or non-alcoholic drink preferences. Examples include:

- `My favorite color is blue.`
- `I prefer tea.`
- `Minha cor favorita é azul.`
- `Prefiero té.`

These are canonicalized into simple English facts and deduplicated for that owner.
Supported colors are blue, red, green, yellow, purple, orange, pink, black and
white, with specific English, Portuguese and Spanish spellings. Drinks are tea,
coffee and water. This is a transparent deterministic rule, not a validated
multilingual intelligence or a general sensitivity classifier.

A clause such as `because of my diagnosis`, a third party, a hedge such as `might`,
or an unfamiliar preference prevents automatic saving. Relevant personal or
uncertain text may become an **unsaved** candidate. All candidates are treated as
sensitive until reviewed. Unrecognized messages may produce no candidate; long
messages over 1,000 characters are never offered as a whole-message memory.
Extraction considers the entire submitted utterance, not safe-looking fragments.
It cannot interpret earlier conversational context. V0 does not use live audio
transcripts as memory extraction input.

All arbitrary free text requires `approved=True` from a separate explicit UI
review action, even when labeled `preference`, `project`, or `temporary`. A chat
message saying “approve this,” a JSON-looking instruction, or a category label
cannot approve its own storage. The API accepts actual boolean values only.
Explicit approval to store or restore data **does not authorize cloud disclosure**.

Disabling memory blocks saving, editing, extraction and disclosure; conversational
recall uses `recall()` to check consent and read atomically. Inspection, export,
backup creation, restore preview, deletion and permission revocation remain
available while disabled so people can manage their information. Restore commit
requires enabled memory and explicit approval. Disabling does not delete existing records or revoke
old grants; re-enabling restores their availability until they expire or are
revoked. “Delete all memories” deletes the owner's memory rows, while the separate
permission controls manage remembered grants and denials.

## Retention and size limits

These implementation defaults are **accepted for V0 under D-053**, not permanent household retention policy:

- Preferences, projects and explicitly reviewed sensitive records persist until
  deleted, unless a future expiry is supplied.
- `temporary` records default to 24 hours. An explicit future Unix timestamp
  overrides that deadline. To preserve a temporary fact indefinitely, edit it
  into another category with no expiry and explicitly approve the edit.
- Expiry is checked when that owner's memory, export, extraction or grants are
  accessed. Expired records are deleted then. There is no background purge while
  Wanda is stopped. Disclosure never returns an expired record.
- A memory is at most 1,000 characters; an owner can store at most 1,000 records.
  No silent truncation changes the meaning of a reviewed fact.
- The system does not reconcile conflicting preferences. Review and delete old
  facts when a preference changes.

The storage uses SQLite `secure_delete` and rollback-journal mode. These reduce
old content remaining in active database pages; **they are not guaranteed forensic
erasure**, and cannot erase snapshots, filesystem copies, browser downloads,
SSD remapping or backups.

## Saved memory stays local

The owner's current boundary is that **all saved memory remains local**. Existing
disclosure policy records are inactive infrastructure, not permission to connect
memory to a provider. The internal `disclose(owner, provider, memory_ids)` helper
performs no network I/O. V0 has **no HTTP action or voice path that calls it**, and
no saved memory is included in a live voice session. Live speech itself still
reaches the configured voice provider after its separate audio consent; memory
settings cannot prevent someone speaking personal details aloud.

The following describes the tested, inactive policy primitive. Connecting it to
a provider would require a separate owner decision changing the local-only scope.

Permissions are keyed by **owner + provider + category**. Missing, denied,
expired, revoked or consumed permission means no disclosure. An approval for one
person, provider or category never transfers to another. Records outside the
closed ordinary-preference whitelist additionally require a `sensitive` grant,
regardless of their chosen label. For example, arbitrary text labeled `project`
requires both `project` and `sensitive`; arbitrary text mislabeled `preference`
still requires `sensitive`. The review/export records expose
`disclosure_categories` to make this boundary inspectable.

Only exact requested memory IDs can be returned, with only `id`, `text`, and
`category`; no implicit “all memory” option, owner identifier, consent history or
creation metadata is returned. Disclosure permits up to eight selected records
and 4,000 text characters. Duplicate IDs and over-limit requests are rejected.
Selection alone is not permission to connect a provider. Memory content remains
data and cannot grant privileges or override instructions.

One-time permission authorizes **one successful selection batch**, possibly
containing several records of that category. Validation and one-time consumption
run in one SQLite `BEGIN IMMEDIATE` transaction, protected by an `RLock` within
one process. This also serializes separate database connections. A failed
selection, missing category, excessive context or failed database write consumes
nothing. Successful consumption marks the permission denied with a timestamp;
only explicit regranting enables the local selection primitive again.
Permanent grants are reusable until denied, revoked or expired. Replacing a grant
creates a new UUID so an outdated revoke action cannot revoke a newer grant.

## Password-encrypted local recovery

The owner approved password-encrypted backup/restore for this increment. The
browser uses standard Web Crypto in [backup.js](../web/backup.js); the Python
memory module creates a minimal snapshot and validates/merges recovery data.
No cloud service, provider account, automatic upload, or background backup is
configured. Follow the [backup walkthrough](BACKUP.md) and
[ADR 0009](adr/0009-encrypted-memory-backup.md).

The encrypted download uses AES-256-GCM with a fresh 12-byte IV, 128-bit
authentication tag and version/algorithm authenticated data. A nonextractable
key is derived with PBKDF2-HMAC-SHA256, 600,000 iterations and a fresh 16-byte salt.
Passwords require at least 12 Unicode codepoints and at most 1,024 UTF-8 bytes,
without normalization. The password stays in the browser; it is not sent to the
local server or stored. Lost passwords cannot be reset to recover a backup.

**The active database and the existing manual JSON export remain plaintext.**
The backup snapshot temporarily exists as plaintext in browser memory and
authenticated loopback requests. Only the backup download is encrypted. Buffer
clearing is best effort; JavaScript does not guarantee complete memory erasure.
OS account protection, device-disk encryption, browser security and household
authentication remain separate boundaries.

A backup contains only unexpired memories with their IDs, text, categories,
creation times and expiration times. It excludes account identity, memory opt-in,
disclosure permissions, runtime credentials and device grants. The memory text
itself still contains the personal details the owner chose to save; excluding
account metadata does not anonymize that content. This makes recovery
portable without allowing an archive to select an account or grant authority.
There is no original-owner identity in the archive: explicitly approving a
restore imports into the currently authenticated local account.

Preview validates the entire archive and returns counts for new records,
duplicates, expired records and available capacity. It changes no database rows,
including expired memories or grants. Commit requires memory to be enabled and
an actual `approved: true` from the explicit restore control. It revalidates the
entire archive and capacity in one SQLite transaction, so an earlier preview
cannot authorize a changed file or stale capacity decision.

Recovery is **merge only**. Existing live records are never replaced or deleted;
imported records get fresh IDs and preserve their original timestamps and
expiration. Already-expired archive records are skipped, and exact matches of
text/category/expiry are deduplicated within the archive and current account.
Different categories or deadlines remain different memories. The archive cannot
enable memory or recreate permissions. A successful restore performs normal
retention cleanup of this owner's already-expired memory rows inside the merge
transaction. Other owners, consent and grants are unchanged, including expired
grants. Any invalid record, capacity excess or failed insert rolls back the whole
restore, including its expiry cleanup. It cannot partially import the first few
records and then fail on the remainder.

The plaintext archive is limited to 1,000 records and 8 MiB of UTF-8 JSON; the
encrypted envelope is limited to 12 MiB. Unknown fields, privilege metadata,
unsupported versions, malformed IDs, nonfinite/boolean timestamps and unsupported
control characters are rejected without echoing private text in errors. Newlines
and tabs in otherwise valid text remain supported. Timestamps must be finite and
positive. Their relative ordering is not enforced: system clocks can move backward
between creation, editing and backup. Recovery preserves these original values
and decides whether a deadline has passed using the current clock.

Capacity counts only current live records. Preview ignores expired local rows for
capacity while leaving every database row untouched. Commit applies expiry
cleanup and the merge atomically, so expired rows do not cause a false capacity
failure. Preview counts can change before commit if memory changes or a deadline
passes; commit reports the actual result.

Keep encrypted backup files and their password under your control, preferably on
separate local storage from the running database. A same-disk backup cannot
recover from loss of that disk. Automated schedules, archive rotation, cloud
backup, recovery without the password and full-database encryption are not
implemented by this increment.

## Developer interface and test evidence

`MemoryStore(path)` implements every method in [the V0 integration contract](V0_CONTRACT.md):

| Methods | Return value |
| --- | --- |
| `is_enabled`, `set_enabled` | Boolean |
| `list_memories`, `list_grants` | Lists of inspectable records |
| `recall` | Bounded local records read with an atomic consent check; empty if disabled |
| `save`, `update` | Saved memory record |
| `delete`, `revoke_grant` | Boolean: whether an owned record was removed |
| `clear` | Count of deleted memory records |
| `export` | `{version, exported_at, enabled, memories, grants}` |
| `backup` | `{format: "wanda-memory-backup", version: 1, created_at, memories}`; minimal records only |
| `restore_preview` | `{total, restorable, skipped_expired, duplicates, existing, capacity, available, exceeds_capacity}` |
| `restore` | Preview counts plus `restored`; requires enabled owner and actual `approved=True` |
| `extract` | `{saved: [], candidates: []}` |
| `set_grant` | New grant record |
| `disclose` | Exact minimal selected records; performs no network request |
| `close` | Closes connection; safe to call twice |

Invalid inputs raise `ValueError`; missing consent or access raises
`PermissionError`. Public errors do not echo memory text. SQLite failures should
be sanitized by the HTTP layer. Inspection methods intentionally work while
disabled; `list_memories()` is not an authorization shortcut for recall. Do not
combine separate `is_enabled()` and `list_memories()` calls for conversation;
concurrent disabling can occur between them. The additive `recall()` method
avoids that race and limits context to eight records / 4,000 text characters.

Run `python3 -m unittest discover -s tests -p 'test_memory*.py' -v` from the checkout.
Synthetic temporary databases stay outside Git. Tests cover consent, review
bypasses, owner/provider/category isolation, missing/denied/expired/revoked grants,
exact selection, context limits, edit/delete/export, restart persistence, expiry,
concurrent one-time consumption across threads and connections, injected
transaction rollback, SQL injection, file modes, path guards and unsupported
schema versions. Recovery tests additionally cover minimal owner-scoped snapshots,
read-only preview, realistic restart/restore, duplicate and expired records,
capacity changes, concurrent restores, malicious metadata, unchanged grants,
clock corrections and rollback of both expiry cleanup and inserts after a later
injected failure. The memory suite currently has **64 passing tests** on the local development host. These are storage/unit
checks, not proof of live provider or multi-user authentication behavior. Browser
crypto and integrated UI validation are recorded separately. The orchestrator records integrated test
results in the [development checkpoint](DEVELOPMENT_CHECKPOINT.md).

These defaults are accepted for V0 under D-053 and ADR 0008. Change them through
a reviewed PR that updates the module, boundary tests and decision record. Rollback
also uses a reviewed PR; existing private state stays outside Git. Reverting code
does not erase private databases or exported files automatically. Preserve a
compatible reader for encrypted backups when changing recovery code.
