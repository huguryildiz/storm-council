# Output Bundle

A Storm Council run is a directory of plain-text and JSON artifacts. The HTML
report is a rendered view over the same data; it is not the only record.

## Core Artifacts

| File | Stage | Meaning | Required |
| --- | --- | --- | --- |
| `01_decision_frame.md` | 1 | Decision, scope, exclusions, stakeholders, acceptance criteria | Yes |
| `02_perspective_scan.md` | 2 | Human-readable lens charters | Yes |
| `02_perspective_scan.json` | 2 | Structured lens charters | Yes |
| `03_evidence_plan.md` | 3 | Per-lens search plan and selected results | Yes |
| `03_claims.jsonl` | 3 | One claim record per line | Yes |
| `03_sources.bib` | 3 | BibTeX source list | Yes |
| `03_source_registry.csv` | 3 | Source registry keyed by `S-###` | Yes |
| `03_evidence.jsonl` | 3 | Evidence records keyed by `E-###` with locators/excerpts | Recommended; required for direct support |
| `03_support_packets.jsonl` | 3b | Local quoted-passage packets keyed by `P-###` | Required for passage-checked argument support |
| `source_material/` | 3b | Local text files hashed by support packets | Required when support packets exist |
| `03_evidence_verdicts.jsonl` | 3b | LLM-assisted or human entailment/scope verdicts over support packets | Required when direct/strong/comparative support is claimed |
| `04_contradiction_ledger.md` | 4 | Human-readable conflict ledger | Yes |
| `04_contradictions.json` | 4 | Structured contradiction records keyed by `X-###` | Yes |
| `04_council_deliberation.md` | 4 | Council Mode cross-examination log | Council Mode only |
| `04_council_deliberation.jsonl` | 4 | Structured deliberation moves | Council Mode only |
| `05_synthesis.md` | 5 | Source-mapped synthesis | Yes |
| `05_argument_map.mmd` | 5 | Mermaid argument map | Yes |
| `05_decision_brief.md` | 5 | One-page decision brief | Yes |
| `06_adversarial_review.md` | 6 | Human-readable review | Yes |
| `06_quality_gate.json` | 6 | Computed verifier verdict and scores | Written by `verify.py --write` |
| `report_data.json` | Final | Renderer input and report dashboard data | Yes |
| `storm_council_report.html` | Final | Self-contained rendered report | Written by `render_report.py` |

## Optional Artifacts

| File | Meaning | Writer |
| --- | --- | --- |
| `run_manifest.json` | Dispatch mode, lens models, retrieval tools used | Orchestrator/run |
| `decision_tripwires.json` | Manual or auto-recheckable revisit conditions | Orchestrator/run |
| `decision_criticality.json` | Ordinal pivotal/contributing/peripheral claim rankings | Orchestrator/run |
| `metadata_verification.jsonl` | Per-source metadata adapter results | `metadata_adapters.py` |
| `source_versions.jsonl` | Canonical source/version status records | `metadata_adapters.py` |
| `retrieval_log.jsonl` | Cache/network retrieval audit log | `metadata_adapters.py` |
| `provenance_manifest.json` | SHA-256 artifact hashes and copied verdict | `verify.py --seal` |
| `refresh_diff.json` | Recheck before/after source and gate diff | `verify.py --recheck --write` |
| `refresh_report.md` | Human-readable recheck summary | `verify.py --recheck --write` |

## Schema Notes

The repository uses templates under `skills/storm-council/templates/` rather than
a single centralized JSON Schema. The deterministic verifier is the practical
schema enforcer for IDs, enums, source linkage, evidence locators, evidence
verdicts, support packet path/hash/quote integrity, source identity flags,
argument support, and recommendation support.
