# Wanda — Requirements and priorities

**Status:** Product requirements and test intentions; not implementation status. Reviewed 2026-10-15.

Labels: **Must** = important to envisioned product; **P0** = required for initial prototype; **Later** = still desired but deliberately deferred.

| ID | Requirement | Priority | Verification approach |
| --- | --- | --- | --- |
| R-01 | Natural speech-to-speech conversation is the **primary P0 success criterion**: comfortable turn-taking, pauses, barge-in and interruption handling | Must / P0 / top priority | Benchmark unscripted multi-turn conversations with interruption and silence cases against a reference voice experience; measure latency and cost separately |
| R-02 | Follow-up conversation without repeating the wake word during an active session | Must / P0 | Multi-turn dialogue tests |
| R-03 | Microphone state visible; user can immediately disconnect | Must / P0 | UI and session shutdown tests |
| R-04 | Secrets remain server-side; no raw audio retained by default | Must / P0 | Review flow, network traffic and storage behavior |
| R-05 | Natural room-level voice entry, eventually with inexpensive satellites | Must / Later | Far-field, duplex and echo tests |
| R-06 | Seamless conversation continuity between rooms | Must / Later | Two-room handoff and arbitration tests |
| R-07 | Allowlisted household voice commands via Home Assistant | Must / Later | Mock and real-world safe-state tests |
| R-08 | Restrict access to private data and sensitive machine tools | Must / Later | Untrusted-speaker and prompt-injection tests |
| R-09 | Research, file and computer workflows through a permissioned agent | Must / Later | Sandboxed integration tests and approvals |
| R-10 | Persistent cross-session memory from P0, with private storage and user inspect/delete controls; progressively add full search, export, per-person household isolation and structured memory | Must / P0 foundation + Later expansion | Restart session and verify authorized recall, review and deletion; evaluate access control, retention and export as they mature |
| R-11 | User-controlled deployments and safe offline home functions where feasible | Must / Later | Internet-disconnect tests |
| R-12 | Reproducible, public hardware/software docs without exposing user data | Must / ongoing | Repo review and contribution checklist |
| R-13 | Operate within hardware + monthly budget targets when practical | Target / ongoing | Bill of materials and real usage measurements |
| R-14 | P0 implementation is portable and does not require a specific computer or dedicated GPU | Must / P0 | Document setup and run/test on supported host environments; avoid machine-specific hardcoding |

| R-15 | Browser voice interface independent from underlying portable session service | Must / P0 | Browser client and documented non-browser interface boundary |
| R-16 | Click-to-connect conversation with interruptions and follow-ups in P0; wake-word activation is a later household goal | Must / P0 + Later | P0 hands-free session test; later wake-word detection evaluation |

| R-17 | P0 supports multilingual speech conversation without an English-only application restriction and tests code-switching | Must / P0 | Evaluate multiple model-supported languages plus mid-conversation switching; record language-specific limitations rather than asserting universal support |

| R-18 | Ensure persistent memory is opt-in/controlled, stored outside the public repository, and raw audio is not retained by default | Must / P0 | Inspect storage configuration, test disabling/deleting stored information, and verify no recordings or credentials leak into Git |

| R-19 | Selective automatic memory with explicit approval for contextually sensitive details | Must / P0 | Test ordinary recall, sensitive approval, review and deletion |
| R-20 | Memory requires setup-time opt-in; keep primary database on the local host | Must / P0 | Test memory disabled before consent and local persistence across restart |

| R-21 | Context-aware expiration: durable facts persist while temporary memories expire with user override | Must / P0 design | Test temporal expiry, retention of durable preferences and user preservation/deletion |
| R-22 | Use multi-user-ready account, ownership and memory boundaries in P0; deliver full multi-user UX in later milestones | Must / P0 architecture + Later | Validate schema separates private resident data from explicit shared household data; test denial of unauthorized cross-user reads |

## Deliberately not in P0

- Always-on microphones or continuous household recording
- Automatic room tracking and resident voice authentication
- Full Home Assistant or OpenClaw production integration
- Custom electronics or hardware purchases

## Interpretation

A feature's presence in this table is **not** evidence it works. If a requirement changes, update this file and docs/DECISION_LOG.md; architecture changes need ADRs. Precise quantitative acceptance criteria should be established with benchmark evidence, not invented here.
