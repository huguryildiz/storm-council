# Stage prompt library

Runnable prompt templates — one per stage of the six-stage Storm Council
workflow. They are the operational instructions the orchestrator (or a
dispatched lens subagent) follows at each stage. Each writes the stage
artifact(s) named in [`../SKILL.md`](../SKILL.md) before the next stage begins.

Together they carry the core idea — *simulate competing experts, map their
contradictions, synthesise, then peer-review the synthesis* — into a rigorous,
source-traceable, artifact-producing pipeline: explicit claim shapes, stable
source IDs, separated fact/inference/recommendation, named blind spots, and a
computed quality gate.

## Stage map

| Stage | What it produces | Stage prompt |
| --- | --- | --- |
| 1 | Decision framing | [`stage1_decision_frame.md`](stage1_decision_frame.md) |
| 2 | Lens charters | [`stage2_perspective_scan.md`](stage2_perspective_scan.md) |
| 3 | Source-grounded claims | [`stage3_evidence_inquiry.md`](stage3_evidence_inquiry.md) |
| 4 | Contradiction ledger | [`stage4_contradiction_ledger.md`](stage4_contradiction_ledger.md) |
| 5 | Source-mapped synthesis | [`stage5_synthesis.md`](stage5_synthesis.md) |
| 6 | Adversarial review | [`stage6_adversarial_review.md`](stage6_adversarial_review.md) |

## How to use

Run the stages in order. Each prompt assumes the prior stage's artifacts already
exist in the output folder. Substitute the `{{double_brace}}` placeholders before
running. Where a prompt references a data shape (claim, source, contradiction,
quality gate), use the JSON templates in [`../templates/`](../templates/) so IDs
stay consistent across every artifact.
