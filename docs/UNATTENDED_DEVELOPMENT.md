# Unattended engineering autonomy — provisional architectural decisions

**Status:** Project-owner operating rule accepted 2026-10-15. Applies to Codex work under [V1 issue #7](https://github.com/arthurlorente/wanda/issues/7). No Codex task has been started by this document.

## Mandate

The lead orchestrator may make reasonable engineering, design, and architectural judgments autonomously when the owner is unavailable. Do not stall overnight merely because a tradeoff was not explicitly settled. Ground decisions in Wanda's manifesto, identity, trust/privacy principles, accepted decisions, requirements, and the objective of a working testable V0/V1.

## How to make a judgment

1. Read the relevant principles and past decisions; name the user-facing goal and tradeoff.
2. Prefer privacy, independence, consent, locality, openness, reliability and reversibility ahead of convenience or speed when conflicts arise.
3. Choose the simplest sound implementation that can be tested. Investigate available evidence and alternatives, favoring portable and replaceable components.
4. Implement the choice on an isolated feature branch with tests where practical. Do not merge automatically.
5. Record a **provisional** ADR in `docs/adr/` or a clearly labeled decision in the PR: context, options, chosen path, why it aligns with Wanda's principles, impact, evidence/tests, known risks, and exact rollback/replacement steps.
6. Include provisional decisions in the morning handoff under **Decisions for owner review**, with links to changes.
7. If tests fail, iterate independently; preserve useful work and document blockers clearly.

A decision made by an unattended agent is provisional, not an accepted product policy. Owner may accept, revise or revert.

## Parallel delegation

Use a strong reasoning model for overall architecture, security and integration. Delegate isolated bounded tasks to less costly available models when supported. Separate file ownership or use independent worktrees; orchestrator reviews and integrates results. Do not assume every Codex client has hierarchical heterogeneous-model agent features; inspect actual tool support and fall back to multiple independent tasks or sequential execution if necessary.

## Absolute boundaries for unattended execution

- No real household device operations, purchases, subscription changes, account administration, secret extraction, or releasing private data.
- Never bypass platform approval requirements or widen machine privileges beyond the configured sandbox.
- No automatic merge to main or destructive modification of unrelated branches.
- No silently changing accepted privacy, consent, safety or identity policies. Implement policy-compliant defaults or record a blocked dependency.
- Never claim tests, integration, provider terms or data protection guarantees not verified.
- Work with synthetic fixtures or safe local test environments; keep credentials, household identifiers, live recordings and real personal data out of Git.
- Keep cloud provider exposure explicitly disclosed; minimize personal context.

The objective is maximum **safe, reviewable** progress without requiring the owner to wake up.
