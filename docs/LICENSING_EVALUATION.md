# Licensing evaluation brief — decision pending

**Status:** Research assignment for Codex; no license approved.
**Date:** 2026-10-15
**Issue:** [#6](https://github.com/arthurlorente/wanda/issues/6)

## Wanda-specific goals

1. Keep Wanda legally reusable, modifiable and redistributable for ordinary households and community contributors.
2. Consider preventing modified network-hosted services from withholding their corresponding code.
3. Enable interoperability with Home Assistant, OpenClaw, device firmware, SDKs and commercial or community extensions.
4. Keep contributions and compliance understandable for non-specialist developers and hardware makers.
5. Protect users' private household data; do not confuse copyleft licensing with privacy protections or immunity from vendor lock-in.
6. Differentiate source code, written documentation, hardware/CAD and possibly firmware.

## Evaluate software licenses

| Option | Strength | Cost / trade-off |
| --- | --- | --- |
| Apache-2.0 | Permissive reuse, including commercial and closed-source derivatives; explicit patent grant | No general requirement to publish modifications |
| GPL-3.0 | Copyleft for distributed modified software | Pure network service use generally does not trigger corresponding-source offer |
| AGPL-3.0 | Adds source-offer obligation for users interacting with certain modified versions over a network | Greater license compliance and integration complexity; may limit adoption by some commercial projects |
| Other | Include if a materially better fit emerges | Justify explicitly |

**Important:** Open-source licenses are not noncommercial licenses. AGPL obligations do not automatically require publication of every private modification in every circumstance; evaluate the actual triggering conditions and interactions of separate components. A license alone cannot enforce a commitment to make AI affordable or ensure runtime privacy.

## Candidate split by artifact type

- **Software:** AGPL-3.0 vs Apache-2.0 are the leading candidates; assess GPL-3.0.
- **Documentation:** Evaluate CC BY 4.0 versus applying the software license to docs.
- **Hardware designs:** Evaluate CERN-OHL-P-2.0, CERN-OHL-W-2.0 and CERN-OHL-S-2.0 based on whether reciprocal sharing of modifications is desired.
- **Firmware:** Check distribution approach and compatibility with dependencies.
- **Third-party dependencies and contributed code:** Assess compatibility, notices, inbound contributions and future relicensing implications.

## Codex deliverable — recommendation, not implementation

1. Verify current canonical license terms from license stewards; cite sources.
2. Compare license implications for Wanda's real architecture: personal installs, local gateways, plug-ins, linked/separate services, cloud-hosted variants, firmware and CAD distribution.
3. Give a primary recommendation **and a credible alternative** with practical scenarios demonstrating the trade-offs.
4. Explain AGPL networking triggers accurately; analyze compatibility with likely dependencies without assuming their licenses.
5. Recommend any per-directory license notices, `LICENSE` files, `NOTICE`, SPDX headers, and contributor policy.
6. Identify legal questions that deserve independent review; do not present this as legal advice.
7. Write a proposal in a branch / PR and ask the maintainer to approve **before** adding operative licenses or changing contribution rights.

## Preliminary, nonbinding view

AGPL-3.0 may align more closely with the goal of keeping modified network services open, while Apache-2.0 may serve the goal of maximum adoption and compatibility. **Neither has been selected.**

## Official references

- [GNU AGPLv3](https://www.gnu.org/licenses/agpl-3.0.html)
- [Apache License 2.0](https://www.apache.org/licenses/LICENSE-2.0)
- [GNU licensing overview](https://www.gnu.org/licenses/licenses.html)
- [Creative Commons BY 4.0](https://creativecommons.org/licenses/by/4.0/)
- [CERN Open Hardware Licence](https://cern-ohl.web.cern.ch/home)
