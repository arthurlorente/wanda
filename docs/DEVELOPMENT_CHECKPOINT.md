# Development checkpoint

2026-10-15 — Runnable V0 and encrypted recovery published; bounded synthetic
voice connection verified for [Issue #7](https://github.com/arthurlorente/wanda/issues/7).
V1 is not complete. Main has not been changed or merged.

## Branches and delivery

- [PR #8](https://github.com/arthurlorente/wanda/pull/8): `codex/wanda-v0`, base main.
  Latest handoff commit `2d965315af263fa027207ea598e599719b117ec1`.
- [PR #9](https://github.com/arthurlorente/wanda/pull/9): `codex/wanda-v0-next`,
  stacked on PR #8. Encrypted memory recovery. Latest verified commit
  `4d02c03c3e073fc4ebeff22ba9b24537889c180f`.
- [PR #10](https://github.com/arthurlorente/wanda/pull/10): `codex/wanda-voice-validation`,
  stacked on PR #9. HTTPS trust repair, exact SDP preservation and bounded live
  evidence. Latest verified commit `d6dee615ec71460b092ca9c293fc2154cfd9061e`.
- [PR #11](https://github.com/arthurlorente/wanda/pull/11): `codex/wanda-live-turns`,
  stacked on PR #10. Browser response sequencing passed local tests and independent
  review. Implementation commit `5342454346d175e4a9eb00c1ffa69f6d1585a3d9`;
  final handoff `17d71d547c8075535715daa2414b2aa971731b92` passed
  [all CI jobs](https://github.com/arthurlorente/wanda/actions/runs/38709876678).
- [PR #12](https://github.com/arthurlorente/wanda/pull/12): active cumulative branch
  `codex/wanda-demo-recovery`, based on PR #11. Local draft-loss/stop recovery and
  a committed-source ZIP builder. Implementation commit
  `7a6d452f6b4e21fc9746d68adfe9f6b69c07a525`; local integration and extracted startup passed.
- Keep all PRs unmerged for human review. Preserve private runtime state outside Git.

## Implemented state

- Python standard-library loopback server, native browser UI, scripted EN/PT/ES
  persona, real opt-in local SQLite memory with review/deletion/expiry, scoped
  disclosure policy records, mock home and deny-default light permissions.
- Optional OpenAI WebRTC and Home Assistant REST adapters. Cloud voice has no saved
  memory, home or computer tools. Home Assistant is transport-mock tested only.
- Portable launch/stop/doctor/private-key configuration scripts; no runtime packages
  or GPU. Local OS-user boundary, plaintext working database/config, no resident
  authentication or wake word. Home grants/audit reset on restart.
- Encrypted local memory download, password-based browser decryption, paged preview
  and explicit atomic merge. Backups exclude credentials, identities and grants.
  See ADR 0009 and BACKUP.md; the working database remains unencrypted.
- Private key is configured. The second bounded synthetic WebRTC attempt completed
  one response with audio packets/transcript, zero microphone/input audio, and
  confirmed provider hangup. No real microphone or listening quality is claimed.
- Missing Python CA configuration on the development Mac was diagnosed. Narrow
  fallback to the OS certificate bundle preserves certificate/hostname checks;
  voice and HA adapters share the helper. No TLS verification bypass exists.
- Browser tracks requested, active and cancelling responses, waits for matching
  acknowledgements, retains one queued typed turn and additional draft, and drops
  unsent work on disconnect. One correlated automatic-response conflict retry
  never duplicates typed text; fifteen-second missing acknowledgements disconnect.
- Delayed memory saves preserve newer drafts/selected edits and reject duplicate
  pending submissions. Failed chat restores only an untouched composer; Clear chat
  and newer drafts survive. Lost mutation responses disclose uncertain outcomes
  without automatic retry; a failed refresh cannot undo a confirmed write/reply.
- Stop resolves the selected data folder without unrelated configuration validation,
  preserves explicit environment precedence, and reports corrupt/unreachable state
  honestly. Unknown custom folders require the original window or repaired config;
  no process scanning, token guessing or cross-folder shutdown is introduced.
- A deterministic source ZIP includes only allowed committed Git blobs, launchers,
  docs and templates, with a commit/hash manifest. Untracked/ignored runtime files,
  local Git object replacements, links/submodules and development harnesses cannot
  enter through the builder. Python remains required; Git is not needed at runtime.

## Tests and evidence

- Baseline: 89 Python tests plus 11 browser workflows; all six Windows/macOS/Linux
  Python 3.11/3.14 jobs and Linux browser job passed.
  [Baseline CI](https://github.com/arthurlorente/wanda/actions/runs/38697725609).
- Recovery: 126 Python tests, six actual Web Crypto/interoperability tests and
  20 browser workflows passed locally. All six platform/version jobs and Linux
  browser job passed [recovery CI](https://github.com/arthurlorente/wanda/actions/runs/38702654185).
- Initial recovery CI exposed a macOS test-client race during correct early HTTP
  413 rejection. The test now sends an oversized Content-Length without its body;
  the expected rejection remains asserted. The corrected run above passed.
- Final TLS/SDP/harness gate: **160 Python tests passed** in 10.987s, including
  real loopback auth/cleanup with fake provider, budget limits and SDP preservation.
  **Six crypto and five child-input tests passed**; **20 browser workflows passed**
  before the final SDP change (covered by Python and actual live smoke). Final
  [PR #10 CI](https://github.com/arthurlorente/wanda/actions/runs/38708512976)
  passed all six platform/version jobs and the browser job at `d6dee615ec71460b092ca9c293fc2154cfd9061e`.
  CI corrections fixed a Windows path assertion in a macOS mock and another macOS
  test-client early-413 race; actual body-size rejection assertions remain intact.
- Browser sequencing follow-up: **31 local Chrome workflows passed**, with no
  page errors or external requests. JavaScript syntax and diff checks passed.
  An independent agent reviewed request correlation, queued-message preservation,
  conflict retry, disconnect guards and backup privacy transitions. Its two
  findings (late audio clear and updated preferences on retry) have regressions.
  [Follow-up CI](https://github.com/arthurlorente/wanda/actions/runs/38709595553)
  passed all six platform/version jobs and Linux Chromium browser checks at
  `5342454346d175e4a9eb00c1ffa69f6d1585a3d9`; basic repository checks also passed.
- Actual microphone, listening quality, natural pauses, spoken interruptions and
  physical device behavior still require human testing. No household data used.
- Recovery/delivery local gate: **178 Python tests passed** in 22.265s and **41
  Chrome browser workflows passed**. Ten bundle tests cover committed snapshots,
  exclusions, deterministic bytes, permissions, overwrite refusal and extracted
  doctor without Git. Eighteen launcher/config tests cover corrupt configuration,
  folder scoping and truthful shutdown. Node syntax and diff checks passed.
  [Initial remote CI](https://github.com/arthurlorente/wanda/actions/runs/38712291597)
  passed Linux/macOS and 41 browser workflows. Windows exposed eager home-directory
  lookup before honoring an explicit private configuration file in an isolated
  environment. Lazy config resolution now honors the explicit file before requiring a home
  directory; 20 focused tests passed, including missing-home regressions and safe
  error reporting. Corrected remote CI is pending. Artifact upload correctly
  stayed blocked on the initial failed CI. The full corrected local suite passed
  **180 Python tests** in 23.100s; browser code is unchanged from the 41-workflow pass.
- The exact PR #12 commit ZIP (65 files) was extracted with macOS `ditto`, preserving
  executable launcher mode. With no Git in PATH and fresh external synthetic state,
  the app started, served the UI, kept cloud voice disabled, captured a consented
  preference, retained it after restart, deleted it, enforced deny/grant/mock-light
  control and stopped cleanly. Zero external calls. ZIP SHA-256:
  `96bf48ec21158f1cbbdbb5f9bcec434a043aa38f02b75a474baf63842d6c7a55`.
  Local artifact: `dist/wanda-demo-7a6d452f6b4e.zip` (ignored, not committed).

## Authorization, limits and blockers

- D-050: all saved memories stay local. D-051: encrypted local recovery approved.
  D-052: **US$10 total** synthetic voice test ceiling, replacing the original US$5
  before paid calls. No real devices, new accounts, billing changes or automatic merges.
- Stop starting new work/calls at **2026-10-15 15:00 UTC (11am New York)** or an
  actual usage limit. Last usage check reported 37% of the account window used;
  ordinary usage was allowed. Do not consume reset credits or bypass limits.
- Supported hourly chat continuation is active through that cutoff under
  `wanda-overnight-development-until-11am`. It cannot bypass usage limits.
- No additional owner decision blocks current development. Later owner work:
  listening/manual voice acceptance, real light acceptance, provisional ADR review,
  household identity/privacy policy and license selection.
- Live attempt 1: provider HTTP 400 before any SDP answer or response creation.
  Exact SDP preservation fixed a protocol mutation. The failed attempt was explicitly
  reconciled as `setup_rejected`, estimated usage zero, retaining its full US$3 hold.
- Live attempt 2: **PASS**: session HTTP 201, one completed response, 38 input / 98
  output tokens, no input audio/image, 53 RTP packets/3433 bytes, transcript observed,
  zero microphone calls, both browser cleanup checks true, provider hangup HTTP 200.
  Conservative usage estimate **US$0.006424**, not a verified invoice.
- **Two-attempt limit exhausted; no further paid inference planned.** Private ledger
  holds **US$6**, not US$6 billed. Do not reset or refund the reservations.
- Harness reserves US$3 per attempt, at most two attempts, retaining reservations
  after failures. Never reset its ledger, silently refund a hold, or retry after
  uncertain usage/termination. See [live test protocol](testing/LIVE_VOICE.md).

## Next actions and exact continuation

1. Publish the tested lazy configuration lookup fix for Windows CI. Verify
   corrected PR #12 remote CI/artifact
   delivery and record the downloadable ZIP link. Root owns docs/Git; no other
   agent owns unfinished edits. Keep this cumulative checkout and all PRs unmerged.
2. PR #10 CI is verified successful. Do not repeat paid tests; both planned
   attempts are complete and live microphone/physical-device acceptance is deferred.
3. Continue useful scoped reliability/UX work before the cutoff; human-dependent
   acceptance remains deferred rather than fabricated. Update handoff/checkpoint.

Continuation instruction:
“Continue Issue #7 on `codex/wanda-demo-recovery` from this checkpoint. Read
AGENTS.md and required canonical context; inspect git status, current Issues/PRs
and the private synthetic-test accounting without exposing credentials. Preserve
unfinished work and keep PRs #8/#9/#10/#11/#12 unmerged. Native subagents are available and
explicitly authorized; use bounded ownership. Follow the approved US$10 total
session cap and 11am New York cutoff. The two-attempt harness limit is exhausted;
no further paid inference is planned, and no ledger reset/refund is permitted. Keep saved
memories local and use synthetic data only. Run `python3 scripts/check.py` and
appropriate browser/crypto checks; loopback/browser permissions may be needed.
Update this checkpoint, PROJECT_STATE and MORNING_HANDOFF with evidence and exact
next steps before a limit or interruption. Do not claim mocked audio or devices
are verified live.”
