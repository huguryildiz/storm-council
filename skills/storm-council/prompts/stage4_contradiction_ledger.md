# Stage 4 prompt · Contradiction Ledger

> Map where the lenses disagree, who has the strongest/weakest evidence, what
> they all agree on, and what none addressed — as a **classified, ID-linked
> ledger** and (when stakes are high) a bounded cross-examination, so
> disagreement is recorded rather than averaged away.
>
> Writes: `04_contradiction_ledger.md` + `04_contradictions.json`
> (+ `04_council_deliberation.md`/`.jsonl` in Council Mode). Shape:
> [`../templates/contradiction_record.json`](../templates/contradiction_record.json).

---

Compare the claims in `03_claims.jsonl` across all lenses for **{{topic}}** and
build the contradiction ledger.

For every genuine conflict, write a record:

- `contradiction_id` — stable, e.g. `X-001`.
- `topic` — short label for what is in conflict.
- `claim_ids` — the specific claims in tension (reference by ID only).
- `relationship` — classify it:
  - `contradiction` / `tension` — the claims genuinely disagree;
  - `scope_difference` — they are about different parts of the problem;
  - `definition_conflict` — they use a key term differently;
  - `evidence_gap` — the comparison that would settle it has not been done;
  - `evidence_conflict` — sources point in different directions;
  - `version_conflict` — preprint / accepted manuscript / publisher versions
    differ or one source is corrected, superseded, or retracted.
- `scope_dimension` — for `scope_difference`, name the exact dimension in conflict
  (e.g. `dataset_or_benchmark`, `metric`, `comparison_baseline`, `deployment_context`,
  `time_horizon`, `population_or_domain`, `limitations`).
- `why_it_matters` — why this disagreement affects the decision.
- `evidence_balance` — `supports_a` | `supports_b` | `mixed` | `insufficient`.
- `resolution_status` — `open` | `leaning` | `resolved` | `unresolvable_now`.
- `next_question` — the single question that, if answered, would most
  reduce this conflict.
- `decisive_missing_evidence` — the primary source, passage, or head-to-head
  comparison needed to resolve or narrow it.
- `human_review_required` — true/false flag for conflicts a person must adjudicate.

For `evidence_gap`, populate `decisive_missing_evidence` with the specific
primary source, benchmark, or head-to-head comparison that would settle it.
If one source supports a claim and another source limits, contradicts, corrects,
or qualifies it, record that as a contradiction rather than smoothing it over
in synthesis.

Then capture the two whole-field findings from the seed:

- **Consensus** — what *all* lenses agree on (likely true; even rivals affirm it).
- **Collective blind spot** — what *no* lens addressed. This is often the most
  valuable finding; record it explicitly as an `evidence_gap`.

Write the human-readable ledger to `04_contradiction_ledger.md` and the records
to `04_contradictions.json`.

**Council Mode** (use when evidence is contested, trade-offs are significant, a
recommendation is requested, or the topic is policy/finance/medicine/safety/
research-design/institutional/architecture): cross-examine the selected
conflicts. Each lens responds to a targeted `claim_id` or `evidence_id` with
exactly one structured move — **support**, **challenge**, **qualification**,
**request_for_evidence**, or **reframing**. Challenges should ask whether the
cited passage actually entails the atomic claim and whether the claim preserves
source scope. Keep it **bounded**: ≤2 rounds,
≤5 items per lens, and stop when no new high-impact contradiction appears. Log
the exchange in `04_council_deliberation.md`/`.jsonl`. Never force consensus —
an honest "unresolved" is a valid outcome.
