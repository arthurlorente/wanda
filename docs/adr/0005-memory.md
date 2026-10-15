# ADR 0005 — Comprehensive persistent memory

**Status:** Requirement accepted; implementation provisional. Updated 2026-10-15 under D-028.

**Milestone change:** A privacy-respecting persistent cross-session memory foundation is now required in P0, alongside the voice prototype. This supersedes the former P2-only staging of durable memory. P2 remains responsible for richer searchable/structured memory, advanced access control and agent-history integration.

**Unresolved for P0:** What is remembered automatically, whether transcripts are retained, storage design, identity and access, retention defaults and consent UX. Until resolved, do not assume every spoken conversation should be saved.

Maintain searchable text conversation history, structured personal and household memories, and auditable agent tasks in private storage. Review, deletion, and consent controls are mandatory. Raw recordings are off by default.

**Consequence:** Identity, retention, access controls, backups and deletion need validation before broad household use.
