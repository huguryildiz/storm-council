# Contributing to Storm Council

Storm Council is a Claude Code skill. It values **traceability, honesty about
uncertainty, and first-class disagreement** over feature count. Contributions
that strengthen those properties are especially welcome.

## What lives where

- [`skills/storm-council/SKILL.md`](skills/storm-council/SKILL.md) — the skill
  itself (the staged instructions Claude follows).
- [`skills/storm-council/templates/`](skills/storm-council/templates/) — the
  JSON/Markdown shapes for each artifact.
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
(priorities, expected evidence, likely blind spots). Keep lenses configurable,
not hard-coded roles.

## Validating the plugin

```bash
claude plugin validate .
```
