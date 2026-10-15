# Architecture overview

**Status: proposed, not validated.**

Room voice satellites → local audio/session gateway → cloud realtime speech-to-speech.

The local gateway exposes allowlisted tool interfaces to Home Assistant (household actions), OpenClaw (permissioned computer tasks), and a memory service (retrieval and persistence).

## Requirements
- Natural conversation, interruptions, follow-ups and pauses comparable to ChatGPT Voice
- Multi-room conversation handoff with shared context
- Guest-safe home control and authenticated privileged actions
- Durable searchable conversation history and long-term memory with explicit privacy controls
- Affordable satellites: initial target hardware budget up to $350
- Cloud operating budget target: $60–100 per month

## Open risks
- Current API/model compatibility and economics require validation
- Reliable full-duplex echo cancellation on inexpensive satellites
- Multi-room microphone arbitration
- OpenClaw and Home Assistant integration compatibility
- Identity, consent, retention, and privacy for household members and guests

Real home settings, transcripts, memory, and credentials are never version-controlled here.
