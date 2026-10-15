# Privacy and trust boundaries (draft)

**V0 implementation:** loopback server plus random per-start browser capability
for one local OS user; no resident or voice authentication. Owner-scoped local
memory and explicit permissions are tested, while SQLite/export remain plaintext.
Default demo has no cloud calls. Optional voice streams audio directly to OpenAI
after per-session consent, without saved memories or tools. This cannot filter
sensitive speech before provider exposure; use synthetic speech until review.
See [ADR 0008](../adr/0008-v0-portable-stack.md), [Memory](../MEMORY.md),
[Voice](../VOICE.md) and [provider evaluation](../PROVIDERS.md).

Unverified speakers may perform only scoped household actions. Personal memories and privileged PC tools require authenticated approval from a personal device. Speaker recognition may aid convenience but is not authentication.

No continuous cloud audio streaming by default. Require an explicit wake word, active-session indicators, physical mute where possible, guest opt-out, retention and deletion controls. Raw audio recording is off by default.

Private data and transcripts are stored outside public Git. Backups must be encrypted and under household control. Test with synthetic data.
