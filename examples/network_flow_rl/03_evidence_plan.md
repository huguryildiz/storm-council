# 03 - Evidence-Grounded Inquiry

## Retrieval status

Live source lookup was used on 2026-06-30. The report remains a decision-support artifact, not a substitute for a formal literature review or production design review.

## Source plan by lens

### Practitioner

- Use solver/library documentation to establish what classical network-flow tooling already provides: S-001, S-002.
- Use production traffic-engineering history to assess operational fit: S-003.
- Use RL traffic-engineering papers to identify required architecture components: S-006, S-007, S-008.

Key claims: C-001 through C-004.

### Academic

- Compare RL/ML-for-CO claims against strong optimization baselines and surveys: S-004, S-005.
- Distinguish traffic engineering from generic network-flow optimization: S-006, S-007, S-008.
- Evaluate hybrid learning-accelerated optimization: S-009.

Key claims: C-010 through C-013.

### Skeptic

- Check whether RL approaches guarantee feasibility or merely penalize violations: S-001, S-002, S-008.
- Look for simulator, topology-shift, and baseline-comparison limitations: S-006, S-007, S-008.
- Convert unsupported safety concerns into explicit assumptions rather than unsupported conclusions: C-022.

Key claims: C-020 through C-023.

### Economist

- Separate stable/offline flow solving from frequent online optimization where latency has measurable value.
- Use source-supported architectural evidence for costs where possible, but avoid inventing TCO numbers.
- Require measurable pilot thresholds before investment.

Key claims: C-030 through C-033.

### Historian

- Use B4 and learning-accelerated optimization as adoption precedents.
- Treat past adoption patterns as analogical evidence, not proof.
- Prefer hybrid and staged deployment over replacement framing.

Key claims: C-040 through C-043.

## Evidence status summary

- Supported facts and recommendations cite S-001 through S-009.
- Unsupported items are limited to assumptions about reward misspecification and problem-scope ambiguity.
- The major unresolved issue is not whether RL can help in some settings. It is whether the target workload needs RL enough to justify simulator, safety, and operations complexity.
