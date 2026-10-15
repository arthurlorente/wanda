# V0 home control

**Status:** Mock home control is implemented and covered by automated tests. The Home Assistant REST adapter is implemented against a synthetic transport, but has **not** been connected to a real household or device. This is a provisional implementation under [ADR 0008](adr/0008-v0-portable-stack.md), not a claim that Wanda has met the V1 home integration gate.

## What the demo does

Wanda starts with two synthetic lights, `light.demo_lamp` and `light.demo_desk`, both off. The owner can inspect them, grant a specific `turn_on` or `turn_off` permission, revoke it, and simulate an outage. All actions are denied until granted. Confirmed actions require a second browser action within 60 seconds. A voice or chat request cannot supply that second approval on its own. The app must authenticate the local owner before calling `HomeService`; the server's owner key is never selected by an API caller.

Only one active grant may exist per owner, light and action. Revoke it before changing its confirmation rule or expiration.

The action response is one of `verified`, `confirmation_required`, `denied`, `unavailable`, or `unverified`. `verified` means the mock changed state, or a Home Assistant state read matched the intended state. `unverified` means Wanda cannot tell whether the real command took effect; check the device before issuing a new request. The service never automatically retries a real command.

The service keeps grants, confirmation nonces, action results and the most recent 256 audit entries **in memory**. They reset on restart. It retains at most 256 active grants and 1,024 distinct request IDs during a process. When the request history fills, new control requests fail closed until restart, because silently evicting an earlier ID could repeat a physical action. Repeating an existing request ID returns its original result without executing again, including after a connectivity failure. Use a fresh request ID only after checking the actual device state. This is a bounded V0 safeguard, not durable exactly-once delivery across restarts. A durable audit and idempotency store belong in later production work.

## Real Home Assistant adapter, when the owner is ready

`HomeAssistantAdapter(url, token, allowed_entities)` is an optional replacement for `MockHomeAdapter()`. Its allowlist accepts only entity IDs in the `light.<name>` domain; it supports only `turn_on` and `turn_off`. Both the adapter allowlist and a separate owner grant must permit a command. It sends a bearer token from server-side configuration to Home Assistant. The token must never enter the browser or repository. Use an HTTPS Home Assistant URL with a valid certificate, or an HTTP loopback URL if Wanda and Home Assistant share a host. HTTP over a local network sends the token in cleartext and requires an explicit `allow_insecure_http=True` constructor opt-in for evaluation. This opt-in is a provisional trade-off for installations without local TLS; review it before real use.

For a future private setup, supply the URL, token and a small list of real light entity IDs through private server configuration outside Git. The public repository contains no actual home address, inventory or token. The adapter calls `POST /api/services/light/turn_on` or `turn_off` with `{"entity_id": "..."}`, then `GET /api/states/<entity_id>` to check the resulting state. Home Assistant's [official REST documentation](https://developers.home-assistant.io/docs/api/rest/) distinguishes service calls, which communicate with devices, from writes to `/api/states`, which only change Home Assistant's representation. Wanda never writes directly to `/api/states`. The default HTTP transport also refuses redirects and bypasses system proxies so a configured token cannot be forwarded through either route.

## Safe manual acceptance protocol for the owner

### Private configuration

Copy `config.example.json` to the private Wanda data folder as `config.json`
(locations in [VOICE](VOICE.md)). If Configure Voice already created that file,
edit its existing home fields without replacing the voice key. Keep this file
outside Git. Set:

```json
{
  "WANDA_HOME_MODE": "homeassistant",
  "HOME_ASSISTANT_URL": "https://your-approved-home-assistant-host",
  "HOME_ASSISTANT_TOKEN": "YOUR_PRIVATE_TOKEN",
  "WANDA_HOME_ENTITIES": ["light.your_selected_safe_light"],
  "WANDA_HA_ALLOW_INSECURE_HTTP": false
}
```

These are placeholders, not an operational configuration. The corresponding
environment variables can override them. Obtain the token through your own Home
Assistant profile using its documented authentication procedure; keep its access
as limited as your installation supports. Wanda's allowlist bounds this adapter,
but does not reduce the token's underlying Home Assistant account privileges.
Run `python3 -m wanda --doctor`, then restart. Doctor validates configuration
without sending a device or provider request. The browser lists only allowlisted
lights and still starts with no action grants. To return to the default demo, set
`WANDA_HOME_MODE` to `mock` and restart. Setting `WANDA_HA_ALLOW_INSECURE_HTTP=true`
is an explicit cleartext-network exception; prefer HTTPS or same-host loopback.

Only after reviewing the configuration and code, choose a low-risk light and create its allowlist entry. Begin with the light off. Grant only `turn_on` with confirmation enabled. From the browser, request the action, check that no device changes before confirmation, then confirm and compare Wanda's reported state with the real light and Home Assistant's dashboard. Revoke the grant and verify a new request is denied. Repeat for `turn_off`. Disconnect Home Assistant and verify Wanda reports an unavailable or unverified outcome without repeating the command. Use a **new** request ID after personally checking the state. Do not test locks, alarms, heating, appliances or any unsupported domain. This protocol has not yet been performed.

## Boundaries and next work

The V0 local browser capability represents a single authenticated owner. Multi-resident and guest identities, durable profiles, out-of-band step-up, comprehensive permission review, persistent audit, crash-safe idempotency, rate limits and actual offline Home Assistant testing remain open. The mock can operate without cloud voice or Home Assistant. A Home Assistant outage does not make a physical light locally controllable through Wanda by itself. Real integration testing must establish that a supported light actually responds and that state readback is reliable before V1 claims.

To run synthetic tests: `python3 -m unittest tests/test_home.py -v`. Tests inject a fake HTTP transport and never contact Home Assistant.
