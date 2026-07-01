# Compatibility

## Python

The scripts use the Python standard library. `python3 scripts/verify.py`,
`python3 scripts/render_report.py`, `python3 scripts/metadata_adapters.py`, and
`python3 scripts/benchmark.py` ran during the documentation audit.

On Apple Silicon, prefer native arm64 Python. On the audit machine:

- `/opt/homebrew/bin/python3.12` reported `arm64`;
- default `python3` reported Anaconda `x86_64` but had pytest installed;
- the project `.venv/bin/python` reported `arm64` but did not have pytest.

## Tests

Both are valid documented checks depending on environment:

```bash
python3 -m unittest discover -s tests
python3 -m pytest tests/
```

`unittest` requires no extra package. `pytest` requires pytest to be installed.

## MCP Servers

`.mcp.json` configures:

- `semantic-scholar` via `uvx semantic-scholar-fastmcp`;
- `paper-search` via `uvx paper-search-mcp`;
- `fetch` via `uvx mcp-server-fetch`.

During this audit, `semantic-scholar-fastmcp` and `mcp-server-fetch` launched,
but `uvx paper-search-mcp --help` failed with:

```text
Package `paper-search-mcp` does not provide any executables.
```

Documentation should therefore treat MCP retrieval as optional and environment
dependent. Runs must record actual retrieval tools used rather than assume every
configured MCP was available.
