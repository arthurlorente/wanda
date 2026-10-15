# V0 local memory and privacy

**Status: provisional implementation for owner review, 2026-10-15.** This is the
small, locally testable memory foundation for [Issue #7](https://github.com/arthurlorente/wanda/issues/7),
[D-028–D-043](DECISION_LOG.md), and requirements R-10, R-18–R-22 and R-28–R-30.
It is not full household identity, semantic memory, a backup system, or a claim
that cloud voice is private. See [ADR 0008](adr/0008-v0-portable-stack.md).

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
7. Add and revoke disclosure permissions in the privacy controls. **V0 never sends
   saved memories to a cloud provider**, even when a permission exists.

Use invented examples when sharing screenshots or reporting bugs. Exported JSON
contains the actual memory text and is private; do not upload it to the public
repository or include it in an issue.

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
Explicit approval to store data **does not authorize cloud disclosure**.

Disabling memory blocks saving, editing, extraction and disclosure; conversational
recall uses `recall()` to check consent and read atomically. Inspection, export,
deletion and permission revocation remain available while disabled so people can
manage their information. Disabling does not delete existing records or revoke
old grants; re-enabling restores their availability until they expire or are
revoked. “Delete all memories” deletes the owner's memory rows, while the separate
permission controls manage remembered grants and denials.

## Retention and size limits

These are **provisional V0 defaults**, not newly accepted product policy:

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

## Cloud disclosure boundary

The implemented service exposes a future integration primitive,
`disclose(owner, provider, memory_ids)`. V0 has **no HTTP action or voice path that
calls it**, and no saved memory is included in a live voice session. Live speech
itself still reaches the configured voice provider after its separate audio
consent; memory settings cannot prevent someone speaking personal details aloud.

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
The future calling integration still has to establish task relevance and treat
memory content as data, not privileged instructions.

One-time permission authorizes **one successful selection batch**, possibly
containing several records of that category. Validation and one-time consumption
run in one SQLite `BEGIN IMMEDIATE` transaction, protected by an `RLock` within
one process. This also serializes separate database connections. A failed
selection, missing category, excessive context or failed database write consumes
nothing. Successful consumption marks the permission denied with a timestamp;
only explicit regranting enables it again. A future network send happens after
consumption, so a network failure must not automatically retry or reuse the grant.
Permanent grants are reusable until denied, revoked or expired. Replacing a grant
creates a new UUID so an outdated revoke action cannot revoke a newer grant.

## Encryption and backup decision for review

**The database and manual JSON export are not encrypted by Wanda.** OS account
isolation and file modes do not replace encryption at rest. The owner should
keep V0 demonstration data synthetic until the storage/identity review is
complete. No provider policy, backup confidentiality or device-disk encryption
has been verified by this implementation.

Backup options remain unresolved under D-034:

| Option | Benefit | Limitation and remaining work |
| --- | --- | --- |
| Manual JSON export | Portable and understandable; no provider required | Plaintext; no import/restore tool or round-trip recovery validation yet |
| Local encrypted backup on another disk | User-owned keys, no cloud disclosure; protects against machine loss | Encryption library/key storage choice, consistent snapshot and restore tests needed |
| Optional client-encrypted offsite backup | Recovery after loss of both local disks | Explicit provider/terms review, encryption before upload, key custody, costs and restore tests needed |

Provisional recommendation: retain manual export for the synthetic V0 demo; design
and test an opt-in encrypted local backup next, before offering cloud backup.
Do not silently copy live SQLite files or upload unencrypted exports. No automated
backup, restore, cloud subscription or provider was configured. Disk encryption
and authenticated household identity remain separate reviews.

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

Run `python3 -m unittest discover -s tests -p test_memory.py -v` from the checkout.
Synthetic temporary databases stay outside Git. Tests cover consent, review
bypasses, owner/provider/category isolation, missing/denied/expired/revoked grants,
exact selection, context limits, edit/delete/export, restart persistence, expiry,
concurrent one-time consumption across threads and connections, injected
transaction rollback, SQL injection, file modes, path guards and unsupported
schema versions. These are storage/unit checks, not proof of live provider or
multi-user authentication behavior. The orchestrator records integrated test
results in the [development checkpoint](DEVELOPMENT_CHECKPOINT.md).

To accept the provisional defaults, review this document and ADR 0008 with the
implementation PR. To change them, update this module and the boundary tests. To
revert, do not merge the feature PR, or revert its code; existing private state
stays outside Git. An unmerged/reverted feature does not erase private databases
or exported files automatically.
