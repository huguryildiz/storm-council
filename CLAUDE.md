# Storm Council — CLAUDE.md

## What this project is

A **Claude Code plugin** that runs a six-stage, contradiction-aware research workflow.  
One question → five research lenses → explicit contradiction ledger → decision-ready brief + HTML report.  
No API key, no external billing — it runs entirely inside the user's Claude Code session.

## Repository layout

```text
skills/storm-council/SKILL.md          # the skill definition (source of truth for the workflow)
skills/storm-council/prompts/          # stage1–stage6 prompt templates
agents/                                # five lens subagents: academic, economist, historian, practitioner, skeptic
scripts/verify.py                      # deterministic quality-gate scorer (pure stdlib, no network)
scripts/render_report.py               # HTML report renderer (pure stdlib, no network)
examples/                              # full example runs (network_flow_rl, university_timetabling)
docs/                                  # methodology, safety-and-limitations, claim-traceability
.claude-plugin/plugin.json             # plugin manifest
```

## The six stages and their artifacts

| Stage | Artifact(s) |
| - | - |
| 1 Decision Frame | `01_decision_frame.md` |
| 2 Perspective Scan | `02_perspective_scan.md`, `02_perspective_scan.json` |
| 3 Evidence | `03_evidence_plan.md`, `03_claims.jsonl`, `03_sources.bib`, `03_source_registry.csv` |
| 4 Contradiction Ledger | `04_contradiction_ledger.md`, `04_contradictions.json` (+ `04_council_deliberation.*` in Council Mode) |
| 5 Synthesis | `05_synthesis.md`, `05_argument_map.mmd`, `05_decision_brief.md` |
| 6 Adversarial Review | `06_adversarial_review.md`, `06_quality_gate.json` |
| Final | `report_data.json` → `storm_council_report.html` |

## ID conventions (enforced by verify.py)

- Sources: `S-001`, `S-002`, …
- Claims: `C-001`, `C-002`, …
- Contradictions: `X-001`, `X-002`, …
- Every `fact`/`inference` claim marked `supported` or `partially_supported` must reference at least one `S-###` source.
- IDs must be consistent across all stage files.

## Running the scripts

```bash
# Score and write the quality gate (after stage 6):
python3 scripts/verify.py <output_dir> --write

# Render the shareable HTML report:
python3 scripts/render_report.py <output_dir>/report_data.json -o <output_dir>/storm_council_report.html
```

Both scripts are pure Python stdlib — no pip installs, no network, no LLM.

## Python runtime

Always use a native **arm64** Python. Verify: `python3 -c "import platform; print(platform.machine())"` must print `arm64`.  
Prefer `/opt/homebrew/bin/python3.12`. Never use `/opt/anaconda3/bin/python3` (Rosetta, silently slow).

## Two interaction modes

- **Hub-and-Spoke** — lenses research independently, assembled centrally. Use for narrow / low-stakes questions.
- **Council Mode** — lenses cross-examine each other's claims in bounded rounds (≤2 rounds, ≤5 items per lens). Auto-select for contested evidence, policy, finance, medicine, safety, security, institutional decisions.

## Hard rules (never violate these)

1. **Never fake retrieval.** If no retrieval tool ran, mark claims `unsupported` and say so. No invented URLs or citations.
2. **Never hand-set quality-gate scores.** Let `verify.py` compute them.
3. **Never set `status.level = PASS`** unless live retrieval/verification actually occurred. Otherwise use `ILLUSTRATIVE` / `UNVERIFIED`.
4. **Never concatenate five independent persona answers** and call it Council Mode. Perspectives must inspect one another.
5. **Never loop Council Mode indefinitely.** Stop when no new high-impact contradiction appears.
6. **Caveat high-stakes output.** Always state the brief supports — and does not replace — domain expertise and human decision-making.

## Git workflow

Push directly to `main`. No feature branches, no pull requests, unless explicitly asked.

## What's gitignored

| Pattern | Why |
|---------|-----|
| `/out/` | Default workflow output directory — runs go here, never committed |
| `__pycache__/`, `*.py[cod]` | Python bytecode |
| `.DS_Store`, `**/.DS_Store` | macOS metadata |
| `.env`, `.env.*` | Secrets — use `.env.example` for templates |
| `*.log` | Runtime logs |

**Preserving an example run:** copy the output folder from `/out/<run>/` into `examples/<name>/` and commit it there — that's the only way it gets into the repo.

## Evidence plan paper rendering (APA-lite)

In `_evidence_plan_html` (`scripts/render_report.py`), `selected/top result` lines are rendered as APA-lite:

```text
Authors (Year). Title. Venue.   [cited by N]
```

- **Authors** — muted small text (`.qauthors`), parsed from `| authors: …` field; omitted if absent
- **(Year).** — inline after authors
- **Title** — linked to `https://www.semanticscholar.org/paper/{paperId}`, opens in new tab
- **Venue** — italic muted text (`.qvenue`), parsed from `| venue: …` field; omitted if absent
- **cited by N** — monospace chip (`.qcite`) on the right; wording is always exactly `cited by N`

The pipe-delimited format in `03_evidence_plan.md` (written by Stage 3) is:

```text
selected/top result: <title> | authors: <Last, F.> | venue: <Journal> | paperId=<id> | year=<YYYY> | citationCount=<N>
```

`authors` and `venue` are optional for backward compatibility; both are required when the API returns them.

## Lens icons (single global source of truth)

The five research-lens icons (academic, economist, historian, practitioner, skeptic)
are defined **once** in `LENS_ICONS` in `scripts/render_report.py` — one canonical icon
per lens, as Lucide line-icon geometry on a `0 0 24 24` viewBox, drawn in the lens accent
via `currentColor`.

- **Never** add a second, divergent lens-icon set. Every place the report shows a lens
  icon must read from `LENS_ICONS`.
- Render through the shared helpers: `_lens_icon_inner(name)` returns the canonical inner
  geometry; `_lens_icon_svg(name, accent)` wraps it for lens-plan cards (`.lplan-ic`);
  `_lens_icon_ca(name)` wraps it for charter headers (`.ca-icon-svg`). Unknown names fall
  back to `LENS_ICON_FALLBACK`.
- To change a lens's icon, edit only its entry in `LENS_ICONS`; both the charter and the
  lens-plan renderings update together.

## Tests

```bash
python3 -m pytest tests/
```

`tests/test_render_report.py` covers the renderer. Add tests alongside any change to `scripts/`.
