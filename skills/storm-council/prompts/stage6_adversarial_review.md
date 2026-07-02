# Stage 6 prompt · Adversarial Review

> Peer-review the briefing — score confidence, name the weakest claim, check
> for bias, find a missing perspective, assign a grade — but run every check as
> an **independent reviewer with a computed verdict**: the synthesis does not
> get to grade itself, and the scores are produced by `verify.py`, not asserted
> by the model.
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
6. **Publication/content verification audit** — identify any source that is only
   metadata- or abstract-level, any missing DOI/version/retraction status, any
   `direct_support` claim without a page/section/table/figure/equation/clause/
   paragraph locator, any secondary citation used instead of a primary source,
   any missing `03_support_packets.jsonl` packet or `03_evidence_verdicts.jsonl`
   entry for located direct/strong/comparative support, any support packet whose
   quote is not present in local `source_material/`, any `does_not_entail` or
   `overclaimed` verdict, and any claim whose wording exceeds the cited source's
   scope. Target packet IDs (`P-###`) and evidence IDs (`E-###`) as well as
   claim IDs (`C-###`).
7. **Overall note** — if a tough external reviewer graded this brief, what grade
   and what must be fixed first (the seed's "Stanford professor" check).

Then compute the verdict **deterministically** — do not hand-set the scores:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/verify.py" <output_dir> --write
```

If the run includes `03_support_packets.jsonl` and `03_evidence_verdicts.jsonl`,
treat them as inspectable passage-support audit artifacts. Packets bind a claim
and evidence ID to a local quoted passage; verdicts record `verdict` (`entails`
| `partial` | `does_not_entail` | `uncertain`) and `scope_preserved` (`yes` |
`narrowed` | `overclaimed` | `uncertain`) for each judged packet. `uncertain`
is a valid non-fatal verdict that must downgrade confidence rather than fake
support.

`verify.py` checks reference integrity plus deterministic publication/content
guards (duplicate/malformed DOI, retracted/superseded source flags,
direct-support locator requirements, support packet path/hash/quote checks,
abstract-only gating, comparative-claim scope fields, obvious overclaiming
language, and presence/shape/outcome of LLM-assisted or human evidence
verdicts). It does **not** decide semantic entailment itself. It computes five
scores (coverage, traceability, argument-support, contradiction-handling,
recommendation-support), writes `06_quality_gate.json` with one verdict —
`PASS` · `PASS_WITH_CAVEATS` · `REVISE` ·
`BLOCKED_PENDING_EVIDENCE` — and patches `report_data.json`.

**Honesty rule:** the report's status banner may show a green / `PASS` state
**only** if live retrieval/verification actually happened. If sources were not
verified, mark the run `ILLUSTRATIVE` / `UNVERIFIED`. Never fake a verification
badge, and never talk the reviewer into approving weak work — the verdict is
computed, not negotiated.
