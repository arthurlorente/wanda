# ADR 0008 — Portable V0 vertical slice

Date: 2026-10-15. **Status: provisional implementation for owner review**, under
[unattended discretion](../UNATTENDED_DEVELOPMENT.md); not an accepted V1 release.

## Alternatives and choice

| Option | Portability, maintenance and setup | Voice, testing and integrations | Tradeoff |
| --- | --- | --- | --- |
| TypeScript end to end | One language, Node plus package/build tooling | Excellent browser/WebRTC ecosystem; mature test tools | Additional package/toolchain installation for owner; SQLite needs a current runtime or dependency |
| Python backend + TypeScript frontend | Mature SQLite and Home Assistant ecosystem; two toolchains | Strong testing, Python adapters; same browser WebRTC | Bundling and generated assets complicate a tiny first client |
| **Python standard library + native browser JavaScript** | Python 3.11+, no runtime packages or build step | SQLite, unittest, HTTP and HTTPS adapters; browser-native WebRTC | Less static checking; stdlib server is loopback development infrastructure, not production hosting |

Choose the third option for V0. Separate service modules and HTTP contracts allow
TypeScript, a production server, or another voice provider later without replacing
the memory schema. No GPU, hosted database, account, cloud call or device is needed
for the default demo. The Python service and start/stop lifecycle pass macOS, Windows and Linux CI
on Python 3.11/3.14 (see [checkpoint](../DEVELOPMENT_CHECKPOINT.md)). Native
double-click launch and physical audio still need owner walkthroughs.

## Boundaries

- Bind only to 127.0.0.1; random per-start browser capability in URL fragment,
  removed by client and used as an Authorization header. Validate Host and Origin.
  This grants the local OS user access; it is not household multi-user authentication.
- SQLite runtime data and optional configuration live outside the checkout.
  Tests use temporary synthetic data. No audio/transcript logging.
- Memory opt-in, owner keys and category/provider consent are enforced in Python,
  never trusted to prompts. Unknown or sensitive extraction needs review.
- Default conversation is explicitly scripted. Optional OpenAI WebRTC is disabled
  without server-side credentials, config opt-in and per-session audio disclosure.
  Live audio inherently reaches the provider before local content classification;
  therefore private household speech cannot be made safe by a category filter.
  V0 sends no saved memory to live voice and enables no model device tools.
- Home defaults to a fake adapter. A real adapter is opt-in and bounded to lights;
  no household operations are authorized during this development session.

## Review and reversal

Accept by reviewing this ADR and its implementation PR. Modify by swapping service
adapters or migrating the HTTP client to TypeScript. Revert the feature branch/PR
without merging; private state remains outside Git. Keep licensing undecided.
V1 still needs real voice, privacy-policy and Home Assistant acceptance evidence.
