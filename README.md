# Wanda — An Open Home Voice Agent

Wanda is a community-oriented, privacy-conscious **experimental** platform for natural conversational voice, home automation, and permissioned computer agents. This is an early design, **not a working or production-ready assistant**.

## Principles
- Built for households and tinkerers, with user-controlled configurations.
- Public source; private memory, transcripts, household data, and credentials stay outside Git.
- Cloud voice processing is part of the initial prototype and will be disclosed plainly.
- No affiliation with Marvel, HBO, or other entertainment franchises.

## Goals
- Natural real-time voice, including interruptions and follow-up conversation
- Affordable multi-room satellites and conversation handoff
- Home Assistant for dependable home control
- Restricted OpenClaw delegation for computer tasks
- Persistent, inspectable, deletable memory with household privacy boundaries

## Roadmap
- **P0:** Benchmark streaming voice and interruptions against ChatGPT Voice
- **P1:** Home Assistant control with a robust local fallback
- **P2:** Restricted OpenClaw tools and memory
- **P3:** Affordable voice satellite evaluation
- **P4:** Multi-room conversation handoff

See [roadmap](docs/ROADMAP.md), [architecture](docs/architecture/overview.md), and [decisions](docs/adr/).

## Security
Do not publish real API keys, household network details, location information, recordings, transcripts, or private memory. Use synthetic fixtures and sample configs. See [SECURITY.md](SECURITY.md).

## Development
Please read [AGENTS.md](AGENTS.md) and [CONTRIBUTING.md](CONTRIBUTING.md) before contributing.

## License
**Pending.** Software, documentation and hardware licenses have not been selected; public visibility alone does not grant open-source reuse rights.
