# Stage 6 prompt · Adversarial Review

> Extends seed [`/prompts/4.md`](../../../prompts/README.md) — "peer-review your
> own briefing". The seed asks the author to score confidence, name the weakest
> claim, check for bias, find a missing perspective, and assign a grade. This
> stage keeps every one of those checks but runs them as an **independent
> reviewer with a computed verdict** — the synthesis does not get to grade
> itself, and the scores are produced by `verify.py`, not asserted by the model.
>
> Writes: `06_adversarial_review.md` + `06_quality_gate.json`. Shape:
> [`../templates/quality_gate.json`](../templates/quality_gate.json).

---

Independently review the synthesis for **{{topic}}**. Do **not** let the stage-5
author grade its own work — adopt a reviewer stance whose job is to find what is
weak.

Write `06_adversarial_review.md` auditing, with specific claim/source/
contradiction IDs as evidence:

1. **Confidence scores** — for each headline finding, a credibility score and a
   one-line justification (the seed's 1–10 scoring).
2. **Weakest link** — the claim you trust least, and the *specific* evidence
   needed to confirm or kill it (the seed's "weakest link" question).
3. **Bias check** — is any single lens over-represented? Did one voice dominate
   the synthesis? Is source concentration distorting the picture?
4. **Missing perspective** — is there a sixth lens whose inclusion would change
   the conclusions? Name it and what it would add.
5. **Integrity audit** — citation mismatches, supported claims with no source,
   overconfident wording, low-quality-source dependence, contradictions hidden
   by the synthesis, recommendations not justified by evidence, missing time
   sensitivity, smuggled value judgements.
6. **Overall note** — if a tough external reviewer graded this brief, what grade
   and what must be fixed first (the seed's "Stanford professor" check).

Then compute the verdict **deterministically** — do not hand-set the scores:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/verify.py" <output_dir> --write
```

`verify.py` checks reference integrity, computes the four scores
(coverage, traceability, contradiction-handling, recommendation-support), writes
`06_quality_gate.json` with one verdict — `PASS` · `PASS_WITH_CAVEATS` ·
`REVISE` · `BLOCKED_PENDING_EVIDENCE` — and patches `report_data.json`.

**Honesty rule:** the report's status banner may show a green / `PASS` state
**only** if live retrieval/verification actually happened. If sources were not
verified, mark the run `ILLUSTRATIVE` / `UNVERIFIED`. Never fake a verification
badge, and never talk the reviewer into approving weak work — the verdict is
computed, not negotiated.
