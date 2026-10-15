# ADR 0002 — Household versus privileged agent permissions

**Status:** Accepted.

Anyone at home may speak to satellites. Anonymous voice input may access only allowlisted household commands. Personal memories, files, and PC actions require stronger authentication and out-of-band approval. Use distinct credentials and tool scopes.

**Speaker identity direction (D-037):** Voice recognition should be the default, hands-free way Wanda recognizes household members for low-risk personalization. Speaker recognition is probabilistic and vulnerable to imitation, replay, or uncertainty. Treat uncertain voices as guests and never equate a voice match with authority to disclose restricted personal memories, credentials, or execute sensitive actions. Use stronger or out-of-band authentication for those operations. The concrete biometric technology and enrollment policy remain undecided, and voice recognition is not required to work in P0.

**Guest behavior (D-038):** Unrecognized speakers may ask general questions with guest permissions. Device controls are denied by default for guests and require an explicit, scoped authorization grant from an authorized resident; never infer control permission from physical presence. A guest may ask by voice to start account/speaker registration. The flow should keep short-lived conversation context active as enrollment proceeds and offer a no-phone initial step, while identity verification and resident authorization may still require a stronger method. A voice enrollment request does not confer device permissions.

**Consequence:** Added identity and authorization UX, reducing risks from untrusted voice commands.
