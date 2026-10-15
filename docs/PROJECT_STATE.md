# Wanda — Current project state

**As of:** 2026-10-15
**Phase:** Foundation and planning complete enough for P0 preparation; **no functioning Wanda voice prototype has been built or validated**.

## Verified repository state

- Public repository: https://github.com/arthurlorente/wanda
- Initial README, architectural sketches, five technical ADRs, security/contribution guidance and issue templates are committed.
- GitHub Issues:
  - [#1 — P0 real-time conversational voice](https://github.com/arthurlorente/wanda/issues/1)
  - [#2 — P1 Home Assistant](https://github.com/arthurlorente/wanda/issues/2)
  - [#3 — P2 permissioned agents and memory](https://github.com/arthurlorente/wanda/issues/3)
  - [#4 — P3 voice satellites](https://github.com/arthurlorente/wanda/issues/4)
  - [#5 — P4 room handoff](https://github.com/arthurlorente/wanda/issues/5)
  - [#6 — license decisions](https://github.com/arthurlorente/wanda/issues/6)
- This consolidation added a context index, decision register, open questions, requirements and decision-capture workflow.
- README uses Wanda's name without entertainment-brand disclaimers.
- Foundational first-person manifesto and initial personality specification documented; runtime character behavior has **not** been implemented.
- D-019: P0 will be developed as a portable application; permanent host selection is deferred.
- D-020 through D-022: Browser client, click-to-connect free conversation in P0, wake word later, and optional free-text alternatives in planning questions.
- D-023: Codex will evaluate and propose the P0 technology stack; none has been selected.
- D-024: Codex can implement scoped issues autonomously on branches; changes require human-reviewed PRs before merge.
- D-025: Codex will research licensing options and propose a recommendation for review. No license has been chosen.
- D-026: Conversational naturalness is the primary P0 success criterion; speed and cost remain benchmarking constraints.
- D-027: Multilingual P0 and mid-session language switching are accepted targets; actual model coverage unverified.
- D-028–D-033: P0 persistent memory uses opt-in consent, selective automatic ordinary memories, permission for sensitive items, and local primary storage. Retention, database, encryption and household identity are not yet selected.

- Memory storage direction: local on Wanda host; consent during setup.

## Decision status

- **Accepted:** Wanda identity and vision, GitHub as canonical project knowledge, decision-record workflow, cloud realtime speech as P0 direction, separate permission tiers, private data excluded from the public repo, staged handoff, durable user-controlled memory as a goal.
- **Proposed/needs validation:** Exact realtime API/model, WebRTC topology, satellite selection, persistent-memory backend and consent/retention design, permanent host selection, OpenClaw API boundary, identity solution.
- **Unresolved:** Software/docs/hardware licenses, data retention policy, costs, user consent details, latency/quality targets, Codex technology-stack recommendation and P0 implementation stack.

## Next work, in order

1. Check and reconcile this consolidation with the project owner's intent; log corrections as documentation updates.
2. Have Codex evaluate licenses via [#6](https://github.com/arthurlorente/wanda/issues/6) and [licensing brief](LICENSING_EVALUATION.md); approve a license before inviting external contributions.
3. Specify P0 experiments and acceptance criteria in [#1](https://github.com/arthurlorente/wanda/issues/1).
4. Build P0 on a branch/PR, not directly on main. Compare measured conversational quality against the official ChatGPT Voice experience.
5. Make hardware purchases only after baseline measurements justify them.

## Known blockers / caution

- No code, test run, audio stream or benchmark has demonstrated the intended user experience.
- No API key or billing configuration should enter Git.
- Public repo != licensed open source until license files are chosen.
- Cross-room, local fallback and comprehensive persistent memory are goals, not current capabilities.

## Updating this file

Keep this short and operational. Whenever an accepted change alters scope, milestone, status, blocker, or next action, update the relevant section along with its issue/PR. Review at the end of significant work sessions; do not invent completion claims.
