# Evidence Plan

## Retrieval Tooling

The Semantic Scholar MCP was not callable in this Codex session, so the run used live HTTPS retrieval:

- Semantic Scholar Graph API search for the seven mandatory queries and additional topic probes.
- Direct PDF/HTML retrieval for Teal, CFR-RL, B4, SWAN, the JMLR Safe RL survey, OR-Tools, and RFC 2702.
- Crossref metadata lookup for DOI-bearing papers.

All retrieval happened on 2026-06-30. Raw mandatory query logs are stored as `retrieval_semantic_scholar.json` and `retrieval_semantic_scholar_additional.json`; downloaded source text is under `source_cache/`.

## Mandatory Semantic Scholar Queries

- `deep reinforcement learning traffic engineering`: result_count=0
  - no top-3 paper selected because the API returned no relevant results for this query in this run.
- `RL network routing optimization production`: result_count=0
  - no top-3 paper selected because the API returned no relevant results for this query in this run.
- `MPLS traffic engineering reinforcement learning`: result_count=0
  - no top-3 paper selected because the API returned no relevant results for this query in this run.
- `safe reinforcement learning network control`: result_count=10
  - selected/top result: Safe Reinforcement Learning for Longitudinal Control of Autonomous Vehicles: An Augmented Neural Network With Supervision Using Safe Distance | paperId=cccc3b57f0d377eed1a15a36c4ba22929fcf74ea | year=2025 | citationCount=1
  - selected/top result: Hierarchical Safe Reinforcement Learning Control for Leader-Follower Systems With Prescribed Performance | paperId=f926f0b908666e2b18137f99fc4f3a8c3fc4a250 | year=2025 | citationCount=28
  - selected/top result: Data-Model Hybrid-Driven Safe Reinforcement Learning for Adaptive Avoidance Control Against Unsafe Moving Zones | paperId=d81823bf9a79cdfcdc884f5ec6c324b4076e68b2 | year=2025 | citationCount=14
- `linear programming network flow vs reinforcement learning benchmark`: result_count=0
  - no top-3 paper selected because the API returned no relevant results for this query in this run.
- `multi-agent reinforcement learning datacenter networking`: result_count=0
  - no top-3 paper selected because the API returned no relevant results for this query in this run.
- `reinforcement learning sim-to-real network`: result_count=0
  - no top-3 paper selected because the API returned no relevant results for this query in this run.

## Lens Plans

### practitioner

Queries and sources: B4, SWAN, CFR-RL fallback behavior, Teal control-loop context. Disconfirming evidence would be a production case where an RL-primary TE controller runs without deterministic fallback while meeting strict SLA targets.

### academic

Queries and sources: Teal SIGCOMM 2023, CFR-RL JSAC 2020, DRL-for-SD-WAN DOI metadata, required Semantic Scholar queries. Disconfirming evidence would be a reproducible RL-primary benchmark beating strong classical baselines under hard constraints and failure tests.

### skeptic

Queries and sources: required null-result logs, Safe RL survey, SWAN update-safety evidence, B4 fallback. Disconfirming evidence would be full production evidence with outage, rollback, and audit details.

### economist

Queries and sources: Teal runtime benchmark, OR-Tools flow optimization docs, production TE architecture papers. Disconfirming evidence would be local cost data showing classical solver latency is negligible or ML infrastructure cost dominates.

### historian

Queries and sources: RFC 2702, B4, SWAN, Teal architecture. Disconfirming evidence would be a historical network-control transition where a new opaque controller replaced the existing mechanism without staged fallback and still survived production adoption.
