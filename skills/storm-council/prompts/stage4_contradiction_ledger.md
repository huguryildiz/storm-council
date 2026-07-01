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

- `id` — stable canonical id, e.g. `X-001` (keep `conflict_id`/`contradiction_id`
  as aliases for one release).
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
- `resolution_status` — `open` | `leaning` | `resolved` | `partially_resolved` |
  `unresolvable_now`.
- `resolution` — required when status is `resolved`/`partially_resolved`. Give
  `basis` (`evidence` | `deliberation` | `concession` | `none`), the
  `evidence_ids` (`E-###`) and/or `move_ids` (`M-###`) that settled it, and a
  short `rationale`. **A `resolved`/`partially_resolved` status only counts
  toward the contradiction score when `basis != none` and it cites at least one
  `E-###` or `M-###`.** A bare status with no basis is uncredited.
- `next_question` — the single question that, if answered, would most
  reduce this conflict.
- `decisive_missing_evidence` — the primary source, passage, or head-to-head
  comparison needed to resolve or narrow it.
- `resolution_plan` — **optional, additive.** For any contradiction *not*
  `resolved` (i.e. `unresolved`/`open`/`leaning`/`partially_resolved`), upgrade the
  `next_question`/`decisive_missing_evidence` seed into a structured, prioritized
  evidence-acquisition plan (sibling of `resolution`, never nested inside it):
  - `evidence_type_needed` — free-text category label (e.g. `head_to_head_benchmark`,
    `primary_source_full_text`, `field_data`, `expert_elicitation`, `replication`,
    `cost_data`, `regulatory_filing`). Not a fixed enum, but must be non-empty.
  - `proposed_experiment_or_source` and/or `data_source` — at least one must be
    present. The first names *what would be done*; the second names *where the
    evidence comes from*.
  - `approx_effort` — ordinal `low` | `medium` | `high`. **Never** hours, days,
    person-weeks, or currency — Storm Council has no resourcing model.
  - `decision_impact` — ordinal `would_flip` | `might_flip` | `unlikely_to_change`.
    Choose `would_flip` **only** when a linked claim is (or is expected to be)
    load-bearing to the recommendation — i.e. ranked `pivotal` in
    `decision_criticality.json` (Stage 5's 07c artifact). If 07c has not run yet,
    reserve `would_flip` for a claim you genuinely expect to be pivotal.
  - `linked_claims` — subset of this record's `claim_ids` the plan would settle.
  - `linked_options` — free-text option label(s) the resolution would help decide.
  - `linked_tripwires` — `T-###` from Phase 8's `decision_tripwires.json` when it
    exists; omit otherwise.
  - `status` — optional bookkeeping (`proposed` | `in_progress` | `done` |
    `abandoned`). It tracks the *plan*, never the contradiction: `done` does **not**
    mean the contradiction became `resolved`.
  - **Never invent value-of-information numbers.** Do not add `evsi`, `evpi`,
    `expected_value`, `probability`, `prior`, `utility`, `payoff`, or any numeric
    decision-value field — Storm Council has no decision model, utility function, or
    probability elicitation, so such a number would be a fabricated statistic. Use
    the ordinal enums only.
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
source scope. Each move carries a stable `move_id` (`M-001`, `M-002`, …) and
must state its **`effect`** — what it changed — using
[`../templates/deliberation_move.json`](../templates/deliberation_move.json):
`change_type` ∈ `none` | `confidence_delta` | `status_change` | `scope_narrowed`
| `withdrawn`, the `field` it moved, `before`/`after` values, and the `resolves`
list of `X-###` it (partially) settles. A move with no real consequence uses
`change_type: none`. When a move settles a contradiction, cite that `move_id`
in the contradiction's `resolution.move_ids`. Keep it **bounded**: ≤2 rounds,
≤5 items per lens, and stop when no new high-impact contradiction appears. Log
the exchange in `04_council_deliberation.md`/`.jsonl`. Never force consensus —
an honest "unresolved" is a valid outcome.
