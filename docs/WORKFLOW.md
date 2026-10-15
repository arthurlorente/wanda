# Wanda — Standing decision and context-capture protocol

**Adopted:** 2026-10-15
**Applies to:** ChatGPT-assisted planning, Codex implementation, maintainers, and future contributors.

## Purpose

An evolving conversation is a workspace, **not a dependable permanent project database**. GitHub is the canonical project record. Every **substantive** agreed decision that changes project direction, requirements, architecture, privacy or security boundaries, product behavior, schedule, ownership, or meaningful priorities must be recorded in GitHub.

This protocol is expected at the conclusion of every meaningful decision or milestone. It does **not** require a full-document rewrite after each message, and does **not** mean uncommitted ideas become binding choices.

## Routine after a decision

1. **Classify:** Is it an idea, proposal, accepted decision, rejected option, open question, or implemented/verified change? If unclear, do not mark accepted.
2. **Capture:** Update the smallest relevant canonical place:
   - docs/DECISION_LOG.md for consequential accepted/rejected/superseded decisions.
   - docs/adr/ for architecture or security trade-offs, including alternatives and consequences.
   - docs/REQUIREMENTS.md for accepted product requirements and tests.
   - docs/PROJECT_CONTEXT.md for durable identity, principles or global constraints.
   - docs/OPEN_QUESTIONS.md for unresolved assumptions and research.
   - A GitHub Issue for executable work, with criteria and links.
3. **Reconcile:** Update docs/PROJECT_STATE.md whenever current work, status, priority, blocker or next action changes. Cross-link issues, PRs and ADRs.
4. **Confirm:** Verify the GitHub write actually succeeded. Tell the user what changed with links. If tools fail or no repository access exists, explicitly state what **was not** recorded and provide a proposed patch instead.
5. **Never invent evidence:** An accepted requirement is not the same as a working feature. An idea is not an approved architecture.

## Development and pull-request policy

Codex may autonomously research, edit code, run tests, improve documentation and open pull requests within an agreed issue's scope and acceptance criteria. Work on a feature branch, never directly on main. Every implementation change must go through a human-reviewed pull request before merge; **do not auto-merge**. Escalate material architecture or provider choices, access-control/security/privacy changes, new recurring costs and destructive operations before implementing irreversible or high-impact changes. PRs must link relevant issues/ADRs, report test evidence and risks, and update project state and decision records when appropriate. Human review is required for merging; no specific reviewer count or branch protection settings have yet been configured.

## Planning questions

When offering choices about Wanda's development, include an optional open-text field so the project owner can add nuance, combine suggestions or propose a different approach. Treat this text as part of the answer. For simple conversational questions, no formal options are required.

## End of a meaningful work session

Review the session for unrecorded decisions, updated assumptions, open questions, risks and implementation outcomes. Consolidate minimally. A **full context-consolidation audit** is warranted after major pivots, long gaps, or when documentation becomes contradictory—not after every minor choice.

## Beginning of a new session

Read README.md, docs/PROJECT_CONTEXT.md, docs/PROJECT_STATE.md, docs/DECISION_LOG.md, docs/OPEN_QUESTIONS.md, AGENTS.md, and relevant ADRs/issues. Consult actual GitHub state before making claims of implementation. Never rely solely on ChatGPT memory or previous chat summaries.

## Privacy and publication

Before documenting anything from a chat:
- Omit personal identifiers, unneeded household details, addresses, passwords, network topology, real conversations, voice recordings and private data.
- Paraphrase general design intent rather than publishing a raw transcript.
- If a potentially sensitive or personal decision is worth retaining, seek an appropriate private record instead of putting it in public GitHub.
- Do not assume a private notebook can safely mirror every project conversation.

## Disagreements or unavailable memory

The user can change decisions. Log reversals with rationale and dated references, rather than erasing prior reasoning. If earlier conversations are unavailable, mark reconstructed conclusions as uncertain and ask only when the gap matters. Repository data should be checked against the latest code and Issues/PRs.
