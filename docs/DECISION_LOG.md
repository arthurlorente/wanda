# Wanda — Decision register

**Reviewed:** 2026-10-15

This is an index, not a substitute for ADRs. **Accepted** means an agreed direction or requirement, not implemented or validated. **Proposed** means a candidate that must not be described as settled. Record reversals rather than rewriting history silently.

| ID | Status | Decision | Rationale / record |
| --- | --- | --- | --- |
| D-001 | Accepted | Name the assistant and public project **Wanda**. | Ordinary, human, approachable; deliberate alternative to elite/corporate AI-servant framing. |
| D-002 | Accepted | Public GitHub repo `arthurlorente/wanda` is canonical for project knowledge and implementation. | One versioned source of truth; no duplicate Notion architecture database. See [ADR 0006](adr/0006-documentation-governance.md). |
| D-003 | Accepted | Capture each substantive decision in GitHub with status, rationale, implications and links. | Conversation context alone is unreliable. See [WORKFLOW](WORKFLOW.md) and [ADR 0006](adr/0006-documentation-governance.md). |
| D-004 | Accepted for prototype, unvalidated | Prioritize cloud real-time speech-to-speech for natural voice. | Voice quality first; price, availability and model mapping require tests. See [ADR 0001](adr/0001-cloud-realtime-voice.md). |
| D-005 | Accepted | Keep home control separate from restricted personal/PC agency. | Minimize risk and preserve household access. See [ADR 0002](adr/0002-trust-boundaries.md). |
| D-006 | Accepted | Public code with private local credentials, history, recordings and household data. | Privacy and safe collaboration. See [ADR 0003](adr/0003-public-repo-private-runtime.md). |
| D-007 | Accepted as requirement; mechanism experimental | Support cross-room continuity; test explicit handoff before automatic tracking. | Technical feasibility and guest privacy. See [ADR 0004](adr/0004-cross-room-handoff.md). |
| D-008 | Accepted as requirement; storage unselected | Preserve useful cross-session text history and structured memory; no raw recordings by default. | User-controlled durable context. See [ADR 0005](adr/0005-memory.md). |
| D-009 | Accepted | Validate laptop-based P0 before buying satellite hardware or implementing all integrations. | Fastest way to test the hardest assumption; [Issue #1](https://github.com/arthurlorente/wanda/issues/1). |
| D-010 | Accepted planning constraint | Aim for ≤$350 initial added hardware and $60–$100/month cloud expense. | Affordable home operation; values are budgets, not verified costs. |
| D-011 | Accepted | No Notion dependency at this stage. | Avoid duplicate truth. Revisit if nontechnical collaboration or a private notebook demands it. |
| D-012 | Accepted requirement | Target general household availability with identity-gated personal/privileged actions. | Anyone at home may use safe shared controls without opening private data. [ADR 0002](adr/0002-trust-boundaries.md). |
| D-013 | Proposed | Use older gaming laptop as possible always-on host and ESP32-class satellites. | Reuse existing devices and avoid requiring desktop GPU availability; benchmark first. |
| D-014 | Proposed | Use Home Assistant for deterministic home control, OpenClaw for broader scoped actions, and a separate memory service. | Clean permission and service boundaries. Specific APIs and components not selected. |
| D-015 | Unresolved | Choose software, documentation and hardware licenses. | [Issue #6](https://github.com/arthurlorente/wanda/issues/6). |
| D-016 | Unresolved | Choose exact voice provider/model, version and transport implementation. | API compatibility, quality and spending are not yet measured. |
| D-017 | Accepted foundational identity | Wanda is the **antithesis of the JARVIS / Big AI assistant model**: extraordinary intelligence for ordinary people, not a luxury servant or opaque institution-controlled product. | [Identity and philosophy](IDENTITY.md) defines design consequences, safeguards, and explicit cloud-dependency caveats. |
| D-018 | Accepted character foundation; implementation pending | Preserve Wanda's first-person manifesto as the foundation of her future personality, with a distinct behavioral specification. | [MANIFESTO](MANIFESTO.md) and [PERSONALITY](PERSONALITY.md); future runtime prompts and memory systems must reflect them without claiming consciousness or overriding safety. |

## How to append decisions

Append a new numbered row when a substantive decision is accepted, rejected, superseded or reopened. Update existing status only with a dated history note and link to the replacing decision or ADR. Technical choices should have an ADR. Keep `PROJECT_CONTEXT.md`, `PROJECT_STATE.md`, requirements and issues in sync.

## History

- 2026-10-15: D-018 accepted: first-person manifesto preserved and initial personality behavior specification established for later implementation.

- 2026-10-15: D-017 accepted and the project's antithesis-to-JARVIS / Big AI philosophy established as foundational product identity, not a brand-origin story.

- 2026-10-15: First consolidated register reconstructed from project planning discussions and existing repository ADRs. Historical detail may be incomplete; prospective decisions should carry direct issue/PR/ADR links.
