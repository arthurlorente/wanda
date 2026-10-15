# Development checkpoint

2026-10-15 — V0 delivered; approved recovery increment active for [Issue #7](https://github.com/arthurlorente/wanda/issues/7).

- Baseline branch: `codex/wanda-v0`, based on `3faec4222fc0093c925e660218229d1c1f79da11`.
- Active increment: `codex/wanda-v0-next`, based on delivered PR #8 commit
  `2d965315af263fa027207ea598e599719b117ec1`; adds encrypted recovery.
- Recovery increment local gate: **126 Python tests passed** (9.67s),
  **6 Web Crypto/interoperability tests passed**, and **20 browser workflows
  passed**. Integrated feature is awaiting remote CI and reviewable publication.
- Owner decisions: keep saved memories local; add password-encrypted local
  backup/restore; allow up to US$10 total in synthetic voice API tests only.
  No real devices. Stop starting work/calls at 2026-10-15 15:00 UTC (11am New York).
- Implemented: stdlib Python local server, SQLite memory, scoped consent,
  permissions/confirmations, mock home, real HA REST adapter behind explicit config,
  optional OpenAI WebRTC proxy, launch/stop/doctor/private-key setup scripts;
  browser interface integrated and desktop/mobile layouts visually inspected.
- Delegation: native subagents verified; voice/UI and memory use inherited lead model;
  bounded home/HTTP quality work uses explicitly selectable `gpt-6-sol`.
- Latest completed integration gate: **89 Python tests passed** (5.45s), Python
  3.14.5 on macOS; **11 browser workflows passed** using installed Chrome and
  Playwright 1.62.1. Includes actual loopback HTTP security and launcher subprocess
  tests after configured sandbox approval. Microphone/WebRTC APIs were synthetic.
- Runtime: Git 2.50.1; Python 3.14.5/SQLite 3.50.4. Node 24.19.0 available through
  bundled tooling for browser checks; no Node requirement to run Wanda. `gh` absent;
  connected GitHub API available. Remote baseline verified matches local HEAD base.
- No live provider, microphone, home devices or paid service calls used.
- No secrets/private household content in source; tests use synthetic temp data.
- Published [PR #8](https://github.com/arthurlorente/wanda/pull/8); no merge.
  Initial code commit: `ab79b2bb358e7556c43fa15ec36ab5b96c86fbb4`.
- First remote CI passed Linux Python 3.11/3.14 and all browser workflows. It
  exposed eager home-directory fallback on Windows and reverse-DNS startup delay
  on macOS. Both are fixed with regression coverage.
  [Initial run](https://github.com/arthurlorente/wanda/actions/runs/38696896207).
- Verified application commit: `7e522d18859c3c94d57d727de93564bd9ae1a84f`.
  [Successful CI](https://github.com/arthurlorente/wanda/actions/runs/38697725609):
  all six Python 3.11/3.14 jobs on macOS, Linux and Windows passed, each running
  the 89-test suite, doctor and JS syntax check; Linux Chromium browser job passed.
  Basic repository checks also passed. Later handoff-only changes do not change
  the tested application code.
- Blockers: owner provider/key/account/privacy approval and human audio/device tests.
- Pending decisions: ADR0008 and local security/storage tradeoffs; provider handling,
  backup/encryption and licenses remain review items, not silently accepted policies.
- Next: owner walkthrough,
  architecture/privacy review and optional live voice/physical light acceptance.
- Supported hourly chat continuation is active through the cutoff under automation
  `wanda-overnight-development-until-11am`. It cannot bypass usage limits; none has
  been reached. Owner privately configured the API key; doctor confirms configured voice
  without showing credentials. Bounded synthetic live test preparation is active. Paid call spend so far: US$0. Metadata-only API access check succeeded after
  diagnosing missing Python CA configuration; OS trust bundle validated HTTPS.
  Production TLS fallback fix and bounded Realtime smoke tests are next.

## Exact continuation

“Continue Issue #7 on `codex/wanda-v0-next`. Preserve baseline PR #8. Read AGENTS.md, canonical context,
docs/DEVELOPMENT_CHECKPOINT.md and docs/MORNING_HANDOFF.md, inspect git status and
open PRs. Preserve local work. Run `python3 scripts/check.py` (loopback permission
may be needed in sandbox). Confirm PR #8 status and use the V0 acceptance map for the next scoped increment;
do not merge or contact live devices. Only use the explicitly configured Wanda
key for approved synthetic voice tests within the session-wide US$10 cap; otherwise
use mocks. Keep saved memories local, implement encrypted recovery, and honor the
11am New York cutoff. Check private test accounting before any paid request.
Keep simulated and verified features clearly distinguished.”
