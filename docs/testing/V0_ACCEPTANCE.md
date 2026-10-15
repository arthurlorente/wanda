# V0 verification and V1 acceptance map

All automated fixtures are synthetic. The default suite and CI never control a
household device or call a paid model. A separately opted-in, bounded live harness
has verified one generated-audio response; see the evidence below. Passing a mock
contract test alone is not live integration proof.

## Repeatable checks

```sh
python3 -m wanda --doctor
python3 scripts/check.py
node --check web/app.js
```

Python is required; Node is only an optional development syntax/browser-test tool.
The first command reports config status without printing keys or contacting providers.
The suite covers real SQLite and loopback HTTP plus mocked provider/device transports.
In a restricted Codex sandbox, local port binding needs the platform's approval.
No dependency installation or compiled build step exists for the V0 application.

Optional browser regression suite (development only; Playwright 1.62.1):

```sh
npm install --no-save --package-lock=false playwright@1.62.1
npx playwright install chromium
node scripts/browser-check.cjs
```

Alternatively, set `WANDA_TEST_BROWSER=chrome` to use an installed Chrome.
`WANDA_TEST_PYTHON` can select the Python executable; `WANDA_SCREENSHOTS` can
select an external folder for synthetic screenshots. The script starts and stops
its own isolated server/database, uses no real microphone, and blocks external
browser requests in the default-demo checks. Browser dependencies are not needed
to launch Wanda. CI includes a Linux Chromium job in addition to the Python matrix.

## Requirement evidence

| Requirements | Implemented slice and automated evidence | Remaining acceptance |
| --- | --- | --- |
| R-01,02,03,16,17 | Optional WebRTC session proxy, semantic turn detection, explicit connect/disconnect and multilingual persona; provider tests, UI lifecycle checks and one synthetic live generated-audio response | Real microphone pauses/barge-in/follow-ups/code-switching; comparative voice quality |
| R-04,18 | Server-only key; local static assets; no audio recording/transcript persistence; HTTP auth/CSRF and redaction tests | Review actual provider/account retention; live network/audio inspection |
| R-10,19,20,21 | Real SQLite opt-in, conservative color/drink extraction, explicit uncertain/sensitive review, CRUD/export, restart and expiry tests | Broad context-sensitive extraction; encrypted working storage and disaster recovery |
| R-37 | Browser-encrypted local backup, password decryption, full preview and approved atomic merge; crypto/HTTP/browser tests | Owner recovery rehearsal; automatic/offsite backups remain unselected |
| R-22,29,30 | Owner-scoped queries, provider/category grants, deny/allow/revoke/expiry and atomic one-time disclosure tests | Multi-resident authentication/UI; voice receives no saved memory in V0 |
| R-07,11,33,34 | Mock home permissions, confirmation nonce, duplicate suppression, state verification and outage; mocked real HA REST adapter | Owner-operated physical light verification and local outage experiment |
| R-15,14,12 | Separate Python service and native browser; one-command runtime, launcher/doctor, portable test CI | Hands-on launch/browser/audio evidence on each OS |
| R-31 | Versioned persona derived from specification, scripted EN/PT/ES examples and prompt boundary tests | Human evaluation of real generated conversations and tone |
| R-32 | Suggestion-oriented persona, user-defined low-risk no-confirmation grant path, revocation and audit | Proactive context detection and real autonomous routine demonstration |
| R-13,27,28,36 | No-cost default, local/private storage, no saved-memory cloud attachment, provider research | Realistic conversation cost, provider/account policy approval and independence review |
| R-35 / Issue #7 V1 | Runnable V0 only | Natural live voice + consented memory + verified real home integration together |

## Manual live voice protocol — not yet performed

First review [provider evidence](../PROVIDERS.md) and [VOICE](../VOICE.md). Configure
only a project key you approve; use a provider budget. Do not use sensitive speech
or include bystanders. No saved memory or home tools are sent to this session.

1. Start with a synthetic greeting and ask a follow-up without clicking again.
2. Pause mid-sentence for 1, 2, and 4 seconds; note premature replies.
3. Interrupt a long answer, then correct the question. Observe whether output stops
   and the next reply reflects the correction. Repeat with browser Interrupt.
4. Switch English → Portuguese → Spanish mid-conversation. Record the exact dialect
   and gaps; do not generalize results to all languages.
5. Disconnect during a response and during microphone permission/connection setup.
   Verify browser microphone indicator clears; test permission denial and no mic.
6. Disconnect the network. The app must label the error and keep local memory/home
   panels usable without pretending the cloud is available. No automatic paid retry.
7. Ask if Wanda can control a light or recall private data; she must explain that this
   voice session has neither tool access nor saved memories. Test neutral tone.
8. Evaluate warmth, concise helpfulness, appropriate disagreement and no sentience claims.

Measure 10 turns per tested language/device: end-of-speech to first audible response,
interruption-to-silence, premature turns, repair success, actual provider usage and
cost. Keep raw voice and private notes outside Git. Record median/p95 only after
measurement; compare with a chosen reference experience using the same prompts.
No latency/cost target or successful benchmark is fabricated here.

## Manual Home Assistant protocol — not yet performed

