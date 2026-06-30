# Stage 3 prompt · Evidence-Grounded Inquiry

> Each lens's strongest evidence and unique insight must become a
> **source-grounded, typed, traceable claim** rather than an informal
> assertion — the difference between a persona's opinion and a defensible
> finding.
>
> Writes: `03_evidence_plan.md`, `03_claims.jsonl`, `03_sources.bib`,
> `03_source_registry.csv`. Shapes: [`../templates/claim_record.json`](../templates/claim_record.json),
> [`../templates/source_record.json`](../templates/source_record.json).

---

For **{{topic}}**, each chartered lens from `02_perspective_scan.md` now
investigates and produces evidence. You may dispatch each lens as its subagent
(`storm-council:<lens>`) so they reason in independent contexts, then collect
their output.

**First**, write a short `03_evidence_plan.md`: for each lens, the queries it
will run, the sources it expects to find, and what would count as
disconfirming evidence.

**Then**, for each lens, produce **3–6 claims**. Every claim is a structured
record:

- `claim_id` — stable, e.g. `C-001`.
- `lens` — which lens produced it.
- `statement` — one sentence.
- `claim_type` — `fact` | `inference` | `forecast` | `assumption` |
  `recommendation`. Keep these distinct; never present a forecast or value
  judgement as a fact.
- `evidence_status` — `supported` | `partially_supported` | `unsupported` |
  `contested`.
- `confidence` — 0.0–1.0.
- `source_ids` — e.g. `["S-001"]`. **Every `fact`/`inference` presented as
  supported must cite at least one source ID**, with a URL where one exists.
- `counterevidence_ids` — sources or claim IDs that cut against it.
- `limitations` — what would weaken or overturn the claim.

Write claims to `03_claims.jsonl` (one JSON object per line).

Register every source once in `03_source_registry.csv` and `03_sources.bib`
using the source shape: `source_id`, `title`, `author/publisher`, `year`,
`url`, `source_type`, and a `credibility` note. Claims reference sources **only
by ID**.

**Hard rules:**
- **Never fake retrieval.** Only mark a claim `supported` if a tool actually
  returned the evidence. If you have no retrieval tool, say so, mark claims
  `unsupported`/`partially_supported`, and do **not** invent sources or URLs.
  Fabricated citations are a hard failure.
- **Record negative evidence and the *absence* of evidence explicitly** — they
  are findings, not gaps to paper over.
- Capture each lens's **unique contribution** as at least one claim other
  lenses did not raise.
