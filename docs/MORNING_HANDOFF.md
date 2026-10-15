# Wanda V0 — morning handoff

You have a local browser app to try. **It is a demonstration, not the completed V1.**
The owner reviewed the demo and explicitly approved merging V0 on 2026-10-15.
PRs #8–#12 are merged into `main`; no Git or GitHub action is required from the owner.
It includes real private local memory and permission checks, simulated home lights,
and an optional cloud voice connection verified with synthetic generated audio.
The owner's quick voice-demo feedback was positive; a documented evaluation of
pauses, interruptions, languages and cost still remains.

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

You can also [download the tested demo ZIP](https://github.com/arthurlorente/wanda/actions/runs/38746282007/artifacts/11979560780)
and [extract it](DEMO_BUNDLE.md), then use its launcher without Git. GitHub may
ask you to sign in; this download expires October 22, 2026. It uses the same private data folder on this computer;
stop an older running copy before testing the new one. Python is still required.

While a memory save or deletion is pending, you can keep drafting. Newer text
is preserved. If its original record was deleted, Wanda labels the text as an
unsaved new-memory draft; it is saved again only if you choose Save.

If **Stop Wanda** cannot verify the running session, press **Control+C** in the
window that started it. The launcher now distinguishes a missing session record
from an unreadable, corrupt or unreachable one. It does not guess process IDs or
search other data folders. An explicitly selected data folder remains stoppable
even when unrelated configuration is broken. If damaged JSON makes a custom
folder's location unknown, repair the config or use the original window to stop.

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

The current demo passed **180 Python checks** across Windows, macOS and Linux
with Python 3.11 and 3.14, plus encryption checks and **47 browser workflows**.
Two OS-specific tests skip on Windows. The [successful CI run](https://github.com/arthurlorente/wanda/actions/runs/38746282007)
also produced the downloadable ZIP. A local rebuild matched its checksum exactly.
After the approved merge, [main CI](https://github.com/arthurlorente/wanda/actions/runs/38749589357)
passed the same eight jobs. Main's implementation tree matches the approved demo.
An extracted earlier build passed startup, memory persistence/deletion, simulated
light permissions and shutdown without Git installed in its runtime PATH.

Browser tests cover encrypted recovery, permission denials, outages, mobile layout,
follow-up sequencing, microphone cleanup using simulated audio APIs, and preserving
newer drafts through slow or failed requests. A missing response acknowledgement
stops the microphone. Lost writes disclose uncertainty rather than retrying.
These checks do not confirm real voice quality, desktop download prompts or physical
devices. Exact versions and evidence are in the [checkpoint](DEVELOPMENT_CHECKPOINT.md).

## Encrypted recovery increment

The tested increment in [PR #9](https://github.com/arthurlorente/wanda/pull/9)
adds [encrypted backup and restore](BACKUP.md). Use Memory to
download a password-encrypted file, preview it locally, and approve a merge. Keep
the password separately: Wanda cannot recover it if lost. Restoring preserves
existing memories and never restores old permissions or keys. Saved memories remain
local as requested. Its 126 Python tests and six encryption tests passed across
Windows, macOS and Linux; 20 browser workflows passed. This increment is now merged
and its technical design accepted for V0 under D-053.

## Optional live voice

The microphone remains off until you choose live voice, consent to the audio
disclosure, and allow browser microphone access. Live speech uses a proprietary
OpenAI API and may incur API charges. The key stays on the local server. An API
key is already privately configured, and a metadata request confirmed account
access to the configured model. A human audio test is still needed.
Follow [VOICE](VOICE.md) and [human actions](HUMAN_ACTIONS_REQUIRED.md).
The optional **Configure Voice** launcher stores your key privately without
editing source files. It makes no provider call; restart Wanda after using it.

Microphone audio, including anything spoken by people nearby during a session,
reaches the provider. No local content filter can undo that disclosure. Use only
synthetic speech until provider handling and household consent are reviewed.
Saved memory is never attached, and cloud voice has no home or computer tools.
The Disconnect control releases microphone tracks and the WebRTC connection.
A synthetic live response completed and server shutdown was confirmed; its
conservative usage estimate was under one cent. No microphone was used. Listening
quality, natural pauses, spoken interruptions and language fluency remain
**unverified**. See [exact evidence](testing/LIVE_VOICE.md).

## What remains incomplete

- Human live-voice acceptance and real Home Assistant evidence; V1 is not achieved.
- General offline language intelligence, broad automatic memory extraction,
  and cloud voice recall of saved memory.
- Separate resident authentication, guests/voiceprints, encrypted working database,
  automated/offsite backups, wake word, satellites, room handoff and computer agents.
- Production hosting, hard provider spending caps and broad platform/audio tests.
- Approved software, documentation and hardware licenses.

Memory is a real local SQLite database. It is protected by local file permissions,
not application encryption. Anyone with sufficient OS access can read it. The V0
browser session represents one local user, not a fully secured multi-resident home.
An exported JSON file contains plaintext memories: keep it private or delete it.

## Accepted V0 decisions and future review

[ADR 0008](adr/0008-v0-portable-stack.md) compares TypeScript end to end, Python
plus TypeScript, and the selected Python plus native JavaScript approach. The
choice keeps launch simple and providers replaceable. The owner accepted the
current design for V0, including SQLite local memory, conservative extraction,
single local-user access, ephemeral device permissions, optional WebRTC and
encrypted local recovery. See D-053 and ADR 0009.

V1 and production use remain separate review gates. Future changes or rollback
go through reviewed PRs; this approval is not permission for future automatic
merges. Reverting code does not delete your private data folder. Preserve a reader
for existing encrypted backups. Data locations are described in [Memory](MEMORY.md).

Accepted development baseline: [main](https://github.com/arthurlorente/wanda/tree/main).
Merged in order: [V0 foundation #8](https://github.com/arthurlorente/wanda/pull/8),
[encrypted recovery #9](https://github.com/arthurlorente/wanda/pull/9),
[synthetic voice fixes #10](https://github.com/arthurlorente/wanda/pull/10),
[conversation sequencing #11](https://github.com/arthurlorente/wanda/pull/11), and
[draft/stop recovery and ZIP #12](https://github.com/arthurlorente/wanda/pull/12).
The original branches remain available as historical references. The review
instance remains running; merging did not restart it or change private data.
Assignment: [Issue #7](https://github.com/arthurlorente/wanda/issues/7).
The final PR and verification evidence are recorded in [checkpoint](DEVELOPMENT_CHECKPOINT.md).

## Next useful step

Continue the local walkthrough and the documented manual voice evaluation.
Home Assistant setup is deferred to a later owner-led session. It must be installed
and connected to a compatible light before the real test; Wanda's Home panel uses
buttons, and spoken device commands are not connected yet. No real device action
is authorized for unattended development. Keep Issue #7 open until its actual V1 criteria
have evidence. [Acceptance map](testing/V0_ACCEPTANCE.md) separates implemented,
simulated and pending work.
