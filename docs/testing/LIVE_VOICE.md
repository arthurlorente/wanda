# Bounded synthetic live voice verification

This developer-only harness is separate from the normal Wanda UI. It needs an
explicit authorization flag, an existing private voice key, Node/Playwright and
Chrome. It never asks for microphone permission, records audio, reads saved
memories, or contacts home devices. CI runs only offline tests.

## Scope and accounting

The 2026-10-15 session authorization is at most **US$10 total**, replacing the
original US$5 ceiling before paid tests began. New calls stop at 15:00 UTC
(11:00am New York). This is not permission for recurring API tests or household
speech. Do not edit the cutoff, reset the ledger or increase its cap to resume.

The parent creates a private SQLite ledger outside Git and reserves **US$3 per
attempt**, at most two attempts. Failed or uncertain attempts retain their full
reservation. A subsequent attempt requires confirmed server cleanup and bounded
usage accounting for the preceding attempt, or a narrowly evidenced setup rejection
(HTTP 400, no SDP answer and zero response creation). That reconciliation preserves
the failed outcome as `setup_rejected` and retains the entire reservation. Reservations are conservative
accounting holds, not actual provider charges or refunds.

The [model page](https://developers.openai.com/api/docs/models/gpt-realtime-2.1)
lists a 128,000-token context, 32,000 maximum output, US$4 per million input text
tokens, and US$64 per million output audio tokens. A conservative inference is
`128000 × 4 / 1000000 + 32000 × 64 / 1000000 = US$2.56` for one text-only response,
charging every output token at the highest output rate. The reservation rounds
this to US$3. It uses the full published model limit rather than relying on the
smoke test's requested 128-token output cap to settle reasoning-token semantics.
Prices and limits were checked on 2026-10-15 and must be rechecked before reuse.

The [billing guide](https://developers.openai.com/api/docs/guides/voice-latency-cost?voice-api=realtime)
explains response-based charging and usage events. The harness supplies explicit
synthetic text, disables VAD, transcription and tools, never commits its silent
audio stream, and sends exactly one `response.create`. It rejects unexpected
session settings and input audio/image usage. A computed usage estimate is not a
verified invoice or a general monthly cost prediction.

## Isolation and cleanup

Python retains the API key; the child receives only a temporary loopback URL,
local capability and test mode over stdin. Child environment variables are
allowlisted; provider credentials and debug logging settings are excluded. The
server uses an empty temporary memory store and fake home adapter. No private
household database is opened. The browser uses a fresh context, a zero-valued
synthetic audio source and muted output; it never attaches a microphone.

The parent accepts only the documented provider call location, captures its ID
before returning SDP, and attempts authenticated
[server-side hangup](https://developers.openai.com/api/reference/resources/realtime/subresources/calls/methods/hangup)
on completion or timeout. A separate watchdog bounds the test. Browser cleanup
and provider hangup are reported separately. No raw SDP, session identifiers,
provider errors, credentials or audio files are printed or saved in the checkout.

The test can establish provider connectivity, generated audio packets, a short
synthetic transcript, usage accounting and cancellation acknowledgements. It
cannot establish microphone recognition, perceived audio quality, natural pauses,
spoken barge-in, household suitability or language fluency. Those still require
the [manual protocol](../VOICE.md#manual-audio-acceptance-procedure).

## Running an authorized attempt

After reading the current checkpoint and private accounting, the authorized
operator can run `python3 scripts/live_voice_check.py --allow-paid --mode smoke`.
Use `--node /absolute/path/to/node` if Node is not on PATH. Playwright must be
available through Node's module lookup, and `WANDA_TEST_BROWSER=chrome` selects
installed Chrome. The cancellation mode is a separate attempt, never an
automatic retry. The script refuses missing configuration, expired authorization
or exhausted/uncertain accounting.

The session-specific runner is intentionally unusable after its cutoff without a
new authorization and reviewed policy. The normal owner launch remains **Start
Wanda**; it does not execute this paid test script or consume its private ledger.

## Evidence

- Metadata-only API access succeeded for the configured model. This did not
  generate a response or consume inference tokens.
- First synthetic WebRTC attempt received provider HTTP 400 before creating a
  response (zero `response.create`, zero microphone calls). Local cleanup passed;
  no call ID or usage was returned. The private ledger retains US$3 and blocks
  automatic retries. No successful live inference is claimed.
- A separate configuration-only client-secret request accepted the identical
  synthetic session settings (HTTP 200). Its 10-second token was discarded without
  being displayed, saved, used to connect, or used to generate a response.
- Investigation found that the generic local string validator stripped the SDP
  offer's final CRLF. Preserving protocol text is required by the
  [SDP line grammar](https://www.rfc-editor.org/rfc/rfc8866.html#section-9);
  the regression fix passed. The remaining planned attempt succeeded with the
  same settings after preserving the offer. The first failed outcome remains in
  the private ledger as `setup_rejected`, with estimated usage zero and its full
  US$3 reservation retained. No ledger reset or refund was performed.
- Second attempt: **passed**, provider session HTTP 201, one completed response,
  38 input tokens, 98 output tokens, zero input audio/image tokens, zero microphone
  calls, one received audio track, 53 RTP packets/3433 bytes, and transcript observed.
  Provider hangup returned HTTP 200 before browser closure; inner and browser
  cleanup both passed. Conservative usage estimate: **US$0.006424**, not a verified
  invoice. Session-created event arrived at 1296ms and the provider audio-start
  event at 1836ms from test setup; these are protocol timings, not perceived latency.
- The two-attempt limit is now exhausted. **US$6 remains reserved** in the ledger;
  this is not US$6 spent. No additional paid inference or live cancellation test
  is planned under this harness policy. Continue offline work and leave listening,
  microphone recognition and spoken interruption acceptance to the owner.
  See the [development checkpoint](../DEVELOPMENT_CHECKPOINT.md).
