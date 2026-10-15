# Wanda — Requirements and priorities

**Status:** Product requirements and test intentions; not implementation status. Reviewed 2026-10-15.

Labels: **Must** = important to envisioned product; **P0** = required for initial prototype; **Later** = still desired but deliberately deferred.

| ID | Requirement | Priority | Verification approach |
| --- | --- | --- | --- |
| R-01 | Low-latency speech-to-speech, natural turns, pauses and barge-in | Must / P0 | Benchmark multiple conversations with interruption and silence cases |
| R-02 | Follow-up conversation without repeating the wake word during an active session | Must / P0 | Multi-turn dialogue tests |
| R-03 | Microphone state visible; user can immediately disconnect | Must / P0 | UI and session shutdown tests |
| R-04 | Secrets remain server-side; no raw audio retained by default | Must / P0 | Review flow, network traffic and storage behavior |
| R-05 | Natural room-level voice entry, eventually with inexpensive satellites | Must / Later | Far-field, duplex and echo tests |
| R-06 | Seamless conversation continuity between rooms | Must / Later | Two-room handoff and arbitration tests |
| R-07 | Allowlisted household voice commands via Home Assistant | Must / Later | Mock and real-world safe-state tests |
| R-08 | Restrict access to private data and sensitive machine tools | Must / Later | Untrusted-speaker and prompt-injection tests |
| R-09 | Research, file and computer workflows through a permissioned agent | Must / Later | Sandboxed integration tests and approvals |
| R-10 | Searchable, user-inspectable and deletable cross-session memory | Must / Later | Persistence, per-person access, removal, export tests |
| R-11 | User-controlled deployments and safe offline home functions where feasible | Must / Later | Internet-disconnect tests |
| R-12 | Reproducible, public hardware/software docs without exposing user data | Must / ongoing | Repo review and contribution checklist |
| R-13 | Operate within hardware + monthly budget targets when practical | Target / ongoing | Bill of materials and real usage measurements |
| R-14 | P0 implementation is portable and does not require a specific computer or dedicated GPU | Must / P0 | Document setup and run/test on supported host environments; avoid machine-specific hardcoding |

## Deliberately not in P0

- Always-on microphones or continuous household recording
- Automatic room tracking and resident voice authentication
- Full Home Assistant or OpenClaw production integration
- Private long-term memory storage
- Custom electronics or hardware purchases

## Interpretation

A feature's presence in this table is **not** evidence it works. If a requirement changes, update this file and docs/DECISION_LOG.md; architecture changes need ADRs. Precise quantitative acceptance criteria should be established with benchmark evidence, not invented here.
