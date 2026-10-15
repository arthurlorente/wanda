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
| D-009 | Accepted | Validate a portable P0 voice prototype before buying satellite hardware or implementing all integrations. | Fastest way to test the hardest assumption; [Issue #1](https://github.com/arthurlorente/wanda/issues/1). |
| D-010 | Accepted planning constraint | Aim for ≤$350 initial added hardware and $60–$100/month cloud expense. | Affordable home operation; values are budgets, not verified costs. |
| D-011 | Accepted | No Notion dependency at this stage. | Avoid duplicate truth. Revisit if nontechnical collaboration or a private notebook demands it. |
| D-012 | Accepted requirement | Target general household availability with identity-gated personal/privileged actions. | Anyone at home may use safe shared controls without opening private data. [ADR 0002](adr/0002-trust-boundaries.md). |
| D-013 | Proposed | Use older gaming laptop as possible always-on host and ESP32-class satellites. | Reuse existing devices and avoid requiring desktop GPU availability; benchmark first. |
| D-014 | Proposed | Use Home Assistant for deterministic home control, OpenClaw for broader scoped actions, and a separate memory service. | Clean permission and service boundaries. Specific APIs and components not selected. |
| D-015 | Unresolved | Choose software, documentation and hardware licenses. | [Issue #6](https://github.com/arthurlorente/wanda/issues/6). |
| D-016 | Unresolved | Choose exact voice provider/model, version and transport implementation. | API compatibility, quality and spending are not yet measured. |
| D-017 | Accepted foundational identity | Wanda is the **antithesis of the JARVIS / Big AI assistant model**: extraordinary intelligence for ordinary people, not a luxury servant or opaque institution-controlled product. | [Identity and philosophy](IDENTITY.md) defines design consequences, safeguards, and explicit cloud-dependency caveats. |
| D-018 | Accepted character foundation; implementation pending | Preserve Wanda's first-person manifesto as the foundation of her future personality, with a distinct behavioral specification. | [MANIFESTO](MANIFESTO.md) and [PERSONALITY](PERSONALITY.md); future runtime prompts and memory systems must reflect them without claiming consciousness or overriding safety. |
| D-019 | Accepted P0 implementation constraint | Develop Wanda as a **portable application**; choose the permanent always-on host after validating the prototype. | Avoid coupling initial code to the RTX desktop or older gaming laptop; keep setup and tests reproducible across supported host machines. |

| D-020 | Accepted | P0 uses a browser interface as a client to an independently designed portable voice service. | Eases testing and later satellite integration. |
| D-021 | Accepted | During project planning, multiple-choice questions include an optional free-text alternative. | Allows clarification and alternatives to suggested responses. |
| D-022 | Accepted | P0 begins with click-to-connect, followed by natural hands-free conversation; the intended household interface uses a Wanda wake word. | Decouples conversational quality testing from wake-word recognition. |

| D-023 | Accepted process delegation; technical selection pending | Let Codex research, compare, and propose the P0 development stack rather than preselecting Python or TypeScript. | Compare portable deployment, WebRTC/browser integration, long-term Home Assistant and agent adapters, developer ergonomics, ecosystem maturity, maintenance, testability and complexity. Record alternatives and rationale before implementing. |

| D-024 | Accepted development workflow | Codex may independently research, implement and test scoped work on feature branches, but must open PRs for human review before merging to main. | Preserve momentum without surrendering architectural, privacy, security or integration approvals. See [WORKFLOW](WORKFLOW.md). |

| D-025 | Accepted evaluation process; licenses undecided | Have Codex compare software, documentation, firmware and hardware licenses against Wanda's philosophy and integrations, then recommend choices for approval. | See [licensing evaluation brief](LICENSING_EVALUATION.md) and [Issue #6](https://github.com/arthurlorente/wanda/issues/6). No operative license added. |

| D-026 | Accepted P0 success priority | Evaluate conversational naturalness first: turn-taking, pauses, interruptions, barge-in and seamless follow-ups. | Response latency and per-session cost remain measured constraints, not ignored or automatically optimized above naturalness. See [Issue #1](https://github.com/arthurlorente/wanda/issues/1). |

| D-027 | Accepted P0 capability target; model support unvalidated | Design Wanda for multilingual speech conversation from P0, including switching languages during a session, without an English-only gate. | Actual language coverage and quality depend on the chosen voice model; benchmark supported languages and mixed-language conversations rather than promising universal fluency. |

| D-028 | Accepted P0 scope expansion; implementation pending | Implement persistent cross-session memory from the first voice prototype, rather than session-only context or a later milestone. | Move the minimum viable private memory capability into P0; preserve consent, access controls, inspectability and deletion, with full multi-user/agent memory enhancements phased later. Supersedes prior P0 memory deferral in roadmap and requirements; [ADR 0005](adr/0005-memory.md). |

| D-029 | Accepted P0 memory policy direction; defaults pending | Use **selective automatic memory with user controls**, not save-only-on-command and not blanket transcript archival. | Extract useful context and preferences from conversations under consented settings, with inspect/delete/disable controls; sensitive information, retention defaults, confirmation policy, and identity scope require separate decisions. See [ADR 0005](adr/0005-memory.md). |

## How to append decisions

Append a new numbered row when a substantive decision is accepted, rejected, superseded or reopened. Update existing status only with a dated history note and link to the replacing decision or ADR. Technical choices should have an ADR. Keep `PROJECT_CONTEXT.md`, `PROJECT_STATE.md`, requirements and issues in sync.

## History

- 2026-10-15: D-029 accepted: selective automatic memory with user controls; detailed sensitivity and retention rules remain open.


- 2026-10-15: D-028 accepted: persistent cross-session memory is now within P0 scope, superseding earlier deferral; specific memory granularity and retention remain open.


- 2026-10-15: D-027 accepted: multilingual-first P0, including in-session language switching, subject to actual model support and tests.


- 2026-10-15: D-026 accepted: conversational naturalness is P0's primary quality criterion; benchmark latency and cost alongside it.


- 2026-10-15: D-024 adopted: autonomous Codex implementation through reviewed pull requests; no automatic merges.


- 2026-10-15: D-023 accepted: delegate stack assessment to Codex; no programming language or framework has yet been selected.


- 2026-10-15: D-019 accepted: portable-first development; permanent host decision deferred. D-009 wording revised from laptop-based to portable without changing its prototype-first rationale.

- 2026-10-15: D-018 accepted: first-person manifesto preserved and initial personality behavior specification established for later implementation.

- 2026-10-15: D-017 accepted and the project's antithesis-to-JARVIS / Big AI philosophy established as foundational product identity, not a brand-origin story.

- 2026-10-15: First consolidated register reconstructed from project planning discussions and existing repository ADRs. Historical detail may be incomplete; prospective decisions should carry direct issue/PR/ADR links.
