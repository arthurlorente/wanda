# V0 conversation and voice

**Accepted V0 implementation, 2026-10-15 (D-053).** The default text conversation is a
small deterministic script, not open-domain AI. Optional live cloud voice has an
implemented connection path and mocked transport tests. Actual audio quality,
pauses, interruption quality, multilingual performance and realistic cost
remain **unverified** until the manual checks below pass.
A synthetic WebRTC response with generated audio/transcript and confirmed server
hangup passed using the private key. No microphone or personal data was used.
See [bounded live validation](testing/LIVE_VOICE.md) for exact evidence and cost limits.

## What the browser does

- Opens without microphone access in local demo mode. Text messages go only to
  the local Wanda server. Chat is held in this page's memory, not archived.
- If a local chat request fails, its message is marked unconfirmed. The text can
  return to an empty composer without replacing a newer draft or undoing Clear
  chat. There is no automatic resend: consented local capture may already have
  happened before a response was lost. A later memory-list refresh failure does
  not turn an already received answer into an unconfirmed message.
- Offers English, Portuguese and Spanish scripts and warm or neutral tone.
- Can read scripted replies with `speechSynthesis` only when explicitly enabled
  and a voice reports `localService: true` for the selected language. Browser/OS
  behavior still needs manual validation. No browser speech-recognition API is used.
- Shows whether local memory is enabled, all saved memories and their disclosure
  categories, export/edit/delete controls, and explicit proposed-memory review.
- Uses scoped home permissions and a separate confirmation click; conversation
  never invokes home tools. Repeated clicks on a pending device are suppressed.
- Removes the launch token from the URL immediately, retains it in tab session
  storage, and sends it as a bearer header only to the local API. This is access
  for the local OS user, not household identity verification.

## Optional live path

### Set up your key without editing code

1. Review [provider evidence](PROVIDERS.md) and decide whether to authorize the
   provider's data handling and API costs. A ChatGPT subscription is not used by
   this adapter; it requires your own separately configured API project/key.
2. Double-click **Configure Voice.command** (Mac) or **Configure Voice.bat**
   (Windows). Linux: `python3 -m wanda --configure-voice`.
3. Type `yes`, then paste your key at the hidden prompt. This only writes private
   configuration; it does not contact OpenAI, create an account or spend money.
4. Stop Wanda, then Start Wanda. Connect live voice only after reviewing the
   browser's per-session audio disclosure. Use synthetic examples first.
5. To turn this off, run Configure Voice again and type `disable`, then restart.

The default private configuration is `config.json` inside the Wanda data folder:
Mac `~/Library/Application Support/Wanda`, Windows `%LOCALAPPDATA%\Wanda`, Linux
`~/.local/share/wanda` (or `$XDG_DATA_HOME/wanda`). Unix file mode is `0600`;
Windows depends on your OS account ACL. It is not encrypted by Wanda.
The template `config.example.json` contains no key. Never edit it to add a secret.
For advanced setups, `WANDA_CONFIG` selects a different external JSON file and
environment variables override file values. `WANDA_DATA_DIR` changes private
storage. An explicitly empty `WANDA_CONFIG` disables config-file loading.

