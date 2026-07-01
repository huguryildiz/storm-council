# Worked examples

Two complete, committed runs live under [`examples/`](../examples/). Both are
**Council Mode** runs (bounded cross-examination) with live retrieval,
source-mapped claims, explicit contradictions, and a deterministic
`PASS_WITH_CAVEATS` quality gate. Open `storm_council_report.html` in either folder
for the rendered report.

## `network_flow_rl` — RL vs. classical optimization for network flow control

[`examples/network_flow_rl/`](../examples/network_flow_rl/) runs the question:

> Should RL replace or augment classical optimization for real-time network flow
> control?

Five lenses · 28 claims · 9 sources · 8 explicit contradictions. This run
demonstrates the **v2 evidence path** — `03_evidence.jsonl` with locators and
`03_evidence_verdicts.jsonl` entailment judgements.

**The (honest) outcome.** The synthesis does not force a verdict: do **not** replace
classical LP/MIP/CP-SAT-style optimization with an RL-primary controller on the
retrieved evidence; use RL only as bounded augmentation. The gate returns
`PASS_WITH_CAVEATS`, with contradictions left open for human review.

## `ai_jobs_policy` — taxing vs. letting markets adjust to AI automation

[`examples/ai_jobs_policy/`](../examples/ai_jobs_policy/) runs the question:

> Should governments tax or slow AI-driven automation to protect jobs, or let labor
> markets adjust?

Five lenses · 26 claims · 12 sources · 8 explicit contradictions · live web
retrieval. Its recommendation: neither a blanket automation tax nor laissez-faire
adjustment, but a targeted transition compact — again `PASS_WITH_CAVEATS`, with the
disagreements kept on the record.

## What to read, in order (either example)

1. `05_decision_brief.md` — the one-page answer.
2. `04_contradiction_ledger.md` — where the perspectives disagree and why.
3. `04_council_deliberation.md` — the bounded cross-examination between lenses.
4. `03_evidence_plan.md` + `03_claims.jsonl` — the claims and their sources.
5. `06_adversarial_review.md` — the independent reviewer's checks and scores.
6. `05_argument_map.mmd` — the visual map of the argument.
