# Origin seed prompts

`1.md`–`4.md` are the four original prompts that Storm Council grew out of. They
are kept verbatim (in Turkish) as the project's seed and design record:

| Seed | Idea |
| --- | --- |
| [`1.md`](1.md) | Simulate five competing expert perspectives; for each, a position, its strongest evidence, and the one thing no other perspective would say. |
| [`2.md`](2.md) | Map the contradictions across those perspectives: who has the strongest/weakest evidence, the one question that resolves the biggest conflict, what they all agree on, and the blind spot none addressed. |
| [`3.md`](3.md) | Synthesise into a briefing: one-paragraph summary, five confidence-ranked findings, a hidden connection, an actionable insight, and a frontier question. |
| [`4.md`](4.md) | Adversarially peer-review the briefing: confidence scores, weakest link, bias check, missing perspective, overall grade. |

## These are seeds, not the runbook

Do **not** run the skill straight from these four prompts. They prove the core
idea but lack source traceability, typed claims, an explicit contradiction
ledger, and a computed quality gate — the things that separate a clever
brainstorm from a defensible decision brief.

The production prompts that **extend** these seeds into the six-stage,
artifact-producing workflow live in the skill:

→ [`skills/storm-council/prompts/`](../skills/storm-council/prompts/README.md)

That library maps each seed above to the stage it became, in English, with the
claim/source/contradiction shapes and the deterministic verify-and-render step.
Edit the seeds only to record design intent; edit the stage prompts to change
how the skill actually runs.
