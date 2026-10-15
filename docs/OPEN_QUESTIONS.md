# Wanda — Open questions and evidence required

**Reviewed:** 2026-10-15. These are not decisions, specifications or validated facts.

## Voice and cost — before implementing P0

1. What OpenAI real-time speech-to-speech API/model(s) are actually available to the project, and how do they compare with the official ChatGPT Voice experience? Do not assume the ChatGPT Live model is separately exposed through the API.
2. Does a local web app with backend-generated session credentials and WebRTC yield satisfactory latency, interruptibility and turn taking?
3. What latency/quality test methodology and thresholds are meaningful (multiple speakers, device microphones, background speech, pause behavior)?
4. How much does realistic household conversation cost per day/month? How should usage caps, warnings and graceful degradation work?
5. Is wake-word detection local and robust enough, and how are false activations measured?

**Multilingual validation:** Which languages and dialects does the chosen realtime voice model handle well, including within-session language switching? Test mixed-language interruptions and turn-taking; document actual coverage and gaps.

## P0 software stack

**Assigned for Codex evaluation, not decided:** Select the simplest maintainable stack for a browser WebRTC client and portable backend, considering long-term Home Assistant and permissioned agent adapters, testing, onboarding, performance, and future non-browser satellites. Compare at least TypeScript-only and Python-backend/TypeScript-frontend approaches and document trade-offs; propose a decision before implementation.

## Device and deployment

6. After validating a portable P0 application, can an older laptop host the gateway reliably, or is a different always-on host preferable?
7. Which inexpensive satellites actually support echo cancellation, far-field pickup, duplex audio and interruptions?
8. Can existing cast speakers be used for output only, and how does that affect latency and handoff?
9. How should room attribution and simultaneous wake-ups work?
10. What remains usable with no internet, and which functions should have a distinct offline/local path?

## Tools, memory and safety

11. Which Home Assistant calls are safe without authentication, and how are command outcomes verified?
12. How is an OpenClaw action isolated, scoped, logged, rate-limited and approved out of band?
13. How are residents/guests informed of active listening and retention; how do they opt out?
14. **P0 memory policy agreed:** Setup opt-in, selective ordinary memories, context-sensitive approval, local primary storage. Which database, encryption, backups, retention, per-person access and third-party protections should we use?
15. Can long-term conversation memory avoid storing private third-party content by default?
16. How do we recover from agent errors and revoke all active tokens/devices quickly?

**Assigned to Codex:** Evaluate local automated backups, optional client-side-encrypted offsite backups, and manual export/restore. Recommend a P0 recovery baseline and later enhancements, covering backup encryption and key custody, loss of the host, portability/migration, integrity verification, automated restore testing, retention, complexity and cost. Do not choose a vendor or implementation before review.

## Community and governance

17. Choose software, documentation and hardware licenses (Issue #6).
18. What public contribution policy and security disclosure mechanism should be enabled?
19. When, if ever, would a private notebook or Notion add value without competing with GitHub's source of truth?
20. Should GitHub Discussions and Projects be enabled to separate exploratory discussions from accepted work?

## Rule for closing a question

Provide a link to evidence, acceptance-test output, PR, or an ADR. Update the decision register and any affected requirements/architecture. No answer should silently transition from proposed to accepted.
