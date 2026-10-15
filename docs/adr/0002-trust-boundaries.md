# ADR 0002 — Household versus privileged agent permissions

**Status:** Accepted.

Anyone at home may speak to satellites. Anonymous voice input may access only allowlisted household commands. Personal memories, files, and PC actions require stronger authentication and out-of-band approval. Use distinct credentials and tool scopes.

**Speaker identity direction (D-037):** Voice recognition should be the default, hands-free way Wanda recognizes household members for low-risk personalization. Speaker recognition is probabilistic and vulnerable to imitation, replay, or uncertainty. Treat uncertain voices as guests and never equate a voice match with authority to disclose restricted personal memories, credentials, or execute sensitive actions. Use stronger or out-of-band authentication for those operations. The concrete biometric technology and enrollment policy remain undecided, and voice recognition is not required to work in P0.

**Consequence:** Added identity and authorization UX, reducing risks from untrusted voice commands.
