# ADR 0005 — Comprehensive persistent memory

**Status:** Requirement accepted; implementation provisional. Updated 2026-10-15 under D-028.

**Milestone change:** A privacy-respecting persistent cross-session memory foundation is now required in P0, alongside the voice prototype. This supersedes the former P2-only staging of durable memory. P2 remains responsible for richer searchable/structured memory, advanced access control and agent-history integration.

**Accepted P0 policy (D-029–D-033):** During setup, ask users to opt in before persistent memory is enabled. Once enabled, selectively save useful ordinary context; request explicit permission before storing sensitive context, interpreting sensitivity in context and asking when uncertain. Do not archive all conversations or raw audio by default. Store primary memory locally on Wanda's host, outside the public code repository. Users can inspect and delete saved memory and disable further saving.

**Backup evaluation (D-034):** Codex will recommend a backup and restore approach, comparing on-device/local external backups, optional encrypted offsite backups, and export/import. No backup method or provider is selected. Recovery testing and user control over keys matter.

**Open:** Storage engine, encryption, backup choice, retention duration, household identity and third-party privacy implementation. A cloud voice provider may receive relevant context for processing, which does not make it the memory database.

Maintain searchable text conversation history, structured personal and household memories, and auditable agent tasks in private storage. Review, deletion, and consent controls are mandatory. Raw recordings are off by default.

**Consequence:** Identity, retention, access controls, backups and deletion need validation before broad household use.
