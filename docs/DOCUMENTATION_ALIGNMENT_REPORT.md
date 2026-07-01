# Storm Council Documentation Alignment Report

## Executive Summary

- Documentation status: ALIGNED WITH CONDITIONS
- Repository revision: local working tree, `main` checkout on 2026-07-01
- Scope reviewed: README, CLAUDE/AGENTS/CONTRIBUTING instructions, skill and
  prompt docs, agent docs, docs wiki, plugin/MCP manifests, scripts, tests,
  examples, templates, and committed sample bundles.

## Canonical Runtime Model

```text
User input
  -> Claude Code storm-council skill
  -> five functional research lenses
  -> evidence/source/claim artifacts
  -> contradiction ledger and optional Council Mode deliberation log
  -> synthesis, argument map, decision brief
  -> verify.py quality gate and optional metadata/provenance/recheck utilities
  -> render_report.py HTML output
  -> output bundle
```

Current behavior is implemented as a Claude Code plugin skill plus local
standard-library scripts. It is not a hosted service, MCP server, autonomous
monitor, or multi-model consensus system.

## Documentation Inventory

| File | Intended audience | Current claim/purpose | Verified against code? | Required action |
| --- | --- | --- | --- | --- |
| `README.md` | External technical users | Product overview, quickstart, commands, limits | Yes | REWRITE |
| `CLAUDE.md` | Claude Code/developer agents | Repo workflow and hard rules | Yes | UPDATE |
| `AGENTS.md` | Local Codex/agent instructions | Local-only repo notes | Yes | UPDATE |
| `CONTRIBUTING.md` | Contributors | Repo layout and validation commands | Yes | UPDATE |
| `SECURITY.md` | Security reporters | No file present | Yes | MISSING |
| `LICENSE` | Users/contributors | Apache-2.0 terms | Yes | KEEP |
| `.claude-plugin/plugin.json` | Claude plugin manifest | Plugin metadata | Yes | KEEP |
| `.claude-plugin/marketplace.json` | Claude marketplace metadata | Marketplace listing | Yes | KEEP |
| `.mcp.json` | Claude Code MCP config | Optional MCP servers | Partially; paper-search failed | UPDATE DOCS ONLY |
| `skills/storm-council/SKILL.md` | Workflow orchestrator | Six-stage runbook and commands | Yes | UPDATE |
| `skills/storm-council/prompts/*` | Stage execution | Stage-specific instructions | Yes | KEEP |
| `skills/storm-council/templates/*` | Artifact authors | Artifact shapes | Yes | KEEP |
| `skills/storm-council/examples/README.md` | Skill users | Example links | Yes | UPDATE |
| `agents/*.md` | Lens subagents | Five functional role instructions | Yes | UPDATE |
| `agents/README.md` | Agent maintainers | Role model summary | Yes | UPDATE |
| `docs/index.md` | Documentation readers | Wiki landing page | Yes | UPDATE |
| `docs/methodology.md` | Methodology readers | Workflow rationale | Yes | UPDATE |
| `docs/claim-traceability.md` | Artifact readers | ID/evidence/source rules | Yes | UPDATE |
| `docs/examples.md` | Example readers | Worked examples | Yes | UPDATE |
| `docs/benchmark.md` | Evaluators | Offline benchmark | Yes | KEEP |
| `docs/safety-and-limitations.md` | Risk reviewers | Responsible-use warnings | Yes | UPDATE |
| `docs/publication-content-verification-audit.md` | Maintainers | Historical audit | No longer current as product contract | MARK LEGACY |
| `docs/report-improvement-audit.md` | Maintainers | Historical improvement audit | Partially stale | MARK LEGACY |
| `docs/misc/SKILL.md` | Unknown/legacy | Different Storm Research workflow | Not current implementation | MARK LEGACY |
| `docs/architecture.md` | Technical users | Runtime/module boundaries | Yes | MISSING -> CREATED |
| `docs/quickstart.md` | New users | Install/run/verify path | Yes | MISSING -> CREATED |
| `docs/output-bundle.md` | Artifact readers | Bundle anatomy | Yes | MISSING -> CREATED |
| `docs/verification-and-provenance.md` | Auditors | Verifier/seal behavior | Yes | MISSING -> CREATED |
| `docs/recheck-and-refresh.md` | Auditors/users | Manual recheck behavior | Yes | MISSING -> CREATED |
| `docs/role-model.md` | Users/contributors | Five-lens model | Yes | MISSING -> CREATED |
| `docs/limitations.md` | Users/reviewers | Limits and responsible use | Yes | MISSING -> CREATED |
| `docs/compatibility.md` | Users/contributors | Python/MCP compatibility | Yes | MISSING -> CREATED |
| `docs/CLAIMS_VS_IMPLEMENTATION.md` | Release auditors | Public-claim audit | Yes | MISSING -> CREATED |
| `mkdocs.yml` | Docs site builder | Navigation | Yes | UPDATE |
| `scripts/*.py` | Developers/users | CLIs | Yes | KEEP |
| `tests/` | Developers/auditors | Offline regression suite | Yes | KEEP |
| `examples/*` | Users/auditors | Worked bundles | Yes | KEEP |

## Updated Files

- `README.md`
- `CLAUDE.md`
- `AGENTS.md`
- `CONTRIBUTING.md`
- `skills/storm-council/SKILL.md`
- `skills/storm-council/examples/README.md`
- `agents/README.md`
- `agents/academic.md`
- `agents/economist.md`
- `agents/historian.md`
- `agents/practitioner.md`
- `agents/skeptic.md`
- `docs/index.md`
- `docs/methodology.md`
- `docs/claim-traceability.md`
- `docs/examples.md`
- `docs/safety-and-limitations.md`
- `mkdocs.yml`

