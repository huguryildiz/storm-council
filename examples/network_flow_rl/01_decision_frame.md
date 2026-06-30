# 01 - Decision Frame

## Decision question

Should an engineering organization use reinforcement learning (RL) methods for network flow optimization?

## Framed decision

Do not treat the question as "can RL solve any network-routing toy problem?" Treat it as an architecture decision for production network-flow optimization: whether RL should replace, augment, or be excluded from systems that route traffic, allocate capacity, or solve traffic-engineering problems under capacity, conservation, latency, reliability, and operational constraints.

## Audience

Infrastructure engineering leadership, network optimization researchers, SRE/network operations, and product owners deciding whether to fund an RL-based optimization effort.

## Scope

- In scope: traffic engineering, WAN/datacenter flow scheduling, critical-flow rerouting, learned heuristics, learned warm starts, and RL/GNN methods for online routing decisions.
- In scope: comparison with classical max-flow, min-cost-flow, linear programming, constraint programming, and heuristic traffic-engineering baselines.
- Out of scope: generic reinforcement learning tutorials, physical transportation networks, financial order routing, and replacing all network control-plane logic.

## Stakeholders

- Network operators who need predictable behavior and fast rollback.
- Optimization engineers who own exact and approximate flow solvers.
- SRE/security teams who need guardrails, observability, and incident response.
- Finance/product leaders who care about engineering cost and measurable performance gains.
- Users/customers affected by congestion, packet loss, latency, and outages.

## Acceptance criteria

RL is a credible production option only if it:

1. Meets or beats a strong classical baseline on the same objective and constraints.
2. Preserves hard constraints through a solver, projection layer, shield, or safe fallback.
3. Generalizes across traffic matrices, topologies, failures, and demand shifts.
4. Produces measurable operational value beyond added ML complexity.
5. Can run in shadow mode, be rolled back, and be audited after incidents.

## What would change the answer

- A reproducible benchmark where RL or learning-augmented optimization consistently matches solver quality at lower decision latency across real topologies and unseen traffic matrices.
- Evidence that the RL policy can satisfy capacity and conservation constraints by construction, not only in average simulation results.
- A live or shadow deployment showing reduced congestion, faster convergence, or lower operational toil without increasing incident risk.
- A cost model showing that data, simulator, training, monitoring, and rollback overhead are justified by measured network gains.

## Initial risk posture

Medium-high. RL may be useful for dynamic decision support and learned heuristics, but network flow optimization sits close to safety, reliability, and customer experience. Replacement of mature flow solvers requires stronger evidence than a research prototype.
