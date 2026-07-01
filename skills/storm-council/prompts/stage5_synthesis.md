# Stage 5 prompt · Source-Mapped Synthesis

> Synthesise into a briefing — a one-paragraph summary, confidence-ranked
> findings, a hidden connection, an actionable insight, and a frontier
> question — but **map every finding back to claim and source IDs**, carry the
> disagreements forward instead of erasing them, and add decision options and an
> argument map.
>
> Writes: `05_synthesis.md`, `05_argument_map.mmd`, `05_decision_brief.md`.
> Outline: [`../templates/synthesis_outline.md`](../templates/synthesis_outline.md).

---

Integrate everything — `03_claims.jsonl`, `04_contradictions.json`, the source
registry, and any council deliberation — into a synthesis for **{{topic}}** that
**does not erase disagreement**.

`05_synthesis.md` covers:

1. **Executive summary** — one paragraph. Brief a decision-maker who has 60
   seconds and needs the nuance, not just the headline.
2. **Decision context** — restate the framed decision and acceptance criteria.
3. **Strongest evidence-backed findings** — the most important things now known,
   **ranked by confidence**. For each, cite the claim IDs and note which lenses
   *support* it and which *challenge* it (the seed's "which perspectives back it,
   which question it"). Prefer claims with `direct_support` evidence locators;
   if a finding rests on `partial_support`, `abstract_only`, or `metadata_only`
   evidence, say so visibly.
4. **Main disagreements** that remain unresolved and *why* (cite contradiction
   IDs). Do not average them into a false middle.
5. **Confidence-ranked claims** — the full ranking, with evidence status.
6. **Evidence gaps** — including the collective blind spot from Stage 4.
7. **Decision options & trade-offs** — each option labelled with an honest
   evidence-strength rating.
8. **Recommended next actions** — reference claim/contradiction IDs; concrete,
   not generic (the seed's "what should someone in my role actually do
   differently").
9. **Hidden connection** — the non-obvious link across findings that only
   appears when all lenses are viewed together.
10. **Frontier question** — the one question that, if answered, would change how
    we understand the topic.
11. **Source map** — each source → the claims that cite it.

Before finalizing any headline finding or recommendation, run a scope-preservation
audit against each supporting claim's `support_scope`. Do **not** silently
transform:

- `some` → `all`;
- `can` → `will`;
- `associated with` → `causes`;
- simulation / benchmark evidence → deployed production evidence;
- one dataset or benchmark → the general case;
- short-term evidence → long-term evidence;
- statistically significant → practically meaningful;
- better on metric A → superior overall.

If a claim would require one of those expansions, downgrade it, qualify it, or
move it to `Evidence gaps`.

`05_argument_map.mmd` — a Mermaid graph connecting
`question → claims → sources → contradictions → actions`.

`05_decision_brief.md` — the one-page brief: bottom line, the few findings that
matter, the live disagreements, the recommended option with its evidence
strength, and what would change the recommendation.

`decision_criticality.json` (optional, additive) — **only** when both `options[]`
and a parseable `05_argument_map.mmd` exist. It is a *derived, ordinal,
structurally-computed* ranking, **not** a fresh judgment call and **never** a
numeric score. Apply this fixed rule and record it verbatim:

- **Inputs (exactly these):** the `options[]` `{name, strength}` values, the
  `05_argument_map.mmd` solid edges (a claim/contradiction is *linked to an
  option* iff a path of solid edges connects the option node to it), and each
  linked claim's `evidence_status` / contradiction's `resolution_status`.
  Never read `confidence`/`confidence_band` — confidence is not criticality.
- **Winner:** highest-strength option; ties broken by `options[]` order; ladder
  `strong > conditional > moderate > weak > unsupported`. Record this string as
  `recommendation_rule`, and snapshot the ranked options as `options_considered`.
- **Classify each linked claim/contradiction by *flipping* it** (supported↔unsupported /
  resolved↔unresolved). Losing an option's only supporting-claim link is one tier
  down; gaining a first link is one tier up. Then:
  - `pivotal` — the flip changes *which* option wins (`flips_recommendation: true`,
    always with a non-empty `rule_trace`).
  - `contributing` — the flip changes the winning option's *tier* but the same
    option still wins (`flips_recommendation: false`).
  - `peripheral` — no path to any option, or the flip changes neither
    (`flips_recommendation: false`). Unranked claims are simply omitted.
- `most_load_bearing` = the `pivotal` entry closest to the root question `Q`
  (fewest edge-hops; ties by `claims.jsonl`/`contradictions.json` order). It MUST
  name a `pivotal` entry, or be omitted when none is pivotal.
- **Forbidden:** any numeric importance/weight/probability; a `pivotal` label
  without `flips_recommendation: true` and a `rule_trace`; inventing a ranking
  when `options[]` or the argument map is missing (skip the file entirely).

Copy each ranking's `{criticality, flips_recommendation, affects_options}`
verbatim onto the matching `03_claims.jsonl` / `04_contradictions.json` record as
its optional `decision_criticality` mirror block. The brief gains one sentence
when a `pivotal` entry exists: *"If one assumption is wrong, this is the one most
likely to change the recommendation."*

**Do not** upgrade an `unsupported`/`contested` claim into a confident
conclusion. Every external fact in the brief must trace to a source ID, and
every direct factual support claim should trace through an `evidence_id` with an
exact locator when available.
