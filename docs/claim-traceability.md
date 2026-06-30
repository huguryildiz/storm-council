# Claim traceability

Traceability is the core promise: every consequential statement can be followed
back to its evidence, or is clearly marked as lacking it.

## Claim IDs

Each claim has a stable `claim_id` of the form `C-001`. Claims never reference
sources or other claims by prose — only by ID. This makes the whole graph
machine-checkable (`validators.link_errors`).

## Source IDs

Each source has a stable `source_id` of the form `S-001` and a `source_type`
(`primary`, `peer_reviewed`, `government`, `standards`, `industry`, `news`,
`blog`, `other`). A claim's `source_ids` must resolve to real source records.

## Evidence status

`evidence_status` is separate from confidence:

| Status | Meaning |
| --- | --- |
| `supported` | Backed by cited sources |
| `partially_supported` | Some support; gaps remain |
| `unsupported` | Asserted without evidence (must be labelled) |
| `contested` | Sources or perspectives conflict |

A `supported` fact or inference **must** cite at least one source — enforced in
the schema, re-checked by the reviewer.

## Publication identity is not claim support

A source can be real, correctly identified, and topically relevant while still
not supporting the specific claim being made. Source records therefore carry
publication-identity fields where available: DOI/arXiv/PubMed/OpenAlex/Semantic
Scholar identifiers, publication/version status, duplicate-version linkage,
retraction/correction/supersession status, and full-text availability. Semantic
Scholar is useful for discovery and citation graphs, but it is not the sole
source of truth for publication identity.

Optional Phase-3 metadata adapters may add three local artifacts beside the run:

| Artifact | Meaning |
| --- | --- |
| `metadata_verification.jsonl` | Per-source record of which metadata adapters were checked and what identity status resulted. |
| `source_versions.jsonl` | Canonical source/version map with DOI identifiers, duplicate linkage, and retracted/corrected/superseded flags. |
| `retrieval_log.jsonl` | Cache/network audit log for adapter requests, including cache hits, offline failures, and timestamps. |

The publication metadata hierarchy is publisher / DOI resolver first, then
Crossref, then OpenAlex. Semantic Scholar is discovery and citation-graph
support only; by itself it must not set a source to `PUBLISHED_VERIFIED`.
If no adapter ran, source identity stays `UNRESOLVED` rather than implicitly
verified.

## Evidence records

Direct support must pass through an `evidence_id` (`E-001`) rather than only a
source ID. Evidence records identify the exact supporting passage, table, figure,
equation, clause, or paragraph and include a short excerpt. A claim may cite a
source because it is relevant, but it cannot be marked `direct_support` unless
the supporting evidence has a concrete locator.

## Evidence verdicts

Phase 4 adds `03_evidence_verdicts.jsonl`: one LLM-assisted verdict for each
judged `(claim_id, evidence_id)` pair. The verdict layer answers the question
"does this cited passage support this atomic claim at this scope?" in an
inspectable artifact:

| Field | Values |
| --- | --- |
| `verdict` | `entails`, `partial`, `does_not_entail`, `uncertain` |
| `scope_preserved` | `yes`, `narrowed`, `overclaimed`, `uncertain` |

`uncertain` is a first-class outcome. It downgrades confidence and requires
review; it must not be rewritten as support. `does_not_entail` and
`overclaimed` are blocking for direct/strong/comparative support.

The deterministic verifier checks that required verdicts exist, have valid enum
values, name real claim/evidence IDs, include a rationale, and use a boolean
`human_review_required`. It does **not** prove semantic entailment itself; the
entailment and scope judgement is LLM-assisted and should remain visible for
human review.

Content-verification statuses:

| Status | Meaning |
| --- | --- |
| `direct_support` | The located evidence directly entails the atomic claim |
| `partial_support` | The located evidence supports only part of the claim |
| `indirect_support` | The evidence is suggestive but not direct |
| `contradiction` | The evidence cuts against the claim |
| `out_of_scope` | The evidence is about a different scope |
| `not_verifiable` | Support could not be verified from available material |

Abstract-only evidence cannot directly support strong empirical, causal,
comparative, quantitative, or safety-critical claims. It should be treated as
`partial_support` or lower and clearly caveated.

## Confidence

`confidence` is a 0.0–1.0 subjective strength of belief. It is intentionally
distinct from evidence status: a high-confidence *forecast* is still a forecast.
The reviewer flags `confidence >= 0.8` on anything not `supported` as possible
overconfidence.

## Counter-evidence

A claim's `counterevidence_ids` point at *other claims* that push back on it.
This is how the contradiction stage and the argument map find tensions, and how
the synthesis avoids one-sided presentation.

## Recommendation support

Recommendations are first-class claim types and decision options. The reviewer's
`recommendation_support_score` measures whether options carry an explicit
evidence-strength label and whether recommended actions reference specific
findings (claim/conflict IDs). Recommendations that float free of evidence are
flagged.
