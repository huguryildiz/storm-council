# 04 - Contradiction Ledger

## Consensus

- Classical flow solvers remain the baseline for static and safety-critical flow optimization (C-001, C-012).
- RL has credible evidence in traffic-engineering and datacenter/WAN optimization settings, especially where decisions are online and repeated (C-004, C-011, C-031).
- The strongest near-term architecture is hybrid: RL or ML proposes, ranks, warms, or accelerates; a solver, shield, or optimizer enforces constraints (C-013, C-020, C-041).
- A production decision needs shadow-mode evaluation on real traffic traces and clear rollback, not only paper benchmarks (C-023, C-033, C-043).

## Conflicts

### X-001 - Replacement versus augmentation

The academic recommendation keeps classical optimization as the default baseline (C-012), while the practitioner sees dynamic RL value (C-004). This is partly resolved by narrowing the recommendation: do not replace the solver; evaluate bounded augmentation.

### X-002 - Optimality and feasibility versus fast adaptation

The practitioner and economist disagree on what matters most. Stable optimization benefits from exactness and mature tooling (C-001), while online TE can justify faster approximate decisions (C-031). The resolution depends on workload classification.

### X-003 - Benchmark evidence and simulator fidelity

The academic lens sees promising RL/TE papers (C-011), while the skeptic argues that production transfer remains unproven (C-021). This remains unresolved until tested against real traffic traces, topologies, and failures.

### X-004 - Safety guardrails versus economic upside

The skeptic requires constraint guarantees (C-020); the economist allows RL where speed/value is high (C-031). This remains unresolved until the architecture has a shielded enforcement layer and quantified residual risk.

### X-005 - Total cost of ownership

The economist sees RL as likely overhead for stable flow planning (C-030), but potentially valuable for frequent online decisions (C-031). This remains unresolved without a workload-specific cost model.

## Decision impact

The ledger does not block all RL work. It blocks only a broad replacement recommendation. The defensible path is a guarded pilot for dynamic traffic engineering or learning-accelerated optimization, with classical optimization retained as the system of record.
