# Content verification prompt · Extractor, entailment judge, scope auditor

> Use after Stage 3 has produced `03_claims.jsonl`, `03_evidence.jsonl`,
> `03_support_packets.jsonl`, `03_source_registry.csv`, and local
> `source_material/` files.
>
> Writes: `03_evidence_verdicts.jsonl` (one JSON object per line). Shape:
> [`../templates/evidence_verdict.json`](../templates/evidence_verdict.json).

---

Verify whether each packet's quoted passage supports each atomic claim at the
claim's stated scope. This is an LLM-assisted or human-review audit layer: the
deterministic verifier will check that the packet exists, hashes local material,
quotes material that is actually present, and has a well-formed verdict, but it
cannot and must not be described as proving truth.

## Inputs

- Claims: `03_claims.jsonl`
- Evidence records: `03_evidence.jsonl`
- Passage support packets: `03_support_packets.jsonl`
- Source registry: `03_source_registry.csv`
- Local source text files under `source_material/`.

## Step 1: Extract candidate support

For every support packet:

1. Read the full atomic `claim_text`.
2. Read the linked packet's `quoted_passage`, locator, and `context_note`.
3. Use only the packet passage plus the claim's scope fields for the verdict.
4. Do not use title, abstract, topic similarity, citation count, or source
   reputation as a substitute for passage-level support.

If source material is unavailable, the packet is `metadata_only`, or the quoted
passage is too thin, keep the verdict `uncertain` or `partial`; do not infer
support from bibliographic metadata.

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

Write `03_evidence_verdicts.jsonl`, one JSON object per support packet that you
judge:

```json
{
  "claim_id": "C-001",
  "evidence_id": "E-001",
  "packet_id": "P-001",
  "judged_claim": "Atomic claim text.",
  "claim_atoms": ["Atomic proposition judged from the claim."],
  "entailed_atoms": ["Atoms entailed by the packet passage."],
  "unsupported_atoms": [],
  "verdict": "entails",
  "scope_preserved": "yes",
  "rationale": "One sentence tied to the passage, metric, baseline, or scope.",
  "human_review_required": false,
  "judge_type": "llm_assisted",
  "judge_prompt_version": "stage_content_verification.v2"
}
```

Strict schema:

- `claim_id` must be an existing `C-###`.
- `evidence_id` must be an existing `E-###`.
- `packet_id` must be an existing `P-###` in `03_support_packets.jsonl`.
- `claim_atoms`, `entailed_atoms`, and `unsupported_atoms` must be lists.
- `verdict` must be exactly one of: `entails`, `partial`,
  `does_not_entail`, `uncertain`.
- `scope_preserved` must be exactly one of: `yes`, `narrowed`,
  `overclaimed`, `uncertain`.
- `rationale` must be a short non-empty string.
- `human_review_required` must be a boolean. Set it to `true` for `partial`,
  `does_not_entail`, `uncertain`, `narrowed`, or `overclaimed`.
- `judge_type` must be `llm_assisted` or `human`.
- `judge_prompt_version` must be a non-empty string.

Do not call the output "verified" just because a source exists or its DOI
resolves. The verdict is an inspectable judgement over a local quoted passage
for human review.
