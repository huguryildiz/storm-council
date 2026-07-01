# Storm Council

## One-sentence value proposition

Storm Council is a Claude Code plugin that turns a decision question into a
single-LLM, multi-role deliberation workflow with source-linked claims, visible
contradictions, deterministic artifact checks, and a self-contained HTML report.

## What It Does

Storm Council structures a research run into six stages:

1. Frame the decision, scope, stakeholders, and tripwires.
2. Charter five research lenses: practitioner, academic, skeptic, economist,
   and historian.
3. Record source-grounded claims, sources, evidence locators, and optional
   content-verdict records.
4. Preserve contradictions and, in Council Mode, log bounded cross-examination.
5. Synthesize findings, options, argument-map notes, and a decision brief.
6. Run `scripts/verify.py` to compute the quality gate, then render
   `storm_council_report.html`.

The result is an output bundle that can be inspected as plain files and shared as
one HTML report.

## What It Does Not Do

Storm Council is not a truth engine, guaranteed fact-checker, autonomous
decision-maker, hosted SaaS product, MCP server, or multi-model consensus
system. It runs inside the user's Claude Code session. Its deterministic scripts
check artifact integrity and specific guardrails; they do not prove that a
model-generated recommendation is objectively true.

Use the output as decision support. For consequential legal, medical, financial,
policy, safety, or operational choices, domain experts and accountable humans
still own the decision.

## Core Workflow

```text
User decision question
  -> Claude Code storm-council skill
  -> five functional research lenses
  -> claim/source/evidence artifacts
  -> contradiction ledger and optional council deliberation log
  -> synthesis, argument map, decision brief
  -> deterministic verification and provenance utilities
  -> deterministic HTML renderer
  -> output bundle and optional recheck artifacts
```

The workflow source of truth is
[`skills/storm-council/SKILL.md`](skills/storm-council/SKILL.md). The lens files
under [`agents/`](agents/) are subagent instructions. They do not write files
directly; the orchestrator assembles artifacts.

## Key Trust Features

- Structured disagreement: contradictions are records, not hidden prose.
- Claim/evidence linkage: claims use `C-###`, sources use `S-###`, evidence uses
  `E-###`, and contradictions use `X-###`.
- Contradiction visibility: unresolved conflicts remain in the bundle and gate
  output.
- Verification: `scripts/verify.py` checks IDs, source links, direct-support
  locators, evidence-verdict shape, publication-status flags, abstract-only
  gating, comparative-scope fields, overclaiming heuristics, and recommendation
  support.
- Provenance integrity: `--seal` writes SHA-256 hashes into
  `provenance_manifest.json`; `--check-seal` detects byte changes since the last
  seal.
- Recheck and refresh: `--recheck` manually re-runs publication-identity
  adapters and writes `refresh_diff.json` plus `refresh_report.md`.
- Decision conditions: optional `decision_tripwires.json` records conditions
  that should trigger human review.

Verification means "artifact integrity and guardrails checked." It does not mean
"the recommendation is true."

## Quickstart

Install from the Claude Code plugin marketplace:

```text
/plugin marketplace add huguryildiz/storm-council
/plugin install storm-council@huguryildiz
```

Install from a local clone:

```bash
git clone https://github.com/huguryildiz/storm-council
cd storm-council
bash setup.sh
```

Then in Claude Code:

```text
/plugin marketplace add /absolute/path/to/storm-council
/plugin install storm-council@huguryildiz
```

Invoke the workflow with natural language:

```text
Use Storm Council in council mode to evaluate whether a deep-RL controller should replace rule-based routing in an underwater sensor network.
```

The setup script checks `uv`, MCP server launchability, and Python. On this
machine during the documentation audit, `semantic-scholar-fastmcp` and
`mcp-server-fetch` launched, while `uvx paper-search-mcp --help` failed because
the package did not expose an executable. Treat MCP retrieval as optional and
validate it in your environment before relying on it.

## Example Run

Two committed example bundles are available:

- [`examples/network_flow_rl/`](examples/network_flow_rl/) - 28 claims, 9
  sources, 20 evidence records, 48 evidence verdicts, 8 contradictions,
  `PASS_WITH_CAVEATS`.
- [`examples/ai_jobs_policy/`](examples/ai_jobs_policy/) - 26 claims, 12
  sources, 26 evidence records, 43 evidence verdicts, 8 contradictions,
  `PASS_WITH_CAVEATS`.

Render the network-flow example:

```bash
python3 scripts/verify.py examples/network_flow_rl --write
python3 scripts/render_report.py examples/network_flow_rl/report_data.json -o examples/network_flow_rl/storm_council_report.html
```

Expected output path:

```text
examples/network_flow_rl/storm_council_report.html
```

## Output Bundle Anatomy

Core stage artifacts:

