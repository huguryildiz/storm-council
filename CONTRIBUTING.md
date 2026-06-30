# Contributing to Storm Council

Storm Council is a Claude Code skill. It values **traceability, honesty about
uncertainty, and first-class disagreement** over feature count. Contributions
that strengthen those properties are especially welcome.

## What lives where

- [`skills/storm-council/SKILL.md`](skills/storm-council/SKILL.md) — the skill
  itself (the staged instructions Claude follows).
- [`skills/storm-council/templates/`](skills/storm-council/templates/) — the
  JSON/Markdown shapes for each artifact.
- [`skills/storm-council/prompts/`](skills/storm-council/prompts/) — per-stage
  prompt templates (stages 1–6). Each file maps to one stage of the workflow.
- [`agents/`](agents/) — the five research lens subagents (`academic`,
  `economist`, `historian`, `practitioner`, `skeptic`). Each is a Claude Code
  subagent file usable independently in Council Mode via `storm-council:<lens>`.
- [`docs/`](docs/) — methodology, claim traceability, and safety/limitations.
- [`examples/`](examples/) — a complete worked example's output artifacts.
- `.claude-plugin/` — the plugin + marketplace manifests.
- `scripts/verify.py` — pure-stdlib integrity check + quality-gate scorer (no LLM/API key).
- `scripts/render_report.py` — pure-stdlib JSON → HTML report renderer (no LLM/API key).

## Principles to preserve

- **No fake citations, no invented sources.** Factual claims reference stable
  source IDs; unsupported claims are labelled, not silently upgraded.
- **No forced consensus.** Disagreement is a first-class artifact. An honest
  "unresolved" is a valid result.
- **Bounded deliberation.** Council Mode is capped (rounds + cross-examination
  items) and stops when no new high-impact contradiction appears.
- **Never fake retrieval.** Only claim something was browsed or verified if a
  tool actually returned that evidence.

## Adding a perspective

Add the lens to the perspective list in `SKILL.md` with a short charter
(priorities, expected evidence, likely blind spots). Then create the matching
subagent file in `agents/<lens>.md` following the pattern of the existing five.
Keep lenses configurable, not hard-coded roles.

## Adding or modifying an agent

Each file in `agents/` is a Claude Code subagent. The header frontmatter must
include `name`, `description`, and `disallowedTools` (agents should not write
or edit files directly — that is the orchestrator's job). The body specifies
what the lens focuses on, its priority questions, evidence it seeks, and its
declared blind spots. Keep agent files narrow: they set the reasoning frame, not
the full workflow.

## Adding a prompt template

Stage prompts live in `skills/storm-council/prompts/stage<N>_<name>.md`. If you
add a stage or substantially change a prompt, update the stage summary table in
`skills/storm-council/SKILL.md` and the methodology in `docs/methodology.md`.

## Validating the plugin

```bash
# Check plugin manifest
claude plugin validate .

# Verify artifact integrity and quality-gate scores (no API key needed)
python3 scripts/verify.py <output_dir>

# Render the shareable report
python3 scripts/render_report.py <output_dir>/report_data.json -o <output_dir>/storm_council_report.html
```

Both scripts are pure standard library — no network, no LLM, no API key required.

## Reporting issues

Open a GitHub issue describing:

- what you asked Storm Council to do,
- which stage produced the unexpected output,
- what you expected vs. what you got.

Attach the relevant artifact file if possible.
