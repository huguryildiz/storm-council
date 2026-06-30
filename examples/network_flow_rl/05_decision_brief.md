# Decision Brief

RL should augment, not replace, LP/MIP/CP-SAT-style TE optimization for production network-flow control. The retrieved RL evidence is strongest for learning-accelerated optimization and critical-flow selection, while the production TE evidence emphasizes fallback, safe updates, and auditability. Under low risk tolerance, keep the classical solver as the authority and pilot RL only as a bounded proposer or accelerator.

## Strongest Findings

- Teal reports credible benchmark gains for learning-accelerated WAN TE, but the design still uses constrained optimization. Sources: S-001. Claims: C-001, C-002, C-003.
- CFR-RL uses RL to select critical flows and LP to reroute them. Source: S-002. Claims: C-004, C-005.
- B4 and SWAN show production TE practice values centralized optimization, fallback, and safe update sequencing. Sources: S-003, S-004. Claims: C-006, C-008, C-009, C-010.
- Safe RL literature makes safety constraints and risky exploration explicit concerns. Source: S-005. Claims: C-013, C-014, C-015.

## Top Unresolved Contradictions

- X-002: benchmark generalization versus sim-to-real and failure-mode risk.
- X-004: possible runtime ROI versus missing local ML and operations cost model.
- X-008: no retrieved production evidence for RL-primary TE authority.

## Options

Option A: Stay with LP/MIP/CP-SAT. Strong evidence for safety and auditability; may leave solve-time bottlenecks untouched.

Option B: Hybrid RL for coarse TE, candidate ranking, warm-starting, or critical-flow selection while LP/MIP enforces constraints. Moderate evidence; recommended.

Option C: RL-primary with LP fallback circuit. Weak evidence; only consider after shadow-mode and failure-injection proof.

## Recommended Next Actions

1. Keep solver-centered TE in production while profiling actual solve bottlenecks.
2. Build a replay benchmark from local traffic matrices, failures, and update races.
3. Run RL in shadow mode as a proposer; accept only allocations certified by deterministic constraints.
4. Measure ROI: solve latency, satisfied demand, operator workload, GPU/training cost, and incident risk.
5. Require auditable logs and fallback drills before any traffic exposure.

## Frontier Research Questions

1. Can RL proposals improve TE objective value after deterministic constraint certification?
2. Can safe-RL shields cover update-order, failure, and SLA constraints in a live TE loop?
3. What benchmark best predicts production behavior under traffic shifts and incidents?

This brief supports, but does not replace, domain expertise, source verification, and accountable human decision-making.
