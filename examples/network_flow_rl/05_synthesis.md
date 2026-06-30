# 05 - Source-Mapped Synthesis

## Bottom line

Reinforcement learning should not be adopted as a blanket replacement for network-flow optimization. The strongest evidence supports a narrower architecture: use mature flow solvers and traffic-engineering optimizers as the baseline, then evaluate RL or learning-accelerated optimization only for dynamic, high-frequency decisions where latency and adaptation matter.

## Strongest findings

1. Classical network-flow and TE optimization remains the baseline for feasibility-critical planning. Official solver/library documentation supports mature min-cost-flow and max-flow tooling (C-001, C-012; S-001, S-002).
2. RL has credible traffic-engineering evidence, including critical-flow rerouting, datacenter traffic optimization, and MARL/GNN traffic engineering comparisons (C-004, C-011; S-006, S-007, S-008).
3. The evidence does not justify end-to-end RL replacement. The safer pattern is hybrid: learned selection or acceleration plus a solver, projection, or safety layer (C-013, C-020, C-041; S-004, S-008, S-009).
4. The decision turns on workload economics. RL is hard to justify for stable/offline flow planning, but may pay off for high-frequency dynamic control if faster decisions produce measurable gains (C-030, C-031).
5. Production readiness depends on benchmark replay, shadow mode, hard-constraint enforcement, and rollback (C-023, C-032, C-033, C-043).

## Confidence-ranked claims

- High confidence: classical flow optimization is the baseline for static feasibility and auditable constraints (C-001, C-012).
- Medium-high confidence: RL is plausible for dynamic traffic-engineering augmentation (C-004, C-011, C-031).
- Medium confidence: learning-accelerated optimization is the most promising near-term architecture (C-013, C-041).
- Lower confidence: economic payoff will be positive without a workload-specific benchmark and cost model (C-030, C-031, X-005).

## Decision options

### A - Keep classical optimization only

Evidence strength: strong. Appropriate for stable/offline network-flow optimization, compliance-sensitive routing, and organizations without ML operations capacity.

### B - Hybrid learning-accelerated optimization

Evidence strength: moderate. Keep solvers for constraints and use learning to warm-start, rank candidates, approximate expensive subproblems, or accelerate TE decisions.

### C - Guarded RL for dynamic traffic engineering

Evidence strength: moderate but caveated. Use RL for bounded selection or policy recommendation in a shadowed, shielded, measurable pilot.

### D - End-to-end RL replacement

Evidence strength: unsupported for production. The council does not recommend this path on current evidence.

## Unresolved gaps

- X-003: simulator fidelity and topology/demand generalization remain unproven for the target organization.
- X-004: safety architecture and residual incident risk must be quantified.
- X-005: total cost of ownership cannot be inferred from the literature alone.

## Final synthesis

The practical recommendation is "RL around the optimizer," not "RL instead of the optimizer." Treat RL as an experimental augmentation layer for dynamic TE only after building a benchmark harness, preserving hard constraints through deterministic mechanisms, and proving value in shadow mode.
