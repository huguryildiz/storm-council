# Architecture

Storm Council is a Claude Code plugin, not a standalone service. The repository
contains prompt/runbook instructions, lens subagent instructions, artifact
templates, deterministic verification utilities, and an HTML renderer.

## Runtime Model

```text
User input
  -> Claude Code plugin skill: skills/storm-council/SKILL.md
  -> role execution: agents/*.md or same-session lens reasoning
  -> evidence/source handling: 03_* artifacts and optional metadata adapters
  -> contradiction handling: 04_* artifacts and optional Council Mode log
  -> verification/provenance: scripts/verify.py and scripts/metadata_adapters.py
  -> report rendering: scripts/render_report.py
  -> output bundle: stage artifacts, report_data.json, HTML
  -> optional recheck/refresh: verify.py --recheck
```

## Implemented Boundaries

| Stage | Source files | Input | Output | Failure behavior | Status |
| --- | --- | --- | --- | --- | --- |
| Orchestration | `skills/storm-council/SKILL.md`, `skills/storm-council/prompts/` | User task, optional sources/context | Stage artifacts in an output directory | Model/orchestrator must mark unavailable evidence rather than inventing it | Implemented as skill instructions |
| Role execution | `agents/*.md`, `agents/README.md` | Lens charter plus task framing | Structured claims, sources, and council moves returned to orchestrator | Agents are instructed not to write files; missing retrieval downgrades claims | Implemented as Claude Code subagents |
| Evidence/source handling | `03_claims.jsonl`, `03_evidence.jsonl`, `03_source_registry.csv`, templates | Retrieved or user-provided source material | Claims, sources, locators, verdict records | Unsupported or abstract-only support remains visible | Implemented through artifacts and verifier checks |
| Contradictions | `04_contradictions.json`, `04_council_deliberation.*` | Claims across lenses | Conflict records and bounded deliberation log | Open conflicts are allowed and reported | Implemented as artifacts; deliberation effects are recorded/displayed, not automatically applied to claims |
| Verification | `scripts/verify.py`, `scripts/report/thresholds.py` | Output directory | `06_quality_gate.json`, patched `report_data.json` | Exits nonzero for invalid path; `--strict` exits 2 on `REVISE`/`BLOCKED_PENDING_EVIDENCE` | Implemented |
| Publication identity | `scripts/metadata_adapters.py` | Output directory source registry | `metadata_verification.jsonl`, `source_versions.jsonl`, `retrieval_log.jsonl` | Offline/unavailable sources become explicit unresolved/not checked states | Implemented, opt-in |
| Provenance seal | `scripts/verify.py --seal`, `--check-seal` | Graded output directory | `provenance_manifest.json` and PASS/ALTERED check output | Refuses to seal without `06_quality_gate.json`; unsigned manifests are not authenticity proof | Implemented |
| Recheck/refresh | `scripts/verify.py --recheck` | Finished output directory | `refresh_diff.json`, `refresh_report.md`, refreshed gate, reseal on `--write` | Offline mode reports `not_rechecked`; no automatic claim edits | Implemented |
| Rendering | `scripts/render_report.py`, `scripts/report/` | `report_data.json` plus nearby artifacts | `storm_council_report.html` or layer-specific HTML | Invalid input JSON/path raises Python/CLI error | Implemented |

## Module Notes

- `scripts/verify.py` is pure standard library. It checks machine-readable
  preconditions and guardrails; it does not perform LLM reasoning.
- `scripts/metadata_adapters.py` uses standard-library network calls and a local
  cache. It verifies publication identity, not passage-to-claim support.
- `scripts/render_report.py` is a compatibility facade over `scripts/report/`.
  Layer rendering supports `brief`, `report`, `appendix`, and `all`.
- `.mcp.json` configures optional MCP servers. Current documentation must not
  assume every configured MCP launches in every environment.
