# Source-Mapped Synthesis

## Executive Summary

RL should augment, not replace, classical LP/MIP/CP-SAT-style network-flow optimization for production TE under a low-risk 3-5 year horizon. The strongest retrieved ML evidence, Teal and CFR-RL, is hybrid or learning-accelerated: learning proposes or selects, while constrained optimization still enforces flow allocation. Production TE precedents, B4 and SWAN, emphasize centralized optimization, fallback, and safe update plans rather than opaque controller replacement. The recommendation is Option B: pilot RL as a bounded proposer or accelerator, keep deterministic solvers and fallback as the system of record, and require shadow-mode evidence before traffic exposure.

## Strongest Evidence-Backed Findings

1. Teal is credible benchmark evidence for learning-accelerated WAN TE, not proof of RL-primary production control. Claims: C-001, C-002, C-003. Sources: S-001. Supported by academic; challenged by practitioner and skeptic on deployment scope.
2. CFR-RL supports hybrid critical-flow selection plus LP rerouting. Claims: C-004, C-005, C-028. Sources: S-002. Supported by academic and practitioner; challenged by skeptic on simulation-to-production transfer.
3. Production SDN TE precedents preserve fallback and update safety. Claims: C-006, C-008, C-009, C-010, C-024. Sources: S-003, S-004. Supported by practitioner and historian.
4. Safety-critical RL must address risk criteria and exploration risk explicitly. Claims: C-013, C-014, C-015. Source: S-005. Supported by skeptic; challenged only on networking specificity.
5. The live run did not retrieve production evidence for RL-primary TE in the required queries. Claim: C-012. Source: S-009. Supported by skeptic; qualified as a retrieval-scope finding.

## Main Disagreements

- X-002 remains unresolved because benchmark generalization to failures, demand shifts, and update races is not directly tested.
- X-004 remains unresolved because ROI depends on local solve latency, ML infrastructure, and on-call cost data.
- X-008 remains unresolved because no retrieved production case study supports RL-primary TE authority.

## Confidence-Ranked Claims

High confidence: C-006, C-003, C-001, C-008, C-009, C-023.
Moderate-high confidence: C-002, C-004, C-005, C-007, C-010, C-013, C-014, C-024, C-028.
Moderate confidence: C-011, C-015, C-016, C-017, C-018, C-019, C-020, C-021, C-022, C-025, C-026, C-027.

## Evidence Gaps

- No production RL-primary TE case study with rollback, outage, and SLA evidence. Ref: X-008.
- No local cost model for solve latency versus ML infrastructure and staffing. Ref: X-004.
- No direct failure-injection comparison of RL-primary, hybrid, and solver-only TE in the same production-like environment. Refs: X-001, X-002.

## Decision Options

Option A: Stay with LP/MIP/CP-SAT. Evidence strength: strong for safety and auditability; weaker if current solve latency is already a bottleneck. Trade-off: less ML upside.

Option B: Hybrid RL augmentation. Evidence strength: moderate and best aligned with Teal, CFR-RL, B4, and SWAN. Trade-off: needs simulator, replay, monitoring, and model governance.

Option C: RL-primary with LP fallback. Evidence strength: weak. Trade-off: highest learning upside, but production evidence and auditability remain insufficient.

## Recommended Next Actions

1. Keep classical solvers as the system of record. Refs: C-011, C-020, X-003.
2. Run a shadow-mode hybrid pilot: RL proposes or ranks candidate allocations; LP/MIP validates constraints and fallback behavior. Refs: C-022, C-027, X-001.
3. Build a traffic replay, failure-injection, and update-race benchmark before live exposure. Refs: C-016, X-002.
4. Create a local cost model covering solve latency, GPU/training, engineering time, incident cost, and on-call load. Ref: X-004.
5. Require auditable logs and rollback proof for every ML-suggested action. Refs: C-017, X-006.

## Hidden Connection

The same pattern appears across old and new evidence: the systems that look deployable are not the ones that make the controller more autonomous, but the ones that narrow autonomy into a constrained subsystem with fallback.

## Frontier Question

Can a learned TE component produce proposals that consistently improve objective value while a deterministic solver or shield proves capacity, priority, update-safety, and rollback constraints before any packet path changes?

## Source Map

- S-001: C-001, C-002, C-003, C-011, C-016, C-019, C-020, C-025, C-026, C-028.
- S-002: C-004, C-005, C-022, C-027, C-028.
- S-003: C-006, C-007, C-008, C-011, C-017, C-020, C-021, C-024, C-025, C-027.
- S-004: C-009, C-010, C-011, C-016, C-017, C-020, C-021, C-024, C-025.
- S-005: C-013, C-014, C-015, C-017, C-021.
- S-006: C-018, C-022.
- S-007: C-015, C-018, C-023, C-026.
- S-008: no direct claim support; metadata-only context.
- S-009: C-012.
