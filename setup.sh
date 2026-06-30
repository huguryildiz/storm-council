#!/usr/bin/env bash
set -euo pipefail

echo "Storm Council — setup"
echo "====================="

# ── 1. uv ────────────────────────────────────────────────────────────────────
if command -v uv &>/dev/null; then
    echo "✓ uv $(uv --version | awk '{print $2}')"
else
    echo "→ Installing uv …"
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.cargo/bin:$HOME/.local/bin:$PATH"
    echo "✓ uv installed"
fi

# ── 2. MCP servers ────────────────────────────────────────────────────────────
echo ""
echo "Checking MCP servers (uvx downloads on first use)…"

if uvx paper-search-mcp --help &>/dev/null 2>&1; then
    echo "✓ paper-search-mcp"
else
    echo "✗ paper-search-mcp failed — run: uvx paper-search-mcp --help"
fi

if uvx semantic-scholar-fastmcp --help &>/dev/null 2>&1; then
    echo "✓ semantic-scholar-fastmcp"
else
    echo "✗ semantic-scholar-fastmcp failed — run: uvx semantic-scholar-fastmcp --help"
fi

# ── 3. Python (for verify.py / render_report.py) ─────────────────────────────
echo ""
PYTHON=$(command -v python3 || true)
if [ -z "$PYTHON" ]; then
    echo "✗ python3 not found — install from https://brew.sh or https://python.org"
else
    ARCH=$("$PYTHON" -c "import platform; print(platform.machine())" 2>/dev/null || echo "unknown")
    echo "✓ $PYTHON ($ARCH)"
    if [ "$ARCH" != "arm64" ] && [[ "$(uname -m)" == "arm64" ]]; then
        echo "  ⚠ Running under Rosetta — prefer /opt/homebrew/bin/python3.12"
    fi
fi

echo ""
echo "Done. Open this folder in Claude Code and accept the MCP server prompts."
