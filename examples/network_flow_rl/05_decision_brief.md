# 05 - Decision Brief

## Verdict

Use RL selectively, not as a general replacement for network-flow optimization.

For static, feasibility-critical, or auditable flow problems, keep classical network-flow, LP, min-cost-flow, max-flow, and traffic-engineering solvers as the baseline and system of record (C-001, C-012). For dynamic traffic engineering where decisions are frequent and latency-sensitive, RL is worth evaluating as a bounded augmentation: candidate selection, learned warm starts, policy ranking, critical-flow selection, or learning-accelerated optimization (C-004, C-013, C-031, C-041).

## Recommended path

1. Define the exact workload: offline planning, online TE, datacenter flow scheduling, or incident response (X-002).
2. Build a replay benchmark from real traffic matrices, topology snapshots, and failure scenarios (C-032, X-003).
3. Compare against strong baselines: min-cost/max-flow where appropriate, LP/CP/TE optimizers, and incumbent heuristics (C-012, C-033).
4. If RL is tested, keep it outside direct control first: shadow mode, advisory mode, or solver-guided candidate selection (C-023, C-043).
5. Promote only if the pilot proves measurable value without weakening hard-constraint guarantees (C-020, X-004).

## Non-recommendation

Do not fund an end-to-end RL replacement for network-flow optimization unless the organization can show constraint satisfaction, generalization, rollback, and economic value against a strong optimizer on the target workload.
