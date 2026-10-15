# ADR 0001 — Cloud real-time speech-to-speech

**Status:** Accepted as a prototype direction; implementation unverified.

Natural interruption and ChatGPT-Voice-like dialogue outrank local inference.

Use a supported cloud real-time speech-to-speech API for conversation, with device control and authorization enforced outside the model.

**Consequences:** Requires connectivity, disclosure of cloud audio processing, usage limits, and a gateway for cheap satellites.

**Validation:** P0 benchmark against official ChatGPT Voice.
