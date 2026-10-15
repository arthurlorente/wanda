# Roadmap

**V0 progress (2026-10-15):** local browser, memory and permissioned mock-home
demonstration implemented on a review branch. Optional real adapters are present;
live voice and genuine Home Assistant evidence are still needed for P0/V1 gates.
See [current state](PROJECT_STATE.md) and [acceptance map](testing/V0_ACCEPTANCE.md).

- **P0 Voice + memory foundation:** Portable browser-based real-time conversational voice, multilingual switching, and private persistent cross-session memory; measure interruption, natural pauses, turn-taking, latency, and authorized recall/deletion. No permanent host selected.
- **P1 Home:** Scoped Home Assistant controls with local-control fallback.
- **P2 Agent + advanced memory:** Restricted OpenClaw tools, approvals, expanded structured/searchable memory, advanced user/guest boundaries and export workflows, building on the P0 memory foundation.
- **P3 Satellite:** Affordable mic array with full-duplex streaming, echo cancellation, and far-field performance.
- **P4 Multi-room:** Handoff, shared context, simultaneous-speaker arbitration, and privacy separation.

**V1 release gate (D-048):** V1 is reached after combining P0 voice/memory with a verified, permissioned **P1 Home Assistant integration** and user-defined device/action permissions, plus a usable persona and graceful degradation. The P0 prototype is not itself V1. Full guest voice identification, satellites, room handoff and general OpenClaw autonomy remain later unless separately prioritized. Controlled autonomy and proactive suggestions can begin with safe bounded actions and grow incrementally.

**Priority (D-049):** Privacy and user independence supersede convenience, lowest latency or provider convenience where they conflict; document exceptions for review.

Milestones require reproducible acceptance criteria and links to implementation issues/PRs.
