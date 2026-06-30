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
