# Private memory backup and restore

This feature is implemented and accepted in V0 (D-051/D-053). See the
[checkpoint](DEVELOPMENT_CHECKPOINT.md) for current verification status.

In Memory, choose **Encrypted backup**, enter and confirm a unique password, then
download the file. Use at least 12 characters; several randomly chosen words are
better than a familiar phrase. Keep the password separately in a trusted password
manager or another place you control. **There is no password reset or recovery key.**

The file protects the saved memories when it is closed. It does not encrypt Wanda's
working database. Your password stays in the browser. Wanda does not upload the file
or save the password. A backup on the same computer will not protect against losing
that computer; copying the encrypted file to a separate drive is an owner action.
No automatic or offsite backup service is configured.

To restore, select the encrypted file in Memory, enter its password, inspect the
preview, enable memory if needed, and confirm the merge. All records can be inspected
through the preview pages. Existing unexpired memories stay in place. Normal expiry cleanup still applies. Duplicate and expired
records are skipped; invalid or oversized archives fail without partial changes.
Device/cloud permissions, keys and old memory opt-in settings are never restored.

Live voice must be disconnected during backup and restore. The app clears the
password fields after submission and discards the decrypted preview when cancelled
or completed. Keep the computer and browser session private while memories are shown.

The separate **Plaintext export** action remains available for inspection. That JSON
file is readable without a password; handle it as private information.

See [ADR 0009](adr/0009-encrypted-memory-backup.md) for the file format, limits,
standard cryptographic primitives, alternatives and known boundaries.
