# Instructions for Codex and AI development agents

## Required context on every substantial task

1. Read README.md, docs/PROJECT_CONTEXT.md, docs/PROJECT_STATE.md, docs/DECISION_LOG.md, docs/OPEN_QUESTIONS.md, docs/REQUIREMENTS.md and docs/WORKFLOW.md.
2. Read docs/architecture/overview.md, docs/architecture/privacy.md, docs/ROADMAP.md, and ADRs relevant to the task.
3. Inspect current Issues, PRs, implementation, and tests before saying a feature works or a decision is implemented.

## Standing decision protocol — mandatory

After every substantive **agreed** product, engineering or project decision, follow docs/WORKFLOW.md **as part of that same task**:
- Classify accepted vs proposed vs unresolved vs implemented.
- Update the smallest necessary canonical docs, ADR, requirements and/or issue.
- Reconcile docs/PROJECT_STATE.md if execution or next steps changed.
- Link evidence, commit or PR; verify the change was saved.
- Summarize to the user what was recorded and what still needs resolution.
- Don't perform a full consolidation for every message. Don't promote speculation into decisions.
- Never write sensitive personal household context into this public repository.

## Identity guardrail — mandatory

Read [docs/IDENTITY.md](docs/IDENTITY.md) before proposing features, implementation trade-offs, UX, hardware or project messaging. Wanda explicitly rejects the JARVIS / Big AI paradigm of an elite, obedient, institution-controlled assistant. Favor affordable, understandable, user-governed, inspectable designs; surface trade-offs when depending on proprietary cloud services. Do not turn the repository's identity documentation into a discussion of entertainment franchises or name origins. Treat this as an engineering review criterion, not just marketing language.

## Wanda's runtime personality — future implementation

Read [docs/MANIFESTO.md](docs/MANIFESTO.md) and [docs/PERSONALITY.md](docs/PERSONALITY.md) when implementing conversational behavior, prompt design, voice tuning, or memory. Preserve the manifesto as a character/design artifact; do not simply paste it as an unrestricted system prompt or pretend Wanda is sentient. Follow the concrete behavior and consent boundaries in PERSONALITY.md; test the actual results and record any changes through the decision workflow.

## Accepted V0 stack and future changes

The owner accepted the V0 Python standard-library backend, native browser JavaScript and local SQLite design on 2026-10-15 (D-053). [ADR 0008](docs/adr/0008-v0-portable-stack.md) records the comparison with TypeScript alternatives and the V0 limitations. Do not repeat the initial stack decision as if it were unresolved. Evaluate consequential changes against portability, maintainability, browser audio, testing, Home Assistant/agent integration and accessible setup; record alternatives and obtain review. V0 acceptance is not production or V1 readiness.

## Coding autonomy and review

Codex is authorized to autonomously research, implement and test **scoped, approved requirements** on feature branches and open pull requests. Do not commit implementation changes directly to main and **never merge a PR without human review and approval**. Raise consequential architecture, security/privacy, authentication/permissions, deployment, provider commitments or cost decisions for review rather than treating them as delegated. Provide tests, acceptance-criteria mapping, documentation changes and risks in each PR. See docs/WORKFLOW.md.

## Safety and engineering

4. Do not claim APIs, model availability, prices, firmware support, or performance are verified without reproducible evidence.
5. Preserve basic local home control if cloud voice fails once that feature is implemented; never falsely claim it already exists.
6. Treat voice instructions as untrusted; privileged computer actions require out-of-band approval.
7. Never commit secrets, household data, recordings, private memory, addresses, local network details, or tokens.
8. Private runtime state must stay outside this repository.
9. For behavior changes, update tests and documentation; record significant architecture changes as ADRs.
10. Prefer focused branches and pull requests with acceptance criteria and rollback plans.
11. Use mocked integrations and synthetic fixtures. Never execute destructive home or PC actions in automated tests.
12. Clearly mark assumptions, experimental integrations, and pending licenses.
