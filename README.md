# Wanda — An Open Home Voice Agent

Wanda is a community-oriented, privacy-conscious **experimental** platform for natural conversational voice, home automation, and permissioned computer agents. This is an early design, **not a working or production-ready assistant**.

## Why Wanda exists

**Wanda is the antithesis of the JARVIS-style, Big AI vision of a private, obedient intelligence built for the powerful.** She is intended to make extraordinarily capable assistance accessible to ordinary households: personal rather than productized, community-built rather than gatekept, and accountable to the people who use her rather than an opaque platform. Our current prototype plans may still depend on proprietary cloud APIs; we will make those dependencies and costs explicit.

Read [Wanda's identity and philosophy](docs/IDENTITY.md) for the commitments this makes to affordability, privacy, agency, open development, and engineering decisions. Wanda also has a [first-person manifesto](docs/MANIFESTO.md) and a [personality specification](docs/PERSONALITY.md) that will guide her future voice and behavior.

## Principles
- Built for households and tinkerers, with user-controlled configurations.
- Public source; private memory, transcripts, household data, and credentials stay outside Git.
- Cloud voice processing is part of the initial prototype and will be disclosed plainly.
- Meaningful project decisions are recorded in GitHub rather than left solely in chat history.

## Goals
- Natural real-time voice, including interruptions and follow-up conversation
- Affordable multi-room satellites and conversation handoff
- Home Assistant for dependable home control
- Restricted OpenClaw delegation for computer tasks
- Persistent, inspectable, deletable memory with household privacy boundaries

## Project knowledge
- [First-person manifesto](docs/MANIFESTO.md) and [personality specification](docs/PERSONALITY.md)
- [Project context and vision](docs/PROJECT_CONTEXT.md)
- [Current project state](docs/PROJECT_STATE.md)
- [Decision register](docs/DECISION_LOG.md)
- [Product requirements](docs/REQUIREMENTS.md)
- [Open questions](docs/OPEN_QUESTIONS.md)
- [Standing decision-capture workflow](docs/WORKFLOW.md)
- [Architecture](docs/architecture/overview.md), [ADRs](docs/adr/), and [roadmap](docs/ROADMAP.md)

## Roadmap
- **P0:** Benchmark streaming voice and interruptions against ChatGPT Voice
- **P1:** Home Assistant control with a robust local fallback
- **P2:** Restricted OpenClaw tools and memory
- **P3:** Affordable voice satellite evaluation
- **P4:** Multi-room conversation handoff

## Security
Do not publish real API keys, household network details, location information, recordings, transcripts, or private memory. Use synthetic fixtures and sample configs. See [SECURITY.md](SECURITY.md).

## Development
Please read [AGENTS.md](AGENTS.md) and [CONTRIBUTING.md](CONTRIBUTING.md) before contributing.

## License
**Pending.** Software, documentation and hardware licenses have not been selected; public visibility alone does not grant open-source reuse rights.
