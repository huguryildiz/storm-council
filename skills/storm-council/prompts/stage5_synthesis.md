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

**Do not** upgrade an `unsupported`/`contested` claim into a confident
conclusion. Every external fact in the brief must trace to a source ID, and
every direct factual support claim should trace through an `evidence_id` with an
exact locator when available.
