# Development checkpoint

2026-10-15 — active unattended implementation for [Issue #7](https://github.com/arthurlorente/wanda/issues/7).

- Branch: `codex/wanda-v0`, based on `3faec4222fc0093c925e660218229d1c1f79da11`.
- Implemented: stdlib Python local server, SQLite memory, scoped consent,
  permissions/confirmations, mock home, real HA REST adapter behind explicit config,
  optional OpenAI WebRTC proxy, launch/stop/doctor/private-key setup scripts;
  browser interface integrated and desktop/mobile layouts visually inspected.
- Delegation: native subagents verified; voice/UI and memory use inherited lead model;
  bounded home/HTTP quality work uses explicitly selectable `gpt-6-sol`.
- Latest completed integration gate: **87 Python tests passed** (6.26s), Python
  3.14.5 on macOS; **11 browser workflows passed** using installed Chrome and
  Playwright 1.62.1. Includes actual loopback HTTP security and launcher subprocess
  tests after configured sandbox approval. Microphone/WebRTC APIs were synthetic.
- Runtime: Git 2.50.1; Python 3.14.5/SQLite 3.50.4. Node 24.19.0 available through
  bundled tooling for browser checks; no Node requirement to run Wanda. `gh` absent;
  connected GitHub API available. Remote baseline verified matches local HEAD base.
- No live provider, microphone, home devices or paid service calls used.
- No secrets/private household content in source; tests use synthetic temp data.
- GitHub publishing/PR still pending; no merge.
- Blockers: owner provider/key/account/privacy approval and human audio/device tests.
- Pending decisions: ADR0008 and local security/storage tradeoffs; provider handling,
  backup/encryption and licenses remain review items, not silently accepted policies.
- Next: publish reviewable branch/PR and verify remote CI. Then owner walkthrough,
  architecture/privacy review and optional live voice/physical light acceptance.
- No automatic resumption is configured; no limit has been reached. Native usage
  snapshot during work reported 2% of weekly allowance used.

## Exact continuation

“Continue Issue #7 on `codex/wanda-v0`. Read AGENTS.md, canonical context,
docs/DEVELOPMENT_CHECKPOINT.md and docs/MORNING_HANDOFF.md, inspect git status and
open PRs. Preserve local work. Run `python3 scripts/check.py` (loopback permission
may be needed in sandbox). Complete outstanding V0 tests/docs and reviewable PR;
do not merge, access private credentials, contact live devices or spend on APIs.
Keep simulated and verified features clearly distinguished.”