The official [WebRTC guide](https://developers.openai.com/api/docs/guides/voice-webrtc)
and [call creation reference](https://developers.openai.com/api/reference/resources/realtime/subresources/calls/methods/create)
were checked on 2026-10-15. The browser negotiates an SDP offer; Wanda posts it and
a session configuration as multipart form data to the fixed OpenAI
`/v1/realtime/calls` endpoint. The long-lived API key remains in Python. Media flows
directly between browser and provider once connected. WebRTC negotiates its audio
format; the session does not override it.

The accepted V0 configurable default is `gpt-realtime-2.1`, documented in the
current guide. A metadata request accepted the configured account/key for this
model. The subsequent bounded synthetic connection passed; this does not establish
perceived conversational quality.
Session configuration uses semantic turn detection with low eagerness, automatic
response and interruption, voice `marin`, at most 1024 output tokens per response,
and no tools. The browser disconnects after five minutes and caps connection setup
at forty seconds. These bounds are not a financial spending limit.

Every connection requires a fresh disclosure and checkbox before microphone
permission. Live speech, nearby voices, typed messages in that session and
connection metadata reach OpenAI. Saved local memories are **never** automatically
sent. Memory category grants cannot filter microphone audio. Provider retention
and processing policies apply; no blanket privacy guarantee is made.

The UI sends typed live messages over the data channel. If Wanda is responding,
one typed follow-up waits for the matching cancellation acknowledgement; another
draft stays in the text box. Language and tone changes accompany that waiting
message without replacing the server's foundational persona. Missing creation or
cancellation acknowledgements disconnect after fifteen seconds. A correlated
automatic-response conflict permits one retry of the rejected response request,
without sending the typed text twice; repeated or unrelated errors disconnect.
No network/session creation retry is added. These sequencing paths are covered by
synthetic browser events; real spoken interruption quality remains unverified. Audio
transcripts returned by the provider appear in the page only; user transcription
is not separately enabled. Reloading removes the page transcript. Clearing an
active live chat first disconnects; this cannot erase prior provider processing.

Interrupt sends response cancellation and clears unplayed audio when applicable,
following the [conversation event guidance](https://developers.openai.com/api/docs/guides/realtime-conversations).
Disconnect, setup failure, connection loss, capture ending and page exit stop
microphone tracks and close the peer connection. A cancelled attempt also stops
microphone tracks if the permission prompt resolves late. Live start is blocked
while local chat is pending; local speech synthesis is blocked during live setup
and playback so a pending memory reply cannot be read into the cloud microphone.
The browser also disconnects when the tab is hidden. While connecting or live it
checks the local server every three seconds with a two-second timeout. Stopping
Wanda via the external launcher therefore ends capture within about five seconds
in an active responsive browser; use Disconnect for immediate control. Browser
freezes and OS behavior require manual verification and cannot be guaranteed by
JavaScript timers.

An authenticated local heartbeat runs every three seconds during capture, with a
two-second timeout, so using the external Stop launcher also disconnects the
browser's otherwise independent cloud audio connection. The normal detection
window is up to five seconds while browser timers run; this is not a real-time OS
guarantee. Hiding the tab immediately disconnects, avoiding background capture and
timer throttling. The in-page Disconnect and Stop controls stop capture immediately.

The adapter rejects redirects, ignores environment proxy configuration, times
out requests, limits response size and returns generic errors without provider
bodies, credentials or SDP. It does not retry paid calls automatically. The local
HTTP boundary preserves the browser SDP exactly, including its final CRLF; generic
chat-text trimming must never be applied to this protocol payload.
HTTPS preserves Python's verified default trust. If a macOS Python distribution
loads no certificate authorities, Wanda tries the fixed OS certificate bundle at
`/etc/ssl/cert.pem`. Missing or invalid trust still fails closed; certificate and
hostname verification are never disabled. The Home Assistant adapter uses the
same helper, while retaining its separate URL and permission restrictions.

## Persona and review

`wanda/persona.py` version `0.1.0-v0` distills the manifesto into short behavior
instructions: concise warmth, thoughtful disagreement, occasional welcome humor,
factual humility and user agency. The manifesto is not pasted into a system
prompt. Neutral tone changes style while keeping privacy and capability limits.
Prompts describe boundaries; executable permissions enforce authority separately.

Tests check privacy disclosure, private-message refusal, honest home limits,
constructive challenge, neutral tone, language scripts, invalid inputs and the
provider request envelope. These deterministic tests cannot prove model behavior.
The owner accepted the current V0 implementation under D-053; this does not replace
human persona/audio evaluation. Modify the versioned instructions or replace the
`VoiceProvider` adapter through a reviewed PR; rollback also requires review.
See [ADR 0008](adr/0008-v0-portable-stack.md).

## Manual audio acceptance procedure

Use synthetic, non-sensitive content and a quiet room with informed participants.
Follow [Human actions required](HUMAN_ACTIONS_REQUIRED.md) for optional key setup.

1. Launch without voice configured. Confirm the page works, the microphone is
   off, and live connection is unavailable with a useful explanation.
2. With owner-approved API configuration, click Connect. Cancel the disclosure;
   confirm no microphone prompt appears. Reopen, consent, then deny microphone
   permission; confirm clear error and functioning local controls.
3. Connect and speak a simple greeting. Ask three follow-up questions. Pause
   mid-sentence for two seconds, then continue. Record interruptions or truncation.
4. Interrupt Wanda verbally while she speaks, then with Interrupt. Confirm audio
   stops promptly and a new utterance remains coherent. Try typing a follow-up.
5. Speak English, then Portuguese, then Spanish, including a mid-sentence switch.
   Record language/dialect errors; do not generalize untested language support.
6. Try warm and neutral tone; ask for an uncertain fact, suggest rebuilding an
   unnecessary component, request another person's private messages, and request
   a home action. Check humility, useful disagreement and truthful limits.
7. Disconnect during speech, while connection is starting, and before a delayed
   microphone prompt resolves. Verify the browser's capture indicator turns off.
8. Disconnect network access during an active call. Confirm live voice stops,
   while local memory and mock home remain usable. Reconnection must be explicit.
9. Let a session reach five minutes; confirm capture ends automatically. Close
   or reload the tab and check that microphone capture also stops.
10. Record browser/OS, model, date, language, pause/barge-in observations, perceived
    and measured latency, and actual provider usage. Do not record raw audio or
    publish private transcripts. Compare with the reference voice experience.

No microphone, real provider call, real household data or device is necessary for
the default demo or automated tests. Full V1 acceptance remains open in
[Issue #7](https://github.com/arthurlorente/wanda/issues/7).
