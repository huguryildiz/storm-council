# Role Model

The current implemented role model is a five-lens model.

| Lens | Function | Main blind spot |
| --- | --- | --- |
| Practitioner | Tests operational reality, deployment friction, maintenance burden, failure modes | May discount research not yet productized |
| Academic | Evaluates peer-reviewed evidence, methods, benchmarks, reproducibility | May underweight deployment reality |
| Skeptic | Stress-tests unsupported claims, overclaims, incentives, missing evidence | May dismiss genuinely novel methods |
| Economist | Assesses costs, incentives, opportunity costs, externalities, distributional effects | May measure only what is quantifiable |
| Historian | Uses precedent, analogies, adoption history, institutional memory | May overfit the past to new cases |

Each lens is a functional research perspective, not an independent model. The
default runtime is a single Claude Code session unless the orchestrator dispatches
the lens files under `agents/` as Claude Code subagents. `run_manifest.json`, when
present, records the claimed dispatch mode and retrieval tools used, but it is
not cryptographic proof of independent reasoning.

## Council Mode

Council Mode means selected claims are cross-examined with bounded moves such as
`support`, `challenge`, `qualification`, `request_for_evidence`, or `reframing`.
The current implementation records and renders deliberation logs. It does not
automatically mutate the original claims after a challenge; the synthesis and
quality gate must carry unresolved conflicts forward.

## Not Implemented

This repository does not currently implement a Four Horsemen runtime. If older
materials mention a Four Horsemen model, treat them as legacy or external
planning material, not the current default architecture.