```text
01_decision_frame.md
02_perspective_scan.md
02_perspective_scan.json
03_evidence_plan.md
03_claims.jsonl
03_sources.bib
03_source_registry.csv
03_evidence.jsonl
03_evidence_verdicts.jsonl
04_contradiction_ledger.md
04_contradictions.json
04_council_deliberation.md
04_council_deliberation.jsonl
05_synthesis.md
05_argument_map.mmd
05_decision_brief.md
06_adversarial_review.md
06_quality_gate.json
report_data.json
storm_council_report.html
```

Optional artifacts include `run_manifest.json`, `decision_tripwires.json`,
`decision_criticality.json`, `metadata_verification.jsonl`,
`source_versions.jsonl`, `retrieval_log.jsonl`, `provenance_manifest.json`,
`refresh_diff.json`, and `refresh_report.md`.

See [`docs/output-bundle.md`](docs/output-bundle.md) for the artifact table.

## Verification and Recheck

Run the deterministic verifier:

```bash
python3 scripts/verify.py <output_dir> --write
```

Render the report:

```bash
python3 scripts/render_report.py <output_dir>/report_data.json -o <output_dir>/storm_council_report.html
```

Run publication-identity adapters:

```bash
python3 scripts/metadata_adapters.py <output_dir>
```

Use cache-only mode when network retrieval is not allowed:

```bash
python3 scripts/metadata_adapters.py <output_dir> --no-retrieve
```

Seal and check artifact integrity:

```bash
python3 scripts/verify.py <output_dir> --seal
python3 scripts/verify.py <output_dir> --check-seal
```

Manually recheck a finished bundle:

```bash
python3 scripts/verify.py <output_dir> --recheck --write
python3 scripts/verify.py <output_dir> --recheck --offline
```

`--recheck` is point-in-time only. It does not schedule monitoring. It never
silently changes claim text or contradiction status; it surfaces changes for
human review.

See [`docs/verification-and-provenance.md`](docs/verification-and-provenance.md)
and [`docs/recheck-and-refresh.md`](docs/recheck-and-refresh.md).

## Architecture

Storm Council is mostly prompt/runbook plus deterministic local utilities:

- `skills/storm-council/SKILL.md` - workflow instructions.
- `skills/storm-council/prompts/` - stage prompt templates.
- `skills/storm-council/templates/` - artifact shapes.
- `agents/` - five research lens subagent instructions.
- `scripts/verify.py` - deterministic quality gate, seal, and recheck.
- `scripts/metadata_adapters.py` - opt-in publication identity adapters.
- `scripts/render_report.py` and `scripts/report/` - deterministic HTML
  rendering.
- `tests/` - offline regression tests.

See [`docs/architecture.md`](docs/architecture.md).

## Role Model

The implemented role model is a five-lens model:

| Lens | Function |
| --- | --- |
| Practitioner | Operational constraints, implementation reality, failure modes, adoption friction |
| Academic | Peer-reviewed evidence, benchmarks, methods, reproducibility limits |
| Skeptic | Unsupported claims, weak assumptions, overclaims, missing evidence |
| Economist | Costs, incentives, opportunity cost, distributional effects |
| Historian | Precedent, analogies, repeated failure patterns, institutional context |

There is no implemented Four Horsemen runtime in this repository. See
[`docs/role-model.md`](docs/role-model.md).

## Limitations and Responsible Use

Storm Council can preserve evidence references, structured disagreement,
verification status, provenance, and decision conditions. It cannot guarantee
complete retrieval, semantic entailment, factual truth, source freshness, or
the correctness of a recommendation.

Known release-audit conditions are listed in
[`docs/DOCUMENTATION_ALIGNMENT_REPORT.md`](docs/DOCUMENTATION_ALIGNMENT_REPORT.md).

## Documentation

- [`docs/quickstart.md`](docs/quickstart.md)
- [`docs/architecture.md`](docs/architecture.md)
- [`docs/output-bundle.md`](docs/output-bundle.md)
- [`docs/verification-and-provenance.md`](docs/verification-and-provenance.md)
- [`docs/recheck-and-refresh.md`](docs/recheck-and-refresh.md)
- [`docs/role-model.md`](docs/role-model.md)
- [`docs/limitations.md`](docs/limitations.md)
- [`docs/examples.md`](docs/examples.md)
- [`docs/benchmark.md`](docs/benchmark.md)
- [`docs/CLAIMS_VS_IMPLEMENTATION.md`](docs/CLAIMS_VS_IMPLEMENTATION.md)

Historical audit snapshots remain under `docs/` but are not the current product
contract.

## Development

Run the stdlib test suite:

```bash
python3 -m unittest discover -s tests
```

Run the pytest suite when pytest is installed:

```bash
python3 -m pytest tests/
```

Run the offline benchmark:

```bash
python3 scripts/benchmark.py
python3 scripts/benchmark.py --json
```

This repository prefers native arm64 Python on Apple Silicon. On this audit
machine, `/opt/homebrew/bin/python3.12` is arm64; the default `python3` is
Anaconda `x86_64` but has pytest installed.

## License

Apache-2.0. See [`LICENSE`](LICENSE).
