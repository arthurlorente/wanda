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
