# Wanda — Current project state

**As of:** 2026-10-15. **Phase:** Runnable V0 on `codex/wanda-v0`, awaiting owner
review. **V1 is not complete.** Main remains untouched by this implementation.

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
  Provider/device transports are verified with synthetic mocks, **not live services**.
- 87 Python tests passed on macOS Python 3.14.5; 11 installed-Chrome browser
  workflows passed with synthetic microphone/WebRTC APIs. Launcher subprocess
  start/reopen/stop/restart verified. Node syntax and diff checks passed.
- Windows/Linux/Python 3.11 CI matrix configured; final remote results are recorded
  in [checkpoint](DEVELOPMENT_CHECKPOINT.md), not assumed from configuration.

## Decisions and limitations

Accepted product requirements D-001–D-049 remain unchanged. [ADR 0008](adr/0008-v0-portable-stack.md)
records **provisional** Python/native-JS/SQLite/loopback architecture, comparison
with TypeScript alternatives, boundaries and reversal. These are implemented
choices for review, not owner-approved production policy.

The V0 local OS-user capability is not multi-resident authentication. Database and
exports are plaintext with file permissions. Automatic extraction is deliberately
narrow. Home grants/audit reset on restart. Cloud voice has no saved memory, home
or computer tools. No raw audio or transcript archive exists. Provider costs and
quality are not measured. No live key, physical device, private household data,
account creation, billing change, purchase or automatic merge was used.

## Next actions and blockers

1. Owner: try [MORNING_HANDOFF](MORNING_HANDOFF.md); no account or key needed.
2. Review ADR0008, storage/authentication boundary and [provider evidence](PROVIDERS.md).
3. If approved, privately configure an API key with Configure Voice; manually test
   pauses, interruptions, languages, disclosure and measured cost.
4. Configure one safe Home Assistant light and have the owner personally validate
   permissions and observed state. No unattended household actions.
5. Add real voice-memory integration only after resolving unavoidable live-audio
   disclosure and identity/consent. Keep [Issue #7](https://github.com/arthurlorente/wanda/issues/7)
   open until all V1 criteria have evidence.
6. Review licensing ([#6](https://github.com/arthurlorente/wanda/issues/6)), encrypted
   backups, robust household authentication and durable home audit as separate work.

Satellite hardware, wake word, voiceprints, room handoff and general computer
agents remain later. See [acceptance mapping](testing/V0_ACCEPTANCE.md),
[human actions](HUMAN_ACTIONS_REQUIRED.md) and [checkpoint/PR](DEVELOPMENT_CHECKPOINT.md).
