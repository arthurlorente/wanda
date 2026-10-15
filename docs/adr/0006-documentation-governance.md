# ADR 0006 — GitHub-first documentation and decision capture

**Date:** 2026-10-15
**Status:** Accepted

## Context

Wanda is evolving through multi-session conversations and AI-assisted development. Important constraints and design reasons risk becoming trapped in chat history, forgotten, or contradicted by future agent work. Adding a parallel Notion architecture database could create competing sources of truth.

## Decision

- GitHub is canonical for code, requirements, ADRs, decisions, issues, PRs and execution state.
- ChatGPT is the exploration and decision-support environment; Codex reads canonical files and implements scoped changes.
- Use docs/WORKFLOW.md as the standing protocol: following each substantive decision, capture status, rationale, consequences and links in the correct repository document; update current state when relevant; confirm the write.
- Do **not** perform a full project-context rewrite after every minor decision. Run fuller reconciliations at meaningful milestones or when drift is detected.
- Defer Notion unless distinct nontechnical collaboration or private notebook needs emerge; prevent any secondary tool from superseding canonical architecture and requirements.
- Do not publish private household details when consolidating discussions.

## Alternatives considered

1. **Rely on chat memory:** rejected; neither deterministic nor a version-controlled engineering record.
2. **Notion as primary:** deferred; extra sync burden and poor coupling to implementation history.
3. **GitHub without consistent decision capture:** rejected; raw docs alone don't solve context drift.

## Consequences

Maintainers and agents must keep docs up to date. Commit/PR history provides an audit trail. Tools may not always have GitHub write access; when unable to write, state this clearly and prepare a patch rather than falsely claim persistence.

## Related

docs/PROJECT_CONTEXT.md, docs/PROJECT_STATE.md, docs/DECISION_LOG.md, docs/OPEN_QUESTIONS.md, AGENTS.md.
