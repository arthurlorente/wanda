# V0 verification and V1 acceptance map

All automated fixtures are synthetic. No automated test controls a household
device or calls a paid model. A passing contract test is not live integration proof.

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
| R-01,02,03,16,17 | Optional WebRTC session proxy, semantic turn detection, explicit connect/disconnect and multilingual persona; provider tests and UI lifecycle checks | Real microphone pauses/barge-in/follow-ups/code-switching; comparative voice quality |
| R-04,18 | Server-only key; local static assets; no audio recording/transcript persistence; HTTP auth/CSRF and redaction tests | Review actual provider/account retention; live network/audio inspection |
| R-10,19,20,21 | Real SQLite opt-in, conservative color/drink extraction, explicit uncertain/sensitive review, CRUD/export, restart and expiry tests | Broad context-sensitive extraction; encrypted backup/restore |
| R-22,29,30 | Owner-scoped queries, provider/category grants, deny/allow/revoke/expiry and atomic one-time disclosure tests | Multi-resident authentication/UI; voice receives no saved memory in V0 |
| R-07,11,33,34 | Mock home permissions, confirmation nonce, duplicate suppression, state verification and outage; mocked real HA REST adapter | Owner-operated physical light verification and local outage experiment |
| R-15,14,12 | Separate Python service and native browser; one-command runtime, launcher/doctor, portable test CI | Hands-on launch/browser/audio evidence on each OS |
| R-31 | Versioned persona derived from specification, scripted EN/PT/ES examples and prompt boundary tests | Human evaluation of real generated conversations and tone |
| R-32 | Suggestion-oriented persona, user-defined low-risk no-confirmation grant path, revocation and audit | Proactive context detection and real autonomous routine demonstration |
| R-13,27,28,36 | No-cost default, local/private storage, no saved-memory cloud attachment, provider research | Measured voice cost, provider/account policy approval and independence review |
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
- Voice/provider transport and real HA tests use injected responses only.
- Browser/launcher final evidence and commit/PR linkage: see
  [development checkpoint](../DEVELOPMENT_CHECKPOINT.md).
- Final local gate: **89 Python tests passed** and **11 browser workflows passed**
  on installed Chrome, including mobile overflow checks, consent before microphone,
  delayed permission cancellation, permission denial, five-minute cutoff and local
  server loss. WebRTC/audio were mocked; no natural voice benchmark was run.

- Remote application commit `7e522d18859c3c94d57d727de93564bd9ae1a84f`: all six
  Python 3.11/3.14 macOS/Linux/Windows jobs and Linux Chromium browser job passed
  in [CI run 38697725609](https://github.com/arthurlorente/wanda/actions/runs/38697725609).
  CI does not validate physical audio devices or live provider availability.
