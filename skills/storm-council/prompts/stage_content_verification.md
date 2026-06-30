# Content verification prompt · Extractor, entailment judge, scope auditor

> Use after Stage 3 has produced `03_claims.jsonl`, `03_evidence.jsonl`, and
> `03_source_registry.csv`.
>
> Writes: `03_evidence_verdicts.jsonl` (one JSON object per line). Shape:
> [`../templates/evidence_verdict.json`](../templates/evidence_verdict.json).

---

Verify whether each cited passage supports each atomic claim at the claim's
stated scope. This is an LLM-assisted audit layer: the deterministic verifier
will check that your verdict exists and is well formed, but it cannot and must
not be described as proving entailment.

## Inputs

- Claims: `03_claims.jsonl`
- Evidence records: `03_evidence.jsonl`
- Source registry: `03_source_registry.csv`
- Any retrieved full text, tables, figures, or standards clauses available in
  the run context.

## Step 1: Extract candidate support

For every claim/evidence pair:

1. Read the full atomic `claim_text`.
2. Read the linked `evidence_excerpt` and locator.
3. If the excerpt is too thin, inspect the cited page/section/table/figure/
   equation/clause/paragraph when available and summarize only the relevant
   passage.
4. Do not use title, abstract, topic similarity, citation count, or source
   reputation as a substitute for passage-level support.

If the source material is unavailable, keep the verdict `uncertain`; do not
infer support from bibliographic metadata.

## Step 2: Entailment judge

Decide only whether the located evidence entails the exact claim:

- `entails` — the located passage/table/figure supports the whole atomic claim.
- `partial` — the passage supports part of the claim or a weaker version.
- `does_not_entail` — the passage is unrelated, contradicts the claim, reports a
  different quantity, or otherwise does not support the claim.
- `uncertain` — available material is insufficient or ambiguous.

uncertain is a first-class, non-fatal verdict. Use it whenever support cannot
be responsibly judged. Never upgrade uncertainty into confidence.

## Step 3: Scope auditor

Separately judge whether the claim preserves the source's scope:

- `yes` — metric, baseline, dataset, population/domain, deployment context,
  time horizon, and caveats are preserved.
- `narrowed` — the claim is narrower than the source or omits some generality.
- `overclaimed` — the claim expands beyond the source, such as `some -> all`,
  one benchmark -> general case, metric A -> overall superiority, simulation ->
  deployment, association -> causation, or short-term -> long-term.
- `uncertain` — scope cannot be judged from available material.

## Required output

Write `03_evidence_verdicts.jsonl`, one JSON object per `(claim_id,
evidence_id)` pair that you judge:

```json
{
  "claim_id": "C-001",
  "evidence_id": "E-001",
  "judged_claim": "Atomic claim text.",
  "verdict": "entails",
  "scope_preserved": "yes",
  "rationale": "One sentence tied to the passage, metric, baseline, or scope.",
  "human_review_required": false
}
```

Strict schema:

- `claim_id` must be an existing `C-###`.
- `evidence_id` must be an existing `E-###`.
- `verdict` must be exactly one of: `entails`, `partial`,
  `does_not_entail`, `uncertain`.
- `scope_preserved` must be exactly one of: `yes`, `narrowed`,
  `overclaimed`, `uncertain`.
- `rationale` must be a short non-empty string.
- `human_review_required` must be a boolean. Set it to `true` for `partial`,
  `does_not_entail`, `uncertain`, `narrowed`, or `overclaimed`.

Do not call the output "verified" just because a source exists. The verdict is
an inspectable LLM-assisted judgement for human review.
