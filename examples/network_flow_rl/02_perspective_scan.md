# 02 - Perspective Scan

## Practitioner

**Role charter:** Judge whether RL can be operated in real networks without creating fragile control loops.

**Priority questions**

- What parts of network flow optimization are static planning versus online adaptation?
- Where do current LP/min-cost-flow/heuristic systems fail operationally?
- What monitoring, simulator, fallback, and rollback mechanisms would RL require?

**Expected evidence:** Solver documentation, SDN/TE deployment papers, operational constraints from traffic-engineering systems.

**Likely blind spot:** Discounting research progress because it is not yet productized.

**Potential conflicts:** May accept RL as an augmentation layer while the skeptic rejects it as unsafe.

**Escalation trigger:** A claim that RL can directly control production routing without a deterministic safety layer.

## Academic

**Role charter:** Ground the decision in algorithms, benchmarks, and reproducibility.

**Priority questions**

- Does RL beat strong flow-optimization baselines, or only shortest-path/ECMP heuristics?
- Are results robust to topology, demand, and failure distribution shifts?
- Is the method solving network flow, traffic engineering, or a narrower proxy problem?

**Expected evidence:** Peer-reviewed ML-for-CO surveys, RL traffic-engineering papers, benchmark comparisons.

**Likely blind spot:** Under-weighting integration and incident-management costs.

**Potential conflicts:** May see promise in learning-accelerated optimization that operators still view as immature.

**Escalation trigger:** Results reported without reproducible baselines or ablations.

## Skeptic

**Role charter:** Stress-test claims about optimality, safety, generalization, and incentives.

**Priority questions**

- Are hard constraints guaranteed or merely encouraged by reward penalties?
- Does RL optimize the real objective or a simulation proxy?
- What happens under adversarial traffic, topology change, measurement error, or partial observability?

**Expected evidence:** Negative results, limitations sections, robustness studies, missing benchmark evidence.

**Likely blind spot:** Reflexive dismissal of genuinely useful hybrid designs.

**Potential conflicts:** Challenges practitioner and academic optimism around dynamic routing gains.

**Escalation trigger:** Any recommendation that lacks explicit fallback and constraint enforcement.

## Economist

**Role charter:** Compare expected value, opportunity cost, staffing burden, and measurable benefit.

**Priority questions**

- What does RL add that cheaper solvers, heuristics, or forecasting cannot?
- Is the target use case frequent and valuable enough to pay for RL infrastructure?
- Who owns training data, simulator maintenance, model monitoring, and incident response?

**Expected evidence:** Cost model, deployment architecture, observed performance deltas, operations labor estimates.

**Likely blind spot:** Overweighting measurable cost and underweighting resilience value.

**Potential conflicts:** May support RL only where traffic variability creates measurable economic upside.

**Escalation trigger:** A payoff claim without an experiment design or baseline.

## Historian

**Role charter:** Bring precedent from network optimization, SDN, and ML-for-combinatorial-optimization adoption.

**Priority questions**

- Which previous network-control innovations succeeded, and why?
- Did they replace optimization/control systems or become hybrid overlays?
- What repeated failure patterns apply to RL-for-network-flow work?

**Expected evidence:** SDN/TE deployment history, classic solver adoption, ML-for-optimization surveys.

**Likely blind spot:** Assuming past adoption patterns fully constrain a newer method.

**Potential conflicts:** May favor hybridization even when the academic lens sees end-to-end RL as intellectually promising.

**Escalation trigger:** Replacement framing that ignores operational trust, control-plane safety, and rollback history.
