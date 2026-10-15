# ADR 0007 — V1 privacy-first agency and reliability

**Status:** Accepted product direction (D-044–D-049); implementation pending. 2026-10-15.

## Decision
Wanda's manifesto anchors her distinctive, warm, witty, discerning persona. Persona cannot bypass truthfulness, privacy or consent. Controlled autonomy permits proactively suggesting actions and autonomously executing only routine low-risk actions within explicit, user-defined scopes. Residents configure device/action permissions and confirmation thresholds; sensitive or out-of-scope actions require stronger approval. Actions must be interruptible, revocable and auditable.

Graceful degradation is required. When models, providers, or connectivity fail, use authorized local capabilities where available, preserve consented context safely, report uncertainty or incomplete actions accurately, and avoid risky automatic retries or duplicate device effects.

V1 requires a working Home Assistant device integration in addition to P0 natural multilingual voice and consented local persistent memory. This expands the user-facing V1 gate, not the earlier narrower P0 prototype. Integration and per-person permissions should be real and tested, not simulated as finished.

Privacy and independence override convenience or marginal performance improvements. Prefer local data/identities, minimal cloud context, replaceable providers, transparent dependencies, and explicit review of deviations. Cloud voice service use is a declared, measured compromise, never evidence of fully local processing.

## Consequences
- Implement in staged, reviewable PRs: portable voice, local memory/consent, bounded Home Assistant control, then V1 acceptance tests.
- Verify device state after each operation where possible; never conflate model intention with completed action.
- No voice biometric recognition, guest enrollment, wake word, satellites or room handoff required for initial V1.
- License, provider terms, and material privacy changes require project-owner approval. Codex can investigate and propose implementations but must not silently settle policy trade-offs.
- A first working demo or PR is not the same as a released V1.

Related: [Roadmap](../ROADMAP.md), [Requirements](../REQUIREMENTS.md), [Decision log](../DECISION_LOG.md), [V1 kickoff issue](https://github.com/arthurlorente/wanda/issues/7).
