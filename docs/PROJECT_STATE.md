# Wanda — Current project state

**As of:** 2026-10-15. **Phase:** Runnable V0 and encrypted recovery published for
review; synthetic live voice connection verified. **V1 is not complete.**
Main remains untouched by this implementation.

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
  also passed. [PR #8](https://github.com/arthurlorente/wanda/pull/8) is open,
  unmerged; exact commit/run evidence is in [checkpoint](DEVELOPMENT_CHECKPOINT.md).
- Password-encrypted local memory backup, decrypt/inspect preview and explicit
  merge restore in [PR #9](https://github.com/arthurlorente/wanda/pull/9), stacked
  on PR #8. The 126-test Python suite passed all six platform/version jobs;
  six Web Crypto tests and 20 browser workflows passed locally and in Linux CI.
  [Recovery CI](https://github.com/arthurlorente/wanda/actions/runs/38702654185).

## Decisions and limitations

Accepted product requirements D-001–D-049 remain unchanged. [ADR 0008](adr/0008-v0-portable-stack.md)
records **provisional** Python/native-JS/SQLite/loopback architecture, comparison
with TypeScript alternatives, boundaries and reversal. These are implemented
choices for review, not owner-approved production policy.

The V0 local OS-user capability is not multi-resident authentication. Database and
exports are plaintext with file permissions. Automatic extraction is deliberately
narrow. Home grants/audit reset on restart. Cloud voice has no saved memory, home
or computer tools. No raw audio or transcript archive exists. Provider costs and
quality and realistic household cost are not measured. A privately configured key
was used for metadata/configuration checks and two synthetic connection attempts;
one completed inference has a conservative US$0.006424 estimate. No physical device, private household data, account
creation, billing change or automatic merge was used by development.

## Authorized development in progress

Owner approved encrypted local backup/restore (D-051) and retained all saved
memories locally (D-050). Recovery is implemented in the unmerged PR #9.
Work continues on `codex/wanda-voice-validation`, based on PR #9. Synthetic live
voice testing has a session-specific **US$10 total** ceiling (D-052), replacing
the original US$5 ceiling before any paid call. The private key is configured.
A durable private spending ledger, strict synthetic input, bounded output and
server-side cleanup gate the tests; no real devices are authorized. New work
stops at 11:00am New York (15:00 UTC) on 2026-10-15 or an actual usage limit.

## Next actions and blockers

1. Owner: try [MORNING_HANDOFF](MORNING_HANDOFF.md); no account or key needed.
2. Review ADR0008, storage/authentication boundary and [provider evidence](PROVIDERS.md).
3. Have the owner manually test
   pauses, interruptions, languages, disclosure and measured cost. Private key
   setup is complete; no additional owner decision blocks unattended development.
   The two planned live attempts are complete; continue offline reliability work.
4. Configure one safe Home Assistant light and have the owner personally validate
   permissions and observed state. No unattended household actions.
5. Add real voice-memory integration only after resolving unavoidable live-audio
   disclosure and identity/consent. Keep [Issue #7](https://github.com/arthurlorente/wanda/issues/7)
   open until all V1 criteria have evidence.
6. Review licensing ([#6](https://github.com/arthurlorente/wanda/issues/6)), the
   implemented backup design, robust household authentication and durable home audit.

Satellite hardware, wake word, voiceprints, room handoff and general computer
agents remain later. See [acceptance mapping](testing/V0_ACCEPTANCE.md),
[human actions](HUMAN_ACTIONS_REQUIRED.md) and [checkpoint/PR](DEVELOPMENT_CHECKPOINT.md).