## Removed or Marked-Legacy Files

- `docs/publication-content-verification-audit.md` marked as a historical audit
  snapshot, not current behavior.
- `docs/report-improvement-audit.md` marked as a historical improvement audit,
  not current behavior.
- `docs/misc/SKILL.md` marked as legacy/non-current and not part of the active
  Storm Council plugin contract.

No useful documentation was removed.

## Claims Softened or Removed

- Removed any implication that verification proves truth.
- Replaced broad "verified" phrasing with artifact integrity, source-backed,
  reviewed, unresolved, or publication-identity wording.
- Removed the implication that all configured MCP servers are currently
  launchable in every environment.
- Replaced any Four Horsemen ambiguity with the implemented five-lens model.
- Clarified that Council Mode logs bounded cross-examination but does not
  automatically mutate claims.
- Clarified that recheck is manual point-in-time refresh, not monitoring.
- Clarified that seal/check-seal prove local integrity only, not authenticity.

## New Documentation Created

- `docs/architecture.md`
- `docs/quickstart.md`
- `docs/output-bundle.md`
- `docs/verification-and-provenance.md`
- `docs/recheck-and-refresh.md`
- `docs/role-model.md`
- `docs/limitations.md`
- `docs/compatibility.md`
- `docs/CLAIMS_VS_IMPLEMENTATION.md`
- `docs/DOCUMENTATION_ALIGNMENT_REPORT.md`

## Commands Verified

| Command | Result |
| --- | --- |
| `python3 scripts/verify.py examples/network_flow_rl --write` | PASS_WITH_CAVEATS; coverage 100, traceability 100, contradiction-handling 25, recommendation-support 100 |
| `python3 scripts/render_report.py examples/network_flow_rl/report_data.json -o examples/network_flow_rl/storm_council_report.html` | Wrote HTML report on temp and example paths |
| `python3 scripts/metadata_adapters.py <output_dir>` | Wrote metadata artifacts for 9 sources on temp copy |
| `python3 scripts/metadata_adapters.py <output_dir> --no-retrieve` | Wrote metadata artifacts for 9 sources on temp copy |
| `python3 scripts/verify.py <output_dir> --seal` | Wrote `provenance_manifest.json`; requires prior gate |
| `python3 scripts/verify.py <output_dir> --check-seal` | PASS on unchanged temp bundle |
| `python3 scripts/verify.py <output_dir> --recheck --offline --write` | 0 of 9 sources rechecked, 9 `not_rechecked`, gate unchanged, resealed |
| `python3 scripts/benchmark.py` | 12 fixtures; false_pass 0/12, false_block 0/3 |
| `python3 scripts/benchmark.py --json` | Emitted JSON benchmark report |
| `python3 scripts/benchmark.py --limit 2` | Ran first 2 fixtures and logged dropped cases |
| `python3 -m unittest discover -s tests` | 191 tests OK under `/opt/homebrew/bin/python3.12` |
| `python3 -m pytest tests/` | 191 passed under default Anaconda `python3`; failed under Homebrew/.venv because pytest is not installed there |
| `.venv/bin/python -m mkdocs build --strict` | Documentation built successfully; informational notes remain for repo-relative example links |
| `python3 -m mkdocs build --strict` | Failed under default Anaconda `python3`: `No module named mkdocs` |
| `python3 scripts/verify.py --help` | Help output matched documented options |
| `python3 scripts/render_report.py --help` | Help output included `--layer {brief,report,appendix,all}` |
| `python3 scripts/metadata_adapters.py --help` | Help output matched documented options |
| `python3 scripts/benchmark.py --help` | Help output matched documented options |
| `claude plugin validate .` | Marketplace manifest validation passed |
| `PATH=/opt/homebrew/bin:$PATH bash setup.sh` | Completed; `semantic-scholar-fastmcp` and `mcp-server-fetch` passed; `paper-search-mcp` failed |
| `uvx semantic-scholar-fastmcp --help` | Launched then stopped server successfully enough to validate executable presence |
| `uvx mcp-server-fetch --help` | Help output printed |
| `uvx paper-search-mcp --help` | Failed: package does not provide executables |
| `python3 -c "import platform; print(platform.machine())"` | Default `python3` returned `x86_64`; Homebrew Python returned `arm64` |

Interactive Claude Code commands such as `/plugin marketplace add ...` and
`/plugin install ...` are documented as Claude Code commands, not shell commands;
they were not executable in the shell audit. The plugin manifest itself was
validated with `claude plugin validate .`.

## Known Limitations Now Disclosed

- Verification checks artifacts and guardrails, not objective truth.
- Evidence verdicts are LLM-assisted/human-review artifacts; deterministic code
  checks their shape and outcomes.
- MCP retrieval is optional and environment dependent.
- The `paper-search-mcp` executable was not available in this audit environment.
- Recheck is manual point-in-time refresh, not monitoring.
- Seals are unsigned local integrity manifests, not authenticity proofs.
- Council Mode does not automatically rewrite claims after challenges.
- High-stakes briefs support, not replace, experts and accountable humans.

## Remaining Documentation Risks

- `SECURITY.md` is still missing; release audit should decide whether to add a
  security policy before public launch.
- The plugin install commands could not be executed inside the shell audit; they
  rely on Claude Code interactive state.
- `paper-search-mcp` is configured but failed launch validation in this
  environment. Public docs now disclose this, but release readiness should either
  fix the package command or remove/replace that MCP config.
- `pytest` availability depends on interpreter; docs now name `unittest` as the
  stdlib check and `pytest` as optional.
- MkDocs is available in `.venv`, not in the default Anaconda `python3`.

## Recommended Next Step

Proceed to release-readiness audit with the named conditions above, especially
the `paper-search-mcp` executable mismatch and missing `SECURITY.md` decision.
