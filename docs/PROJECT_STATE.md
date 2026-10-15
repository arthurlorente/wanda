# Wanda — Current project state

**As of:** 2026-10-15. **Phase:** Owner-approved V0 merged into `main` through
PRs #8–#12; encrypted recovery and synthetic live voice connection verified.
**V1 is not complete.** D-053 records acceptance of the current design for V0.
The final implementation merge is
[`dec8f8a`](https://github.com/arthurlorente/wanda/commit/dec8f8a6f03ee408071ce7e23c1eb2f0c4987bd1).
Its tree matches the approved demo, and [main CI](https://github.com/arthurlorente/wanda/actions/runs/38749589357)
passed all six OS/Python jobs, 47 browser workflows and ZIP delivery.

## Implemented and locally verified

- Browser interface with scripted English/Portuguese/Spanish conversation,
  versioned persona, visible microphone/mode state and local privacy panels.
- Python 3.11+ standard-library server; no runtime packages or GPU. Mac/Windows
  start/stop/configure launchers and portable CLI/doctor.
- Real opt-in SQLite memory outside Git, conservative selective capture,
  sensitive/uncertain review, inspection/edit/export/delete/disable, expiry and
  restart persistence. Owner/provider/category consent engine and atomic one-time
  grants; no saved-memory cloud transmission in V0.
- Deny-default per-light/action permissions, separate confirmations, revocation,
  audit, duplicate suppression and truthful state/outage handling with fake lights.
- Optional OpenAI WebRTC SDP adapter and bounded Home Assistant REST light adapter.
  Device control is verified with synthetic mocks, **not real household devices**.
  A synthetic OpenAI WebRTC response completed with audio packets, transcript,
  bounded usage and confirmed server hangup. Microphone/listening/turn-taking
  acceptance remains pending; see [live evidence](testing/LIVE_VOICE.md).
- 89 Python tests passed on macOS Python 3.14.5; 11 installed-Chrome browser
  workflows passed with synthetic microphone/WebRTC APIs. Launcher subprocess
  start/reopen/stop/restart verified. Node syntax and diff checks passed.
- The same 89-test suite, doctor and JS syntax checks passed in all six macOS,
  Linux and Windows CI jobs on Python 3.11/3.14; Linux Chromium browser checks
  also passed. [PR #8](https://github.com/arthurlorente/wanda/pull/8) is merged;
  exact commit/run evidence is in [checkpoint](DEVELOPMENT_CHECKPOINT.md).
- Password-encrypted local memory backup, decrypt/inspect preview and explicit
  merge restore in [PR #9](https://github.com/arthurlorente/wanda/pull/9), stacked
  on PR #8. The 126-test Python suite passed all six platform/version jobs;
  six Web Crypto tests and 20 browser workflows passed locally and in Linux CI.
  [Recovery CI](https://github.com/arthurlorente/wanda/actions/runs/38702654185).
- Connection fixes and bounded live harness in [PR #10](https://github.com/arthurlorente/wanda/pull/10):
  160 Python tests passed across all six platform/version jobs; six encryption,
  five harness-input and 20 browser checks passed in
  [CI](https://github.com/arthurlorente/wanda/actions/runs/38708512976).
- Browser follow-up sequencing now waits for matching cancellation acknowledgements,
  preserves one queued message and additional drafts, and disconnects on missing
  acknowledgements. The follow-up branch passed **31 browser workflows** locally
  and in [Linux CI](https://github.com/arthurlorente/wanda/actions/runs/38709595553),
  alongside all six platform/version jobs;
  provider event races and microphone quality are still not verified live.

## Decisions and limitations

Accepted product requirements D-001–D-049 remain unchanged. D-053 accepts the
current implementation for V0. [ADR 0008](adr/0008-v0-portable-stack.md) records
Python/native-JS/SQLite/loopback architecture, comparison with TypeScript alternatives,
boundaries and reversal. This is not approval for production deployment or V1 release.

The V0 local OS-user capability is not multi-resident authentication. Database and
exports are plaintext with file permissions. Automatic extraction is deliberately
narrow. Home grants/audit reset on restart. Cloud voice has no saved memory, home
or computer tools. No raw audio or transcript archive exists. Conversational
quality and realistic household cost are not measured. A privately configured key
was used for metadata/configuration checks and two synthetic connection attempts;
one completed inference has a conservative US$0.006424 estimate. No physical device, private household data, account
creation, billing change or automatic merge was used by development.

## Accepted V0 delivery and remaining work

Owner approved encrypted local backup/restore (D-051) and retained all saved
memories locally (D-050). Recovery is implemented in merged PR #9.
TLS/SDP fixes and live evidence are in [PR #10](https://github.com/arthurlorente/wanda/pull/10),
stacked on PR #9. Tested browser follow-up response sequencing is on
[PR #11](https://github.com/arthurlorente/wanda/pull/11), based on PR #10. Synthetic live
voice testing has a session-specific **US$10 total** ceiling (D-052), replacing
the original US$5 ceiling before any paid call. The private key is configured.
A durable private spending ledger, strict synthetic input, bounded output and
server-side cleanup gate the tests; no real devices are authorized. New work
stops at 11:00am New York (15:00 UTC) on 2026-10-15 or an actual usage limit.

The merged increment in [PR #12](https://github.com/arthurlorente/wanda/pull/12)
on `codex/wanda-demo-recovery` preserves browser drafts
across delayed/failed requests, stops the selected instance despite unrelated
config errors, and provides a reproducible ZIP for launch without Git. **180 Python
tests and 47 browser workflows passed locally**. The extracted app also passed
startup, local memory persistence/deletion, mock-light permissions and shutdown
with no Git in PATH. [Corrected CI](https://github.com/arthurlorente/wanda/actions/runs/38746282007)
passed all six OS/Python jobs, the 47 browser workflows and ZIP delivery.
[Download the demo ZIP](https://github.com/arthurlorente/wanda/actions/runs/38746282007/artifacts/11979560780)
(GitHub sign-in may be needed; expires October 22). No new privacy permission
or provider commitment is introduced. Python is still required to run the ZIP.
A final review found delayed deletion could erase newer drafts; the same protection
now covers one/all memory deletions and truthful post-delete refresh failures.
**47 browser workflows passed locally and in the final CI run linked above**.
A local instance is available for owner review; keep the verified demo stable.

## Next actions and blockers

1. V0 is accepted and merged. Use [MORNING_HANDOFF](MORNING_HANDOFF.md) for launch
   and the remaining walkthrough; no account or key is needed for the default demo.
2. Before broader household use, review [provider evidence](PROVIDERS.md), privacy
   and authentication boundaries. V0 acceptance does not resolve those V1 gates.
3. Complete a documented human voice evaluation of pauses, interruptions, languages,
   disclosure and measured cost. Quick owner demo feedback is positive but does not
   constitute the full acceptance protocol. Both planned synthetic attempts are
   exhausted; no additional paid inference is authorized for development.
4. Home Assistant setup and the owner-operated single-light test are deferred to a
   later session. Do not operate real devices unattended or treat setup as verified.
5. Saved-memory cloud integration requires a new explicit owner decision changing
   D-050, as well as privacy and identity review. OpenClaw is not connected.
   Keep [Issue #7](https://github.com/arthurlorente/wanda/issues/7) open until all V1
   criteria have evidence.
6. Review licensing ([#6](https://github.com/arthurlorente/wanda/issues/6)), robust
   household authentication and durable home audit. Use new feature branches and
   human-approved PRs for subsequent changes.

Satellite hardware, wake word, voiceprints, room handoff and general computer
agents remain later. See [acceptance mapping](testing/V0_ACCEPTANCE.md),
[human actions](HUMAN_ACTIONS_REQUIRED.md) and [checkpoint/PR](DEVELOPMENT_CHECKPOINT.md).
