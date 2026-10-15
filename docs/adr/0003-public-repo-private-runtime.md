# ADR 0003 — Public source, private operation

**Status:** Accepted.

Public Git stores code, design, synthetic fixtures and example configurations only. Credentials, transcripts, embeddings, personal memories, household inventory, and real networking details stay in private runtime storage.

**Consequence:** Setup tools should generate local configuration, never publish real settings.
