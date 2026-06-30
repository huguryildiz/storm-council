# Storm Council — Research Lens Agents

The five files in this directory define the **research lens subagents** used by the Storm Council workflow. Each lens is a focused research perspective that produces structured, source-traceable claims. They are deliberately diverse so their disagreements surface real contradictions rather than echo-chamber consensus.

## Lens summary

| Agent | Focus | Blind spot |
|---|---|---|
| [academic](academic.md) | Peer-reviewed evidence, benchmarks, methodological limits | Under-weights deployment and maintenance reality |
| [economist](economist.md) | Cost, incentives, opportunity cost, distributional effects | Measures only what is quantifiable |
| [historian](historian.md) | Precedent, analogies, repeated failure patterns, institutional context | Assumes the past fully constrains a new method |
| [practitioner](practitioner.md) | Operational constraints, implementation reality, adoption friction | Discounts research advances not yet productized |
| [skeptic](skeptic.md) | Unsupported claims, weak assumptions, incentive problems, missing evidence | Reflexively dismisses genuinely novel methods |

Each agent is instructed to **name its own blind spot** so the orchestrator and synthesiser can compensate.

## What each agent produces

Every lens returns 3–6 structured claims in the Storm Council claim shape:

```json
{
  "claim_id": "C-001",
  "claim_type": "fact | inference | forecast | assumption | recommendation",
  "evidence_status": "supported | partially_supported | unsupported | contested",
  "confidence": 0.85,
  "source_ids": ["S-001"],
  "counterevidence_ids": [],
  "limitations": "..."
}
```

Claims with `supported` or `partially_supported` status must reference at least one `S-###` source. If no source was retrieved, the agent marks the claim `unsupported` — it never invents citations.

Sources follow the companion shape in `skills/storm-council/templates/source_record.json`.

## Two operating modes

### Hub-and-Spoke

Each lens researches independently. The orchestrator assembles their claims into the shared evidence file (`03_claims.jsonl`) and contradiction ledger (`04_contradictions.json`). Use this for narrow or lower-stakes questions.

### Council Mode

Lenses cross-examine one another's claims. After an initial research pass, selected claims from each lens are shared with the others. Each lens responds to each claim with exactly one structured move:

| Move | When to use |
|---|---|
| `support` | The claim is correct and you have corroborating evidence |
| `challenge` | The claim is incorrect or misleading; state why |
| `qualification` | The claim is directionally right but overstated or missing conditions |
| `request_for_evidence` | The claim is unverified and needs a specific source type |
| `reframing` | The claim frames the question in a way that obscures a more important issue |

Council Mode runs at most **2 cross-examination rounds** and surfaces a new contradiction only when it is high-impact. Lenses do not loop indefinitely.

Use Council Mode automatically for: contested evidence, policy, finance, medicine, safety, security, institutional decisions.

## Subagent invocation

Each agent ships as a named Claude Code subagent:

```
storm-council:academic
storm-council:economist
storm-council:historian
storm-council:practitioner
storm-council:skeptic
```

In Council Mode, dispatch each as its own subagent so they research in independent contexts before cross-examining. The main workflow orchestrator then assembles their outputs into the shared artifacts.

All agents have `disallowedTools: Write, Edit` — they return structured data to the orchestrator and never write files themselves.

## Adding or replacing a lens

1. Create a new `.md` file in this directory with the same frontmatter shape (`name`, `description`, `disallowedTools`).
2. Define `## Your focus`, `## Priority questions`, `## What evidence you seek`, and name the lens's blind spot.
3. Include the Council Mode instructions so the lens knows how to respond to other lenses' claims.
4. Register the lens in Stage 2 (`02_perspective_scan.md`) of the workflow.

See `skills/storm-council/SKILL.md` for the full workflow specification.
