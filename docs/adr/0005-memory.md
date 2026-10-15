# ADR 0005 — Comprehensive persistent memory

**Status:** Requirement accepted; V0 foundation accepted and merged under D-053. Updated 2026-10-15. Full household memory remains a target.

**Milestone change:** A privacy-respecting persistent cross-session memory foundation is now required in P0, alongside the voice prototype. This supersedes the former P2-only staging of durable memory. P2 remains responsible for richer searchable/structured memory, advanced access control and agent-history integration.

**Accepted P0 policy (D-029–D-033):** During setup, ask users to opt in before persistent memory is enabled. Once enabled, selectively save useful ordinary context; request explicit permission before storing sensitive context, interpreting sensitivity in context and asking when uncertain. Do not archive all conversations or raw audio by default. Store primary memory locally on Wanda's host, outside the public code repository. Users can inspect and delete saved memory and disable further saving.

**Backup evaluation (D-034, updated by D-051/D-053):** Password-encrypted local backup and explicit merge restore are implemented and accepted for V0; see [ADR 0009](0009-encrypted-memory-backup.md). Automatic/offsite backup and providers remain unselected. Recovery testing and user control over keys matter.

**Retention (D-035):** Durable preferences and ongoing projects should persist; temporary memories should expire based on context. Users can review and override retention. V0 defaults and enforcement are implemented and accepted under D-053; see [Memory](../MEMORY.md). Richer household retention policy remains to be designed.

**Multi-user architecture (D-036):** Model private memories with an owner identity and distinguish them from explicitly shared household data from the beginning. P0 may initially expose a single authenticated account, but must not bake single-user access into the storage schema. Voice recognition alone is not sufficient to authorize access to another resident's memories. Full household onboarding and guest policy can be implemented later.

**Voice-first identity (D-037):** Future household interactions should identify speakers primarily by voice for personalization. A voice match does not by itself grant access to private memories; protect access through independently authorized identity/session checks. Unknown voices receive guest-level permissions. Voice recognition implementation is later than P0.

**D-038 guest onboarding:** Keep session context temporary during voice-started registration. Create a persistent personal memory only after individual consent and identity verification. Consented carryover of useful context may be offered after enrollment; the transfer mechanism remains undecided.

**Guest data and trust (D-039/D-040):** A temporary guest identity may retain a minimal, clearly explained set of mundane preferences during the authorized lifecycle. Voice enrollment requires distinct informed consent. Remembered information must not be sold, shared for advertising or used for commercial profiling. Avoid transmitting identifiable memories to cloud providers unless necessary for a disclosed task and consistent with the user's choices. Temporary guest access should not silently become permanent; persistent profiles require explicit authorization.

**Cloud permissions (D-041/D-042):** Keep detailed memories and identity mappings local and share only task-relevant context. Before transmitting identifiable or sensitive memories or personal details to a cloud AI service, seek explicit permission; retain the individual's grant/denial per information type and scope for reuse. Users can inspect and revoke grants. Missing or ambiguous authorization means no disclosure. Another resident's permission never applies to someone else's data. Consent records are local and access-controlled; any unavoidable disclosure in live audio should be explained during onboarding.

**V0 implementation:** Local SQLite, conservative expiry defaults and one local OS-user access boundary are accepted for V0; see [Memory](../MEMORY.md). The working database is not encrypted. Under D-050 all saved memories stay local; existing disclosure policy records do not authorize connecting saved memory to cloud voice. That requires a new explicit owner decision.

**Open:** Encrypted working storage, automatic/offsite recovery, full household identity/authentication, richer retention rules and third-party privacy safeguards.

Maintain searchable text conversation history, structured personal and household memories, and auditable agent tasks in private storage. Review, deletion, and consent controls are mandatory. Raw recordings are off by default.

**Consequence:** Identity, retention, access controls, backups and deletion need validation before broad household use.
