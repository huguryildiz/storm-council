# Decision Frame

## Decision Question

Should a production network operations team replace LP/MIP/CP-SAT flow optimization with a deep-RL controller, augment classical optimization with RL, or keep the current solver-centered architecture for real-time network flow control?

## Why It Matters

Traffic engineering decisions affect congestion, latency, packet loss, service-level agreements, auditability, and on-call risk. A mistaken replacement can turn an optimization improvement into a production outage.

## Scope

- Real-time traffic engineering in IP/MPLS backbones and data-center fabrics.
- Classical LP/MIP/CP-SAT or minimum-cost-flow style optimization used for flow allocation, routing, or rerouting.
- RL as a replacement controller, a proposer, a warm-start mechanism, or an accelerator.

## Exclusions

- Wireless/cellular resource scheduling.
- Pure adaptive bitrate streaming or TCP congestion-control products unless they bear directly on TE controller replacement.
- Vendor claims without inspectable methods, benchmarks, or production evidence.

## Key Assumptions

- The audience operates a mid-to-large ISP or cloud-provider network.
- The decision horizon is 3-5 years.
- Risk tolerance is low because production outages, compliance failures, and SLA violations are unacceptable.
- A credible recommendation must distinguish deployed practice from simulation or offline benchmark evidence.

## Stakeholders

Senior network engineers, NOC/SRE teams, engineering managers, capacity planners, compliance and audit stakeholders, application owners, and customers affected by network reliability.

## What Would Change the Decision

- A verified production deployment where RL is the primary TE authority with published rollback, failure, and SLA evidence.
- A reproducible benchmark where RL-primary control beats a strong LP/MIP/CP-SAT baseline on the same hard constraints, under failures and demand shifts.
- A cost model showing that solve-time savings materially exceed ML infrastructure, training, observability, and on-call costs.
- A safe-RL or hybrid architecture that gives deterministic constraint enforcement and auditable rollback.

## Known Uncertainties

- Whether offline traffic-matrix gains transfer to production failures and update races.
- Whether learned policies can be audited to the standard required by production network operations.
- Whether GPU/training and engineering costs beat solver and operations costs for a specific network.
- Whether the strongest published evidence reflects replacement, augmentation, or only acceleration.

## Research Acceptance Criteria

- Every external factual claim must cite a stable source ID.
- The brief must name at least one production TE deployment or credible benchmark.
- Cross-perspective contradictions must be explicit rather than hidden.
- Evidence insufficiency must be stated directly.
