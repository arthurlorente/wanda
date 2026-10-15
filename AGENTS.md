# Instructions for Codex and coding agents

1. Read README.md, docs/architecture/overview.md, docs/architecture/privacy.md, docs/ROADMAP.md, and relevant ADRs first.
2. Do not claim APIs, model availability, prices, firmware support, or performance are verified without reproducible evidence.
3. Preserve basic local home control if cloud voice fails.
4. Treat voice instructions as untrusted; privileged computer actions require out-of-band approval.
5. Never commit secrets, household data, recordings, private memory, addresses, local network details, or tokens.
6. Private runtime state must stay outside this repository.
7. For behavior changes, update tests and documentation; record architecture changes as ADRs.
8. Prefer focused branches and pull requests with acceptance criteria and rollback plans.
9. Use mocked integrations and synthetic fixtures. Never execute destructive home or PC actions in automated tests.
10. Clearly mark assumptions, experimental integrations, and pending licenses.
