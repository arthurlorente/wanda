# Human actions required

Updated 2026-10-15. **Nothing external is required for the default V0 demo.**
Development uses synthetic fixtures and no real devices. The owner has now
configured a private OpenAI key and authorized up to US$10 total in synthetic voice
API tests for this overnight session. One bounded synthetic response passed, with
a conservative usage estimate below one cent. The two planned attempts are complete;
US$6 remains reserved as a conservative hold, not a billed amount.
See the checkpoint for updated evidence and limits.

| Dependency | Why / tomorrow priority | Free tier and alternative | Exact owner action | Work that continues without it |
| --- | --- | --- | --- | --- |
| Python 3.11+ | Launch V0; required | Free runtime; already verified on development Mac | If launcher reports Python missing, install from [python.org](https://www.python.org/downloads/), then reopen Start Wanda. Windows: enable Python launcher during install. | Source, tests and docs are ready; no package setup needed |
| OpenAI API account/key with Realtime model access | Optional natural cloud speech; high priority to evaluate voice | Do not assume free credits or that a ChatGPT subscription supplies API usage. Local scripted demo is free and offline | Private key is configured and synthetic tests have a bounded session authorization. Before personal/household use, review [provider assessment](PROVIDERS.md) and costs. To change the key, double-click Configure Voice and enter it privately. See [VOICE](VOICE.md). Do not paste keys into chat/GitHub. Restart, consent in the browser and perform synthetic audio tests | UI, local memory, permissions, mock home and automated provider-contract tests |
| Live audio participation | Verify pauses, interruptions, code-switching and microphone behavior; optional tomorrow | No extra service beyond chosen voice provider | Perform the [manual voice protocol](testing/V0_ACCEPTANCE.md) using invented facts and no bystanders. Record measurements locally; publish only aggregate results | No-key demo and automated lifecycle tests |
| Home Assistant instance and scoped light/token | Required for real V1 home evidence; deferred to a later owner-led setup session | Home Assistant software is an alternative to vendor cloud control; hardware/hosting costs vary. Built-in mock needs nothing | Install Home Assistant first if needed, then configure one safe light following [HOME](HOME.md); review transport and per-action permission. Owner personally runs verification; unattended session is not authorized to operate household devices | Complete permission and mocked REST verification tests; V0 use and merge do not depend on this setup |
| Household privacy and deployment review | V0 design accepted in D-053; broader household use remains a separate gate | No account/payment | Review [Memory](MEMORY.md), [provider assessment](PROVIDERS.md), local OS account boundary and plaintext-at-rest limitations before broader use. ADR 0008/0009 are accepted for V0 and PRs #8–#12 are merged; consequential changes still require approval | Local synthetic demo remains usable |
| Project license | Needed before inviting external reuse/contributions; not a private demo blocker | Options in issue #6; none selected | Review license evaluation and explicitly choose software/docs/hardware licenses separately | Private experimentation and review can continue |
| Windows/Linux hands-on launch and audio | Portability evidence beyond CI; not a Mac demo blocker | Existing ordinary computer; no GPU required | Run Start Wanda on Windows or `python3 -m wanda` on Linux and follow the walkthrough; note browser/mic versions | Portable stdlib code and CI matrix are provided |

No registration, legal acceptance, billing, subscription changes or hardware purchases
were performed. Synthetic access to the configured model is verified. Actual invoiced prices,
quotas and provider retention for the specific account remain unverified. Saved-memory cloud
disclosure is not connected to voice; its local policy engine is tested separately.
