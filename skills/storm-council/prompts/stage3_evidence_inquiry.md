# Stage 3 prompt · Evidence-Grounded Inquiry

> Each lens's strongest evidence and unique insight must become a
> **source-grounded, typed, traceable claim** rather than an informal
> assertion — the difference between a persona's opinion and a defensible
> finding.
>
> Writes: `03_evidence_plan.md`, `03_claims.jsonl`, `03_sources.bib`,
> `03_source_registry.csv`, `03_evidence.jsonl`. Shapes:
> [`../templates/claim_record.json`](../templates/claim_record.json),
> [`../templates/source_record.json`](../templates/source_record.json),
> [`../templates/evidence_record.json`](../templates/evidence_record.json).

---

For **{{topic}}**, each chartered lens from `02_perspective_scan.md` now
investigates and produces evidence. You may dispatch each lens as its subagent
(`storm-council:<lens>`) so they reason in independent contexts, then collect
their output.

**First**, write a short `03_evidence_plan.md`: for each lens, the queries it
will run, the sources it expects to find, and what would count as
disconfirming evidence.

For each mandatory query, log results using exactly this pipe-delimited format
so the HTML renderer can parse authors for APA-style display:

```markdown
- `<query string>`: result_count=<N>
  - selected/top result: <title> | authors: <Last, F., Last, F.> | venue: <Journal or Conference Name> | paperId=<id> | year=<YYYY> | citationCount=<N>
```

If the API returns no results, write a single sub-item:

```markdown
  - no top-3 paper selected because <reason>.
```

Include up to 3 `selected/top result` sub-items per query. The `authors` field
is required when author data is available from the retrieval tool; omit it only
when the API returns no author metadata.

**Then**, for each lens, produce **3–6 claims**. Every claim must be **atomic** —
one proposition per claim. If a finding bundles several propositions
(e.g. "method X improves quality *and* reduces solve time"), split it into
separate claims (`C-001`, `C-002`, …) so each can be verified independently.
Every claim is a structured record:

- `claim_id` — stable, e.g. `C-001`.
- `lens` — which lens produced it.
- `statement` — one sentence.
- `claim_type` — `fact` | `inference` | `forecast` | `assumption` |
  `recommendation`. Keep these distinct; never present a forecast or value
  judgement as a fact.
- `claim_strength` — `descriptive` | `comparative` | `causal` | `quantitative` |
  `recommendation`. Comparative, causal, and quantitative claims carry a higher
  evidence bar (see below).
- `evidence_status` — `supported` | `partially_supported` | `unsupported` |
  `contested`.
- `confidence` — 0.0–1.0. This is the lens's subjective strength of belief, **not
  a calibrated probability** — nothing back-tests it, so never present the digits
  as if they were.
- `confidence_basis` **and/or** `confidence_band` — every `confidence` float must
  carry its provenance so the number is never read as calibrated. Set them from
  **evidence tier × verdict × `full_text_status`**:
  - `confidence_band`: `high` only when a `peer_reviewed`/`official` source
    (`source_class`) gives `direct_support` on `full_text`; `moderate` for
    `partial_support`, a `preprint`/`gray` tier, or `abstract_only` full text;
    `low` for `run_log`-only support, `indirect_support`, `unsupported`/`contested`
    status, or `metadata_only`. Abstract-only or run-log support caps the band at
    `moderate`/`low` no matter the float.
  - `confidence_basis`: one short phrase naming the tier + verdict + full-text
    status (and any deliberation move that moved it), e.g.
    `"one full-text safe-RL survey; scope-narrowed after M-001"`.
- `source_ids` — e.g. `["S-001"]`. **Every `fact`/`inference` presented as
  supported must cite at least one source ID**, with a URL where one exists.
- `evidence_ids` — e.g. `["E-001"]`. The specific passages/tables/figures that
  do the supporting (see the evidence registry below).
- `content_verification` — for any claim you present as direct support, record
  `status` (`direct_support` | `partial_support` | `indirect_support` |
  `contradiction` | `out_of_scope` | `not_verifiable`), `full_text_status`
  (`full_text` | `abstract_only` | `metadata_only`), an `entailment_rationale`,
  and an `evidence_locator`.
- `support_scope` — preserve the source's scope: `population_or_domain`,
  `dataset_or_benchmark`, `comparison_baseline`, `metric`, `conditions`,
  `time_horizon`, `deployment_context` (`deployment`/`simulation`), and
  `limitations`. **Comparative claims must fill `metric`, `comparison_baseline`,
  and `dataset_or_benchmark`.**
- `counterevidence_ids` — sources or claim IDs that cut against it.
- `limitations` — what would weaken or overturn the claim.

Write claims to `03_claims.jsonl` (one JSON object per line).

**Build an evidence registry.** For every supported claim, write the exact
supporting evidence to `03_evidence.jsonl` (one record per line, shape:
[`../templates/evidence_record.json`](../templates/evidence_record.json)): an
`evidence_id`, the `source_id`, a `locator` (page+section, table, figure,
equation, clause, or paragraph hint), and a short `evidence_excerpt`. A claim
marked `direct_support` **must** point at an evidence record that has a concrete
locator — relevance or topic-similarity alone is not support.

Register every source once in `03_source_registry.csv` and `03_sources.bib`
using the source shape: `source_id`, `title`, `author/publisher`, `year`,
`url`, `source_type`, identifiers (`doi`, `arxiv_id`, …), a publication
`status` (`PUBLISHED_VERIFIED` / `PREPRINT_VERIFIED` / `RETRACTED` /
`SUPERSEDED` / …), a `full_text_status`, a `source_class`
(`peer_reviewed` / `preprint` / `official` / `gray` / `run_log`; a run's own
search/retrieval log is `run_log` and never counts as external support for a
claim — default an unknown class to `gray`, never `peer_reviewed`), and a
`credibility` note. Claims reference sources **only by ID**.

**Hard rules:**
- **Never fake retrieval.** Only mark a claim `supported` if a tool actually
  returned the evidence. If you have no retrieval tool, say so, mark claims
  `unsupported`/`partially_supported`, and do **not** invent sources or URLs.
  Fabricated citations are a hard failure.
- **Relevance is not entailment.** Title/abstract similarity, embedding
  similarity, or "an LLM says it looks relevant" never counts as support.
- **Abstract-only limits strength.** A source you only saw as title/abstract
  cannot `direct_support` a strong empirical, causal, comparative, quantitative,
  or safety-critical claim — at most mark it `partial_support` and lower the
  confidence.
- **Preserve scope.** Do not turn `some → all`, `simulation → deployment`,
  `associated with → causes`, one dataset → the general case, or
  `better on metric A → superior overall`.
- **Primary over secondary.** A paper citing another paper is not evidence for
  the original finding; cite the primary source where feasible.
- **Record negative evidence and the *absence* of evidence explicitly** — they
  are findings, not gaps to paper over.
- Capture each lens's **unique contribution** as at least one claim other
  lenses did not raise.

`scripts/verify.py` enforces the deterministic half of these rules
(locator required for `direct_support`, abstract-only gating, comparative scope
fields, duplicate/retracted sources, overclaiming language). Run it after
Stage 6.
