# Household trust, guest identity and permissions

**Status:** Accepted product principles, 2026-10-15 (decisions D-039 and D-040). Future implementation and provider choices pending.

## Design principle

People share ordinary personal details with friends and hosts because they trust those people. Their willingness to be remembered by a household does not imply willingness to have those details collected, sold, used for advertising, or circulated to an outside AI provider. Wanda should be a considerate household memory, not a commercial data broker.

This principle guides feature, vendor, architecture and governance decisions. It is compatible with acknowledging that P0 relies on cloud voice processing: disclose any provider exposure truthfully, evaluate provider policies and retention, minimize identifiable information, and avoid claims of perfect privacy.

## Guest permissions (D-039)

- Guests may ask general questions without registration.
- Access to household devices starts denied. Authorized residents may grant device-specific and action-specific permissions.
- Grants to visitors should normally be temporary with automatic expiration and easy revocation.
- For returning trusted guests, an authorized resident can promote individual grants to a persistent permission profile. A recurring visit does not silently elevate privileges.
- Store only information necessary for the agreed guest experience, with clear visibility and deletion controls.

## Guest memory and data trust (D-040)

- Minimal information such as names and ordinary preferences may be useful when the guest has been informed and the agreed consent rules permit it.
- Voice identity templates are biometric data and require distinct informed enrollment consent, protected storage, and revocation/deletion.
- A host's familiarity with someone does not confer permission to expose that person's data to cloud processors beyond disclosed, justified operation.
- No commercial sale, advertising targeting, brokering, or profiling based on entrusted resident or visitor information.
- Voice-first registration can preserve transient conversational context until identity and memory consent are established; do not persist unconsented guest conversations.
- Design reviews must explain who may access data, what goes to cloud services, why, and for how long.

## Status and open design questions

These are accepted principles, not working features. Grant duration, permission schema, how guest choices are communicated, voice enrollment, and cloud provider arrangements require tests and implementation decisions. See [Identity](IDENTITY.md), [Trust boundaries](adr/0002-trust-boundaries.md), and [Memory](adr/0005-memory.md).
