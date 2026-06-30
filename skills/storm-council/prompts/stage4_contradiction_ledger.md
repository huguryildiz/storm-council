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
- `claim_ids` — the specific claims in tension (reference by ID only).
- `lenses` — which lenses they came from.
- `type` — classify it:
  - `contradiction` / `tension` — the claims genuinely disagree;
  - `scope_difference` — they are about different parts of the problem;
  - `definition_conflict` — they use a key term differently;
  - `evidence_gap` — the comparison that would settle it has not been done.
- `evidence_balance` — which side currently has stronger evidence, and why
  (cite source IDs).
- `resolution_status` — `open` | `leaning` | `resolved` | `unresolvable_now`.
- `decisive_question` — the single question that, if answered, would most
  reduce this conflict (the seed's "one question that resolves the biggest
  disagreement").
- `human_review` — true/false flag for conflicts a person must adjudicate.

Then capture the two whole-field findings from the seed:

- **Consensus** — what *all* lenses agree on (likely true; even rivals affirm it).
- **Collective blind spot** — what *no* lens addressed. This is often the most
  valuable finding; record it explicitly as an `evidence_gap`.

Write the human-readable ledger to `04_contradiction_ledger.md` and the records
to `04_contradictions.json`.

**Council Mode** (use when evidence is contested, trade-offs are significant, a
recommendation is requested, or the topic is policy/finance/medicine/safety/
research-design/institutional/architecture): cross-examine the selected
conflicts. Each lens responds to a targeted `claim_id` with exactly one
structured move — **support**, **challenge**, **qualification**,
**request_for_evidence**, or **reframing**. Keep it **bounded**: ≤2 rounds,
≤5 items per lens, and stop when no new high-impact contradiction appears. Log
the exchange in `04_council_deliberation.md`/`.jsonl`. Never force consensus —
an honest "unresolved" is a valid outcome.
