# Contradiction Ledger

## Consensus

All five lenses agree that RL should not replace classical TE optimization on the retrieved evidence. The defensible path is solver-centered or hybrid: RL may propose, rank, warm-start, or accelerate, while deterministic optimization, constraints, and fallback remain the authority.

## Collective Blind Spot

No retrieved source gives a full production case study of RL-primary TE with outage, rollback, SLA, audit, and compliance evidence. This absence is recorded as X-008.

## Conflicts

### X-001 · Benchmark speed versus production authority
- Claims: C-002, C-011
- Relationship: scope_difference
- Evidence balance: mixed
- Resolution: partially_resolved
- Why it matters: A benchmark acceleration result does not itself justify live control authority.
- Next question: Can a pilot reproduce Teal-like gains under live rollback and SLA gates?

### X-002 · RL generalization versus sim-to-real risk
- Claims: C-001, C-016
- Relationship: tension
- Evidence balance: mixed
- Resolution: unresolved
- Why it matters: Generalization beyond traffic-matrix benchmarks determines outage risk.
- Next question: Does the learned policy preserve behavior under failures, demand shifts, and update races?

### X-003 · Hybrid design versus RL-primary replacement
- Claims: C-003, C-020
- Relationship: tension
- Evidence balance: supports_a
- Resolution: partially_resolved
- Why it matters: The strategic choice is replacement, augmentation, or status quo.
- Next question: What measurable value does RL add when solvers still enforce constraints?

### X-004 · Solver runtime bottleneck versus engineering cost
- Claims: C-019, C-021
- Relationship: tension
- Evidence balance: mixed
- Resolution: unresolved
- Why it matters: Runtime savings only matter if they exceed model, observability, training, and on-call cost.
- Next question: What are the local costs of solve latency, ML infra, retraining, and incident response?

### X-005 · Safe exploration versus SLA obligations
- Claims: C-013, C-015
- Relationship: evidence_gap
- Evidence balance: supports_b
- Resolution: partially_resolved
- Why it matters: Online learning can create unacceptable operational exposure.
- Next question: Can all learning be offline or shielded before live deployment?

### X-006 · Auditability versus learned policy complexity
- Claims: C-017, C-022
- Relationship: tension
- Evidence balance: mixed
- Resolution: unresolved
- Why it matters: Network operators need explainable rollback and accountability after incidents.
- Next question: Can the policy emit auditable constraint proofs or only opaque action scores?

### X-007 · Classical TE precedent versus ML acceleration frontier
- Claims: C-023, C-026
- Relationship: scope_difference
- Evidence balance: mixed
- Resolution: partially_resolved
- Why it matters: Older standards define the durable objective; newer ML changes possible implementation speed.
- Next question: Which TE subproblem is too slow for the existing deterministic stack?

### X-008 · Production deployment evidence for RL-primary TE
- Claims: C-012, C-028
- Relationship: evidence_gap
- Evidence balance: supports_a
- Resolution: unresolved
- Why it matters: Replacement requires production evidence stronger than papers on augmentation.
- Next question: Is there a verifiable RL-primary TE deployment with outage, rollback, and SLA evidence?
