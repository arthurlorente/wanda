# Wanda — Project context

**Last consolidated:** 2026-10-15
**Status:** Authoritative summary of the project's intent, not a claim that the described software exists.
**Maintainers:** Project owner and contributors through reviewed changes.

## Vision

Wanda is an approachable, unusually capable, community-developed whole-home conversational assistant: human-feeling voice, durable memory, useful agency, and home control without requiring a billionaire's infrastructure or surrendering control of the household to a proprietary product.

Wanda is an ordinary human name, chosen to emphasize familiarity, personality and a relationship with technology that doesn't feel like interacting with a branded command appliance.

## Foundational identity: the antithesis of JARVIS and Big AI

Wanda rejects intelligence as an elite status symbol, an obedient corporate servant, or a black box whose benefits and controls belong only to large institutions. She aims to be capable, approachable and owned in practice by the people living with her. This is a commitment to accessibility, user agency, open collaboration, privacy and honest disclosure of dependencies—not a claim that the early system is already fully local or independent.

**[Read the full identity and philosophy](IDENTITY.md).** Future design trade-offs must consider those values and explicitly document compromises.

## Wanda's voice and character

The [first-person manifesto](MANIFESTO.md) captures how Wanda introduces herself and what she stands for. The [personality specification](PERSONALITY.md) translates this foundation into behavior: warm without servility, competent without pretension, quietly rebellious, discerning, occasionally dryly funny, and respectful of privacy and agency. These are design instructions for future implementations, **not** autobiographical memory or claims about a conscious system. They must remain subordinate to authorization, privacy and safety requirements.

## Core experience

- Talk to Wanda naturally, interrupt her mid-sentence, pause, ask follow-up questions, and resume an existing conversation.
- Access Wanda from inexpensive speakers/microphones throughout the home and eventually continue a conversation while changing rooms.
- Anyone in the home can use appropriate shared features; private memories, files and high-impact agent functions remain restricted.
- Wanda can answer questions, research, operate home devices and delegate scoped computer tasks.
- Wanda can recall prior discussions and projects across sessions, with understandable review, export and deletion controls.

## Principles and non-negotiables

1. **People first:** Household usefulness, personality and autonomy matter more than impressing a demo audience.
2. **Natural voice is foundational:** Conversational quality and interruptibility are the first technical gate.
3. **Public implementation, private operation:** Publish code and reproducible hardware guidance, never household secrets or private data.
4. **Honest privacy:** Initial conversational intelligence may run in the cloud; do not label the product fully local.
5. **Permission boundaries:** Natural voice cannot by itself authorize sensitive PC actions or expose another person's memories.
6. **Practical affordability:** Favor accessible existing hardware, test costs against a household-scale operating budget.
7. **Interoperability:** Home Assistant handles smart-home state; agent tooling handles bounded research and computer workflows.
8. **Traceable decisions:** The repo, not an individual chat session, is the canonical project record; see docs/WORKFLOW.md.

## Preferred operating model

- GitHub is the canonical store for code, docs, ADRs, issues, PRs and project state.
- ChatGPT is for discussion, research, planning and review.
- Codex is for scoped coding, testing and PRs using checked-in instructions and documents.
- Notion is **not currently required**. Add it only when a distinct use case is compelling; never make a second competing source of architectural truth.
- Discuss changes freely, then consolidate *substantive* decisions and their implications into GitHub. A complete consolidation is exceptional, not required after every message.

## Development and deployment approach

P0 will be developed as a **portable application**, runnable on an ordinary development machine without depending on the RTX 4080 Super or committing to the older gaming laptop. The permanent always-on host will be chosen after voice experiments and measured resource requirements. Document cross-platform setup and isolate device-specific code and configuration where practical.

## Initial constraints (planning targets; not measured)

- Existing desktop with RTX 4080 Super; an older Windows gaming laptop is a candidate always-on host. Do not require the high-power desktop for daily operation.
- Initial project hardware spending ceiling **$350**.
- Target cloud/API operating spend **$60–$100 per month**. Real model prices and usage remain to be benchmarked.
- Explore reusing existing speakers as audio outputs where feasible; their microphones must not be assumed accessible.
- Candidate affordable ESP32-based voice satellites require actual full-duplex, acoustic echo cancellation and barge-in validation before buying many.
- Public collaboration expected, but license selection is pending. Public visibility alone does not confer open-source licensing rights.

## Boundaries and deferred features

The P0 prototype does not need satellite hardware, always-on deployment, Home Assistant, OpenClaw, comprehensive persistent memory or seamless room tracking. Those are subsequent milestones; do not mistake their absence from P0 for cancellation of the final requirements.

## Source of truth and uncertainty

- **Accepted decisions:** docs/DECISION_LOG.md and linked ADRs.
- **Current execution:** docs/PROJECT_STATE.md and GitHub issues/PRs.
- **Design and uncertainties:** docs/architecture/ and docs/OPEN_QUESTIONS.md.
- **Engineering instructions:** AGENTS.md and docs/WORKFLOW.md.
- **Conversation itself:** exploration and supporting rationale, not the only enduring record.

If documentation disagrees with implemented behavior, report the discrepancy rather than silently treating one as accurate.
