# Quickstart

## Install

From the Claude Code plugin marketplace:

```text
/plugin marketplace add huguryildiz/storm-council
/plugin install storm-council@huguryildiz
```

From a local clone:

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

## Run

Ask Claude Code to use the skill:

```text
Use Storm Council in council mode to evaluate whether a deep-RL controller should replace rule-based routing in an underwater sensor network.
```

The skill writes artifacts to the output folder chosen by the run. The committed
examples use `examples/network_flow_rl/` and `examples/ai_jobs_policy/`.

## Verify and Render

```bash
python3 scripts/verify.py examples/network_flow_rl --write
python3 scripts/render_report.py examples/network_flow_rl/report_data.json -o examples/network_flow_rl/storm_council_report.html
```

Expected report path:

```text
examples/network_flow_rl/storm_council_report.html
```

## Optional Checks

```bash
python3 scripts/metadata_adapters.py examples/network_flow_rl
python3 scripts/verify.py examples/network_flow_rl --seal
python3 scripts/verify.py examples/network_flow_rl --check-seal
python3 scripts/verify.py examples/network_flow_rl --recheck --offline --write
```

Use temp copies for destructive or exploratory checks if you do not want to
rewrite committed example artifacts.

## Environment

- The verification and rendering scripts use the Python standard library.
- `pytest` is optional and only needed for `python3 -m pytest tests/`.
- `uv` is needed only for optional MCP servers configured in `.mcp.json`.
- `SEMANTIC_SCHOLAR_API_KEY` or `S2_API_KEY` can improve Semantic Scholar rate
  limits if your adapter/tooling supports it; do not commit secrets.

On this audit machine, `/opt/homebrew/bin/python3.12` is native arm64. The
default `python3` is Anaconda `x86_64` but has pytest installed.
