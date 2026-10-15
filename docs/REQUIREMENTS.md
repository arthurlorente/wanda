# Wanda — Requirements and priorities

**Status:** Product requirements and test intentions; not implementation status. Reviewed 2026-10-15.

V0 implementation evidence and remaining gates are mapped in
[testing/V0_ACCEPTANCE.md](testing/V0_ACCEPTANCE.md). The implementation does not
change these accepted requirements or establish V1 completion.

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

| R-23 | Voice recognition is the primary eventual household identity experience for everyday personalization, with cautious unknown-speaker fallback | Must / Later; P0 design-ready | Evaluate enrolled speakers, false matches, replays, household background speech and unknown voices; require stronger authentication for private data and privileged tools |

| R-24 | Unknown speakers get general Q&A as guests; home-device commands require explicit scoped guest permission | Must / Later | Test allowed general questions and denied device commands absent grant; verify permissions cannot reveal private data |
| R-25 | Guests can initiate speaker registration by voice without immediately using a phone; maintain in-session conversational context through enrollment | Must / Later; P0 interface-compatible | Test voice enrollment invitation, interrupted/resumed session, verification and individual opt-in before durable private memory begins |

| R-26 | Guest device grants use device-scoped profiles, temporary by default, with resident-approved persistence | Must / Later | Validate expiry, revocation and prohibition of ungranted device actions |
| R-27 | Household and guest information is not used for sale, advertising or commercial profiling | Must / ongoing | Verify data flow, retention and provider policies |
| R-28 | Cloud AI receives only necessary task context; identity and detailed memory stay local | Must / P0 design + ongoing | Inspect and minimize provider payloads; document unavoidable voice/audio exposure |
| R-29 | Ask before cloud disclosure of identifiable or sensitive information and store person-specific approvals or denials by information type | Must / P0 design + Later multi-user UX | Test category grants, denials, missing permission prompts, updates/revocation and isolation across residents |

| R-30 | Store cloud disclosure grants by person, provider and information type, with review, expiration/revocation and one-time grants | Must / P0 design + staged UX | Verify authorization does not transfer across people, providers or categories; denied requests do not disclose information |

| R-31 | Persona implementation is grounded in the accepted manifesto, with distinctive but adaptive warmth, humor and considered disagreement | Must / P0 design + V1 validation | Evaluate persona conversation samples for character fidelity, user tone preferences and privacy boundaries |
| R-32 | Proactive suggestions plus bounded autonomous routine actions within explicit permissions | Must / V1 design; expand later | Test suggestion-only mode, authorized low-risk execution, approval for higher-impact actions and stop/revocation |
| R-33 | Residents can define device/action permissions and confirmation levels; guests have narrower temporary grants | Must / V1 Home | Test per-person profiles, deny by default, confirmations, authorization and audit records |
| R-34 | Graceful degraded behavior with local safe functions when available and clear disclosure of failures | Must / V1 | Disconnect API/network and verify safe fallback, no false success, no unauthorized retries or duplicate actions |
| R-35 | V1 succeeds only with natural multilingual voice, durable user-controlled memory and verified home-device control | Must / V1 | End-to-end demo with a real Home Assistant integration and authorized state verification |
| R-36 | Privacy and independence outrank convenience and marginal conversational improvements in trade-off decisions | Must / ongoing | Architecture reviews document local-first boundaries, portability, provider exposure and explicitly approved exceptions |

| R-37 | Password-encrypted local memory backup with previewed, explicitly approved restore; password remains user-controlled and no cloud upload is required | Approved V0 increment (D-051) | Test authenticated encryption, wrong password/tampering, portable restore, expiry, duplicate handling, atomic failure and preservation of existing permissions |

Current implementation boundary D-050 keeps all saved memories local. R-28–R-30
remain broader design requirements; no stored grant currently authorizes an
application path to disclose saved memories to a cloud provider.

## Deliberately not in P0

- Always-on microphones or continuous household recording
- Automatic room tracking and resident voice authentication
- Full Home Assistant or OpenClaw production integration
- Custom electronics or hardware purchases

## Interpretation

A feature's presence in this table is **not** evidence it works. If a requirement changes, update this file and docs/DECISION_LOG.md; architecture changes need ADRs. Precise quantitative acceptance criteria should be established with benchmark evidence, not invented here.
