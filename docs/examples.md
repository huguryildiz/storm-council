# Worked example — RL for university course timetabling

The bundled example
([`examples/university_timetabling/expected_artifacts/`](../examples/university_timetabling/expected_artifacts/)) runs
the question:

> Whether and when reinforcement learning should complement (not replace)
> CP-SAT/MIP for university course timetabling.

The committed artifacts were produced by a deterministic run and are
banner-marked as non-retrieval; treat the sources as illustrative.

## What the example demonstrates

- **Operational concerns** (practitioner): CP-SAT/MIP already solve production
  timetabling with auditable, constraint-guaranteed schedules.
- **Academic evidence limits** (academic): RL-for-combinatorial-optimization
  evidence is mostly on routing/packing and rarely beats strong OR baselines on
  constrained scheduling.
- **Skepticism about hype** (skeptic): vendor gains lack reproducible baselines;
  absence of head-to-head studies signals immaturity.
- **Cost / infrastructure trade-offs** (economist): TCO and opportunity cost vs
  operational-resilience value — an internal tension.
- **Historical lessons** (historian): each prior "autonomous scheduling" wave
  over-promised and settled into niche or hybrid use.

## The five contradictions

| ID | Type | What disagrees |
| --- | --- | --- |
| `X-001` | tension | RL's complementary value vs reproducibility skepticism |
| `X-002` | definition_conflict | "use RL" = replace the solver vs augment soft/dynamic objectives |
| `X-003` | tension (time horizon) | current evidence vs near-term pilot potential |
| `X-004` | tension (stakeholder) | ML budget opportunity cost vs operational resilience |
| `X-005` | evidence_gap | no peer-reviewed RL-vs-CP-SAT head-to-head for this domain |

## The (honest) outcome

The synthesis does **not** force a verdict. Its recommendation: keep solver-based
timetabling, optionally pilot learning-augmented OR, and commission the missing
benchmark before any RL investment. The quality gate returns
`PASS_WITH_CAVEATS` — useful, but with open disagreements (`X-001`, `X-004`,
`X-005`) and low-credibility sources flagged for human review.

## What to read, in order

1. `05_decision_brief.md` — the one-page answer.
2. `04_contradiction_ledger.md` — where the perspectives disagree and why.
3. `04_council_deliberation.md` — the bounded cross-examination that narrowed
   the definitional conflict (`X-002`).
4. `03_evidence_plan.md` + `03_claims.jsonl` — the claims and their sources.
5. `06_adversarial_review.md` — the independent reviewer's checks and scores.
6. `05_argument_map.mmd` — the visual map of the argument.
