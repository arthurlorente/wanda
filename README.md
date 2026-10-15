# Wanda — An Open Home Voice Agent

Wanda is a community-oriented, privacy-conscious **experimental** platform for natural conversational voice, home automation, and permissioned computer agents. This branch contains a runnable **V0 demonstration**, not a completed V1 or a production assistant.

## Try V0

On a Mac, double-click **Start Wanda.command** in this folder. On Windows,
double-click **Start Wanda.bat**. A browser opens automatically. Python 3.11 or
newer is the only runtime requirement; there are no packages to install, no GPU
requirement, and no API key needed for the local demo.

On Linux, or from a terminal on macOS:

```sh
python3 -m wanda
```

Keep the launcher window open. Use **Stop Wanda** or Control+C to stop.
See the plain-English [morning handoff](docs/MORNING_HANDOFF.md) for a five-minute
walkthrough, configuration, and what is simulated.
You can also use the [portable demo ZIP](docs/DEMO_BUNDLE.md): extract it and open
the same launcher, with no Git setup. Python is still required.

| Capability | V0 status |
| --- | --- |
| Browser conversation | Local scripted demo in English, Portuguese, Spanish; no general local AI |
| Persistent memory | Real local SQLite, opt-in, review/edit/export/delete and conservative selective capture |
| Home controls | Simulated lights by default; permissions, confirmation, verification and outage handling |
| Cloud voice | Synthetic OpenAI WebRTC audio response verified; explicit disclosure and server-only key. Microphone and conversational quality still need human testing |
| Home Assistant | Bounded REST light adapter with mocked transport tests; real devices not tested |
| Household identity | One local OS-user capability; no voice authentication or separate resident login |

No microphone starts automatically. No saved memory is sent to the voice provider.
Private state lives outside this repository. Real conversation and device
acceptance tests remain necessary for V1.

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
Run development checks from a repository checkout; the demo ZIP includes runtime
files and documentation, without the test/build tools.

```sh
python3 -m wanda --doctor    # Check runtime/config without contacting providers
python3 scripts/check.py    # Syntax, unit, integration and HTTP security tests
python3 -m wanda --stop     # Stop only this Wanda instance
```

No installation/build step is needed. The source files are the runnable artifact.
Optional browser regression checks are documented in [testing](docs/testing/V0_ACCEPTANCE.md).
Do not place real keys in `.env.example` or `config.example.json`.
For optional integrations, copy the JSON template to a private folder **outside**
this checkout and point `WANDA_CONFIG` to it. See [Voice](docs/VOICE.md),
[Memory](docs/MEMORY.md), [Home](docs/HOME.md), and [provisional architecture](docs/adr/0008-v0-portable-stack.md).

## License
**Pending.** Software, documentation and hardware licenses have not been selected; public visibility alone does not grant open-source reuse rights.
