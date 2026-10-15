# ADR 0009 — Password-encrypted local memory recovery

2026-10-15. **Feature scope accepted (D-051); tested technical design accepted for
V0 (D-053) and merged in [PR #9](https://github.com/arthurlorente/wanda/pull/9).**
All saved memories remain local (D-050).

## Choice and alternatives

Use browser Web Crypto to encrypt a portable memory-only JSON archive. Passwords
stay in the browser and are not submitted to Wanda's Python server. Users download
the encrypted file, keep it where they choose, then select it and enter its password
locally to preview and approve a merge. No account, vendor or cloud upload is added.

| Option | Benefit | Cost / reason |
| --- | --- | --- |
| Existing plaintext JSON export | Simple, inspectable, no dependencies | Does not protect a misplaced backup; remains explicitly labeled plaintext |
| **Web Crypto encrypted download** | Standard browser primitives, portable file, no new runtime dependencies | Browser sees plaintext during use; password loss is unrecoverable; manual recovery only |
| Python cryptography library / CLI | Mature primitives and later scheduled backups | Additional install, dependency and password entry/storage path; defer until automatic backup requirements are approved |
| Encrypted offsite service | Survives loss of the host and local disks | Provider/account, retention, cost and key-custody decisions remain open; not authorized |

The versioned envelope uses PBKDF2-HMAC-SHA-256 with 600,000 iterations and a fresh
16-byte random salt to derive a nonextractable 256-bit AES-GCM key. Every archive
uses a fresh 12-byte IV, 128-bit authentication tag and fixed additional authenticated
data identifying the format/version/algorithms. Unsupported or extra envelope fields,
noncanonical base64, incorrect lengths and arbitrary KDF parameters are rejected
before key derivation. Encrypted files are capped at 12 MiB; plaintext JSON at 8 MiB,
with at most 1,000 memory records and the existing per-record text limits.

The browser's standard PBKDF2/AES-GCM interfaces are documented by
[MDN](https://developer.mozilla.org/en-US/docs/Web/API/SubtleCrypto/deriveKey).
The iteration count follows the SHA-256 work factor in
[OWASP's password-storage guidance](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html).
This applies a password-hardening guideline; it does not claim formal certification
or an independent cryptographic audit. Argon2 would provide memory hardness but is
not a native Web Crypto primitive; introducing a WASM/package dependency is deferred.

## Recovery and consent boundaries

- Archive only memory IDs, text, category and timestamps. Exclude credentials,
  account identity, opt-in state, provider grants and device permissions.
- Preview is read-only. Restore requires current memory opt-in and a separate
  explicit approval. The server revalidates the entire payload within its transaction.
- Merge into the authenticated local owner using new IDs. Never overwrite/delete
  live memories, restore privileges, infer consent from an archive, or accept an
  owner supplied by the file. Skip expired and duplicate records; reject capacity
  excess or any malformed record atomically. Normal cleanup of the current
  owner's expired memories shares the restore transaction and rolls back on failure.
  Timestamps remain finite and positive, but clock rollback does not invalidate
  otherwise valid records.
- Close live voice and local speech playback before backup/preview. Block live
  voice while decrypted content is staged for review. This avoids accidental spoken
  disclosure; it cannot prevent a person deliberately reading data into a later call.
- Browser fields and references are cleared when done or cancelled. Mutable buffers
  are zeroed where practical. JavaScript/OS memory erasure cannot be guaranteed.
- Backup encryption does not encrypt the working SQLite database, the existing
  plaintext export, or the private API configuration. Plaintext travels only over
  authenticated loopback HTTP between this browser and Wanda during recovery.

## Verification and reversal

Tests cover actual encryption/decryption and independent Node crypto interoperability,
wrong passwords, tampering, bounded parameters, malformed records, current consent,
owner boundaries, duplicates, expiration, capacity changes and rollback after an
injected partial-insert failure. Browser and HTTP tests exercise the complete flow.
Successful verification is recorded in the [checkpoint](../DEVELOPMENT_CHECKPOINT.md)
and [feature PR](https://github.com/arthurlorente/wanda/pull/9).

Revert this increment to remove the new UI/routes; existing memory and its plaintext
export remain unchanged. Preserve the documented encrypted format and a compatible
decoder for existing archives before replacing the implementation. Future changes
or rollback require a reviewed PR; V0 acceptance does not authorize automatic merges.
