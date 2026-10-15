# Wanda V0 — morning handoff

You have a local browser app to try. **It is a demonstration, not the completed V1.**
It includes real private local memory and permission checks, simulated home lights,
and an optional cloud voice connection that still needs a live test.

## Start Wanda

1. Open this Wanda folder.
2. Mac: double-click **Start Wanda.command**. Windows: double-click **Start Wanda.bat**.
3. Keep the window that opens running. Your browser should open Wanda automatically.
4. If Python is missing, install Python 3.11 or newer from
   [python.org](https://www.python.org/downloads/) and reopen the launcher.
5. To finish, use **Stop Wanda** in the same folder, or press Control+C in its window.

Linux users can run `python3 -m wanda` from this folder. Developers can use
`python3 -m wanda --doctor` to check the setup. There are **no application packages
to install**, no GPU requirements, and no external accounts needed for this demo.
If the browser says it is locked, reopen Start Wanda so it receives the new local
session key. Do not share the launch link. If port 8765 is busy, set `WANDA_PORT`
to 8766 in a private config. Local service startup does not expose Wanda to your LAN.

## Five-minute walkthrough

Use invented information throughout:

1. **Conversation:** ask about privacy, memory, or home controls. These are scripted
   replies; the offline demo is not a general-purpose AI. Choose Portuguese or
   Spanish to try their scripted replies. Optional browser speech uses a local
   system voice when available; it is not natural microphone conversation.
2. **Memory:** enable memory. Type “My favorite color is green.” in the chat. The
   narrow automatic capture should save a preference. Open Memory to inspect it.
   Other/uncertain details require an explicit save approval; whole conversations
   and recordings are not saved.
3. **Persistence:** stop and start Wanda, then inspect Memory or ask “What do you
   remember?” The preference should remain. Edit it, export if wanted, then delete
   it. Turn memory off: new capture and conversational recall stop, but you can
   still review/export/delete existing records.
4. **Home:** request a light action before granting permission; it must be denied.
   Grant that specific light/action with confirmation enabled. Request again, then
   confirm separately. The simulated light changes. “On” and “off” need separate
   grants. Revoke the grant to block new actions. Grants reset when Wanda restarts.
5. **Outage:** enable the mock home outage and try an authorized action. The app
   reports unavailable, not success. Restore connectivity and issue a new request;
   the app does not retry old actions automatically.
6. **Cloud permissions:** inspect category/provider permissions and revoke them.
   These are real stored policy records, but V0 does not send saved memories to
   voice. Enabling a permission is not evidence that disclosure happened.

## What was tested

The 89 automated Python checks passed on Windows, macOS and Linux with both
Python 3.11 and 3.14. Eleven browser workflows passed, including memory, permission
denials, outages, mobile layout and microphone cleanup using simulated audio APIs.
This confirms the demo flows; it does not confirm real voice quality or devices.
See the [successful CI run](https://github.com/arthurlorente/wanda/actions/runs/38697725609).

## Optional live voice

The microphone remains off until you choose live voice, consent to the audio
disclosure, and allow browser microphone access. Live speech uses a proprietary
OpenAI API and may incur API charges. The key stays on the local server. An API
account/key, model access, billing decision, and human audio test are still needed.
Follow [VOICE](VOICE.md) and [human actions](HUMAN_ACTIONS_REQUIRED.md).
The optional **Configure Voice** launcher stores your key privately without
editing source files. It makes no provider call; restart Wanda after using it.

Microphone audio, including anything spoken by people nearby during a session,
reaches the provider. No local content filter can undo that disclosure. Use only
synthetic speech until provider handling and household consent are reviewed.
Saved memory is never attached, and cloud voice has no home or computer tools.
The Disconnect control releases microphone tracks and the WebRTC connection.
Live latency, voice quality, language coverage and cost are **not measured yet**.

## What remains incomplete

- Live voice and real Home Assistant acceptance evidence; V1 is not achieved.
- General offline language intelligence, broad automatic memory extraction,
  and cloud voice recall of saved memory.
- Separate resident authentication, guests/voiceprints, encrypted database/backup
  recovery, wake word, satellites, room handoff and computer agents.
- Production hosting, hard provider spending caps and broad platform/audio tests.
- Approved software, documentation and hardware licenses.

Memory is a real local SQLite database. It is protected by local file permissions,
not application encryption. Anyone with sufficient OS access can read it. The V0
browser session represents one local user, not a fully secured multi-resident home.
An exported JSON file contains plaintext memories: keep it private or delete it.

## Decisions for your review

[ADR 0008](adr/0008-v0-portable-stack.md) compares TypeScript end to end, Python
plus TypeScript, and the selected Python plus native JavaScript approach. The
provisional choice keeps launch simple and providers replaceable. SQLite local
memory, conservative extraction, single local-user access, ephemeral device
permissions and optional WebRTC are provisional engineering choices.

You can accept them in the PR review, request changes, or leave the branch
unmerged. Nothing was merged automatically. Reverting code does not delete your
private data folder. The data locations are described in [Memory](MEMORY.md).

Development branch: [codex/wanda-v0](https://github.com/arthurlorente/wanda/tree/codex/wanda-v0).
Reviewable, unmerged change: [PR #8](https://github.com/arthurlorente/wanda/pull/8).
Assignment: [Issue #7](https://github.com/arthurlorente/wanda/issues/7).
The final PR and verification evidence are recorded in [checkpoint](DEVELOPMENT_CHECKPOINT.md).

## Next useful step

Try the local walkthrough first, then review the provider disclosure and perform
the manual voice test. Next configure a single safe Home Assistant light and
verify its real state yourself. Keep Issue #7 open until its actual V1 criteria
have evidence. [Acceptance map](testing/V0_ACCEPTANCE.md) separates implemented,
simulated and pending work.