Follow [HOME](../HOME.md) for one explicitly selected light. Owner must personally
confirm the physical result. Test blocked action, scoped grant, separate confirmation,
verified on/off states, revoke, token failure and Home Assistant outage. Do not use
locks, alarms, heating, garage doors, power-critical devices or unattended actions.
Never infer a successful state change from an HTTP dispatch alone.

## Evidence log

- 2026-10-15: Python 3.14.5 / SQLite 3.50.4 macOS integration gate: 30 tests passed
  at the first full server integration (later additions tracked in checkpoint).
- Default voice/provider transport and real HA tests use injected responses only.
  The separately authorized live result below is distinct from those mocks.
- Browser/launcher final evidence and commit/PR linkage: see
  [development checkpoint](../DEVELOPMENT_CHECKPOINT.md).
- Baseline local gate: **89 Python tests passed** and **11 browser workflows passed**
  on installed Chrome, including mobile overflow checks, consent before microphone,
  delayed permission cancellation, permission denial, five-minute cutoff and local
  server loss. WebRTC/audio were mocked; no natural voice benchmark was run.

- Remote application commit `7e522d18859c3c94d57d727de93564bd9ae1a84f`: all six
  Python 3.11/3.14 macOS/Linux/Windows jobs and Linux Chromium browser job passed
  in [CI run 38697725609](https://github.com/arthurlorente/wanda/actions/runs/38697725609).
  CI does not validate physical audio devices or live provider availability.

## Approved encrypted recovery increment

D-050 retains saved-memory locality. D-051 adds R-37 local encrypted recovery;
D-052 permits bounded synthetic API testing and does not change household privacy.
Current local evidence: 126 Python tests, 6 real cryptographic tests and 20 browser
workflows passed. Crypto tests independently decrypt/encrypt with Node's crypto
implementation; browser tests perform an actual encrypted download and restore.
Run `node --test tests/backup_crypto.test.cjs` alongside `python3 scripts/check.py`
and the existing browser test command. Remote CI and review status are tracked
in the checkpoint. A separate synthetic provider check now passed; real microphone
acceptance remains pending.

## Synthetic live provider evidence

[PR #10](https://github.com/arthurlorente/wanda/pull/10) fixes verified HTTPS trust
and SDP preservation defects. Its local gate passed **160 Python tests**, six
crypto tests and five child-input tests. The live harness completed one provider
response with audio packets, transcript, zero microphone/input-audio use and
HTTP 200 server hangup. Conservative usage estimate: US$0.006424, not an invoice.
The first attempt failed setup; both attempts retain US$6 in conservative ledger
reservations. The planned attempts are exhausted. [Exact protocol and evidence](LIVE_VOICE.md).

This establishes a working synthetic provider connection. It does not establish
natural pauses, spoken interruption, actual listening quality, persona fidelity
or multilingual fluency; the manual voice and real-light criteria remain open.

## Browser turn sequencing follow-up

The [PR #11](https://github.com/arthurlorente/wanda/pull/11) follow-up passed
**31 browser workflows** locally and in Linux Chromium CI with
synthetic microphone/provider events and blocked external requests. Regressions
cover delayed creation/cancellation, matching response IDs, one queued typed turn,
preserved drafts, automatic-response conflicts, one bounded retry without duplicate
text, style changes, stale events after disconnect and fifteen-second acknowledgement
timeouts. JavaScript syntax and diff checks passed. This supports R-02/R-03/R-17
failure handling; actual conversational timing and spoken interruption still need
the manual protocol. All six platform/version jobs also passed in
[CI](https://github.com/arthurlorente/wanda/actions/runs/38709595553) at implementation
commit `5342454346d175e4a9eb00c1ffa69f6d1585a3d9`.

## Demo recovery and delivery follow-up

The `codex/wanda-demo-recovery` increment passed **180 Python tests** and **41
local Chrome workflows**. The corrected [CI run](https://github.com/arthurlorente/wanda/actions/runs/38735661927)
passed all six OS/Python jobs, Linux Chromium and bundle delivery. R-10/R-18/R-34 regressions preserve newer memory/chat
drafts through delays and failures, prevent duplicate pending saves, distinguish
confirmed mutations from failed refreshes and disclose uncertain outcomes without
automatic retries. R-03/R-14 recovery checks preserve data-folder scope and report
unverifiable shutdown state honestly. Explicit private configuration is honored
before default home-folder lookup, with missing-home failure regressions. A POSIX signal-cleanup case is skipped on
Windows because process termination there bypasses Python's signal handler.

R-12/R-14 delivery checks validate committed-only ZIP contents, deterministic
output, private/runtime exclusions, executable modes, no overwrite and extracted
`--doctor` without Git. A symlink test is skipped on Windows because creation may
require additional OS privileges. Source review, full extracted-app smoke results,
remote CI and artifact links are recorded in the checkpoint. Actual desktop
download prompts and physical microphone use remain manual acceptance work.

Final deletion review: **47 local Chrome workflows passed**, adding six regressions
for unchanged deletion resets, newer draft/category preservation, deleted edit
conversion to an unsaved new record, unrelated edits and confirmed deletion with
failed refresh. All events are synthetic; no provider or microphone call occurred.
Remote evidence for this final fix belongs in the checkpoint.
