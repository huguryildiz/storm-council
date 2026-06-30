# Stage prompt library

Runnable prompt templates — one per stage of the six-stage Storm Council
workflow. They are the operational instructions the orchestrator (or a
dispatched lens subagent) follows at each stage. Each writes the stage
artifact(s) named in [`../SKILL.md`](../SKILL.md) before the next stage begins.

These templates **extend** the four origin seed prompts kept at the repo root
([`/prompts/1.md`–`4.md`](../../../prompts/README.md)). The seeds prove the core
idea — *simulate competing experts, map their contradictions, synthesise, then
peer-review the synthesis*. The templates below carry that idea into a
rigorous, source-traceable, artifact-producing pipeline: explicit claim shapes,
stable source IDs, separated fact/inference/recommendation, named blind spots,
and a computed quality gate.

## Origin seed → stage map

| Origin seed (root `/prompts`) | Extended into | Stage prompt |
| --- | --- | --- |
| — (new) | Decision framing | [`stage1_decision_frame.md`](stage1_decision_frame.md) |
| `1.md` — five expert perspectives | Lens charters | [`stage2_perspective_scan.md`](stage2_perspective_scan.md) |
| `1.md` — strongest evidence + unique insight | Source-grounded claims | [`stage3_evidence_inquiry.md`](stage3_evidence_inquiry.md) |
| `2.md` — map the contradictions | Contradiction ledger | [`stage4_contradiction_ledger.md`](stage4_contradiction_ledger.md) |
| `3.md` — synthesise the briefing | Source-mapped synthesis | [`stage5_synthesis.md`](stage5_synthesis.md) |
| `4.md` — peer-review your own briefing | Adversarial review | [`stage6_adversarial_review.md`](stage6_adversarial_review.md) |

## How to use

Run the stages in order. Each prompt assumes the prior stage's artifacts already
exist in the output folder. Substitute the `{{double_brace}}` placeholders before
running. Where a prompt references a data shape (claim, source, contradiction,
quality gate), use the JSON templates in [`../templates/`](../templates/) so IDs
stay consistent across every artifact.

The seeds were written in Turkish; these templates are in English to match the
rest of the skill. They are extensions, not translations — do not treat them as
line-for-line equivalents of the seeds.
