<!-- markdownlint-disable MD033 MD041 -->

<p align="center">
  <img src="assets/icon.svg" alt="Storm Council" width="132">
</p>

<h1 align="center">Storm Council</h1>

<p align="center">
  <strong>Contradiction-aware research workflow for decision support</strong><br>
  <sub>Frame the decision. Gather evidence. Preserve disagreement. Verify the artifacts. Render the brief.</sub>
</p>

<p align="center">
  <a href="https://claude.ai/code"><img alt="Claude Code plugin" src="https://img.shields.io/badge/Claude_Code-plugin-111827?style=for-the-badge&logo=claude&logoColor=white"></a>
  <a href="skills/storm-council/SKILL.md"><img alt="Five research lenses" src="https://img.shields.io/badge/5_lenses-council_mode-111827?style=for-the-badge&logo=googlescholar&logoColor=white"></a>
  <a href="docs/verification-and-provenance.md"><img alt="Deterministic verifier" src="https://img.shields.io/badge/verifier-stdlib-111827?style=for-the-badge&logo=python&logoColor=white"></a>
  <a href="LICENSE"><img alt="Apache 2.0" src="https://img.shields.io/badge/license-Apache_2.0-111827?style=for-the-badge&logo=apache&logoColor=white"></a>
</p>

<p align="center">
  <a href="docs/quickstart.md">Quickstart</a>
  · <a href="docs/examples.md">Examples</a>
  · <a href="docs/output-bundle.md">Output bundle</a>
  · <a href="docs/CLAIMS_VS_IMPLEMENTATION.md">Claims audit</a>
  · <a href="NOTICE.md">Notice</a>
</p>

---

Storm Council turns one decision question into a source-linked, contradiction-aware
research bundle. It runs inside Claude Code as a plugin skill: five functional
research lenses, structured claim/evidence records, an explicit contradiction
ledger, a deterministic quality gate, and a self-contained HTML report.

It is for decisions where a clean answer would be suspicious: contested evidence,
tradeoffs, architecture choices, policy questions, risk reviews, and research
direction calls.

---

## ✅ What It Does

| Layer | Output |
| --- | --- |
| 🧭 Frame | Scope, stakeholders, exclusions, acceptance criteria |
| 🧠 Lenses | Practitioner, academic, skeptic, economist, historian |
| 🔎 Evidence | `C-###` claims, `S-###` sources, `E-###` evidence records |
| ⚖️ Contradictions | `X-###` conflicts and Council Mode deliberation |
| 🧾 Synthesis | Findings, options, argument map, decision brief |
| 🛡️ Verification | Quality gate, optional seal, optional recheck |
| 📦 Report | `storm_council_report.html` |

Storm Council does not force consensus. Open contradictions remain visible and
are carried into the final brief.

## 🚫 What It Does Not Do

Storm Council is not a truth engine, guaranteed fact-checker, autonomous
decision-maker, hosted SaaS product, MCP server, or multi-model consensus system.
The verifier checks artifact integrity and deterministic guardrails; it does not
prove that a recommendation is objectively true.

## ⚡ Quickstart

```text
/plugin marketplace add huguryildiz/storm-council
/plugin install storm-council@huguryildiz
```

Local clone:

```bash
git clone https://github.com/huguryildiz/storm-council
cd storm-council
bash setup.sh
```

Run in Claude Code:

```text
Use Storm Council in council mode to evaluate whether a deep-RL controller should replace rule-based routing in an underwater sensor network.
```

MCP retrieval is optional and environment-dependent. Record only tools that
actually returned evidence.

## 🧪 Example Runs

| Example | Claims | Sources | Evidence | Contradictions | Gate |
| --- | ---: | ---: | ---: | ---: | --- |
| [`network_flow_rl`](examples/network_flow_rl/) | 28 | 9 | 20 records / 48 verdicts | 8 | `PASS_WITH_CAVEATS` |
| [`ai_jobs_policy`](examples/ai_jobs_policy/) | 26 | 12 | 26 records / 43 verdicts | 8 | `PASS_WITH_CAVEATS` |

Render an example:

```bash
python3 scripts/verify.py examples/network_flow_rl --write
python3 scripts/render_report.py examples/network_flow_rl/report_data.json -o examples/network_flow_rl/storm_council_report.html
```

## 📦 Output Bundle

A run writes plain files: decision frame, lens scan, claims, source registry,
evidence records, evidence verdicts, contradiction ledger, council deliberation,
synthesis, argument map, decision brief, quality gate, `report_data.json`, and
`storm_council_report.html`.

Optional files include `run_manifest.json`, `decision_tripwires.json`,
`metadata_verification.jsonl`, `source_versions.jsonl`, `retrieval_log.jsonl`,
`provenance_manifest.json`, `refresh_diff.json`, and `refresh_report.md`.

See [`docs/output-bundle.md`](docs/output-bundle.md).

## 🛡️ Verification

```bash
python3 scripts/verify.py <output_dir> --write
python3 scripts/render_report.py <output_dir>/report_data.json -o <output_dir>/storm_council_report.html
python3 scripts/metadata_adapters.py <output_dir> --no-retrieve
python3 scripts/verify.py <output_dir> --seal
python3 scripts/verify.py <output_dir> --check-seal
python3 scripts/verify.py <output_dir> --recheck --offline
```

`--seal` is local integrity, not authenticity. `--recheck` is point-in-time
refresh, not monitoring. See
[`docs/verification-and-provenance.md`](docs/verification-and-provenance.md).

## 🏛️ Architecture

| Path | Role |
| --- | --- |
| `skills/storm-council/SKILL.md` | Six-stage workflow |
| `agents/` | Five lens subagents |
| `scripts/verify.py` | Quality gate, seal, recheck |
| `scripts/metadata_adapters.py` | Publication identity adapters |
| `scripts/render_report.py`, `scripts/report/` | HTML renderer |
| `tests/` | Offline regression suite |

See [`docs/architecture.md`](docs/architecture.md).

## 🎭 Role Model

| Lens | Function |
| --- | --- |
| 🛠️ Practitioner | Operations, deployment, failure modes |
| 🎓 Academic | Evidence, benchmarks, methods |
| 🔍 Skeptic | Unsupported claims, overclaims, missing evidence |
| 💸 Economist | Costs, incentives, tradeoffs |
| 🕰️ Historian | Precedent, adoption patterns, institutional memory |

There is no implemented Four Horsemen runtime. See
[`docs/architecture.md`](docs/architecture.md#role-model).

## 📚 Documentation

[`Quickstart`](docs/quickstart.md) ·
[`Examples`](docs/examples.md) ·
[`Output bundle`](docs/output-bundle.md) ·
[`Verification`](docs/verification-and-provenance.md) ·
[`Limitations`](docs/safety-and-limitations.md) ·
[`Claims audit`](docs/CLAIMS_VS_IMPLEMENTATION.md)

## 🧰 Development

```bash
python3 -m unittest discover -s tests
python3 -m pytest tests/
python3 scripts/benchmark.py
```

This repository prefers native arm64 Python on Apple Silicon. On this audit
machine, `/opt/homebrew/bin/python3.12` is arm64; the default `python3` is
Anaconda `x86_64` but has pytest installed.

## 🧬 Lineage and License

Storm Council is independently developed and is inspired in part by
[Stanford OVAL's STORM](https://github.com/stanford-oval/storm). See
[`NOTICE.md`](NOTICE.md).

Apache-2.0. See [`LICENSE`](LICENSE).
