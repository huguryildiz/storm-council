# Claude Code Build Prompt — Storm Council

You are building a new open-source repository named **`storm-council`**.

## Product Definition

**Storm Council** is a contradiction-aware, evidence-grounded multi-agent research skill for Claude Code.

It turns one research question into:
1. multiple expert perspectives,
2. source-grounded inquiry,
3. an explicit contradiction ledger,
4. a source-mapped synthesis,
5. an adversarial peer-review pass,
6. a decision-ready research brief.

It is **not** a generic prompt pack and must not be implemented as five personas independently producing answers that are merely concatenated.

The central product principle is:

> Parallel answers are not the same as collective reasoning.

The system should make different perspectives inspect one another’s claims, evidence, assumptions, and uncertainties before synthesis.

---

## Mandatory Source Review

Before designing or implementing anything, inspect these sources:

1. Stanford OVAL STORM repository  
   https://github.com/stanford-oval/storm

2. YouMind article describing a STORM-inspired Claude research method  
   https://youmind.com/tr-TR/landing/x-viral-articles/stanford-storm-claude-research-method

Use them only as conceptual references.

### Attribution and IP Constraints

- Do **not** copy text, prompts, diagrams, headings, or examples verbatim from the YouMind article.
- Do **not** present this project as a STORM fork, official STORM extension, Stanford product, Anthropic product, or Claude Code feature.
- The repository/package name is `storm-council` (package `storm_council`, CLI `storm-council`). Because this name echoes STORM, the non-affiliation disclaimer **must** be especially prominent in `README.md` and `NOTICE.md`: the name is an homage to the STORM research lineage, not a claim of affiliation or endorsement.
- Do include clear attribution to the STORM research foundation in `NOTICE.md` and `README.md`.
- The resulting workflow, prompt templates, role descriptions, schemas, examples, and documentation must be independently written.

Use this wording in attribution:

> Inspired by research-first knowledge-curation systems such as Stanford OVAL’s STORM.  
> Storm Council is independently developed and is not affiliated with, endorsed by, or derived from Stanford University, Stanford OVAL, the STORM project, Anthropic, Claude Code, or YouMind. The name is an homage to that research lineage, not a claim of affiliation.

---

## What to Build

Create a repository-quality Claude Code skill and Python implementation.

The project must work in two modes:

### Mode A — Claude Code Skill

A user should be able to invoke the workflow through a natural instruction such as:

```text
Use Storm Council to investigate whether reinforcement learning is appropriate for university course timetabling.
```

The skill should guide Claude Code through the full staged process and create structured Markdown artifacts in an output folder.

### Mode B — Python CLI

Provide a Python command-line interface:

```bash
storm-council run \
  --topic "Should reinforcement learning be used for university course timetabling?" \
  --output ./out/timetabling-study \
  --profiles practitioner,academic,skeptic,economist,historian
```

The Python CLI does not need to call proprietary LLM APIs directly in the first version. It must establish the orchestration interfaces, schemas, storage, validation, and deterministic artifact pipeline so that an LLM adapter can be added cleanly.

---

## Core Workflow

Implement the following six-stage workflow.

### Stage 1 — Decision Framing

Input:
- topic
- intended decision
- intended audience
- scope
- exclusions
- time horizon
- risk tolerance
- output preference

Output artifact:

```text
01_decision_frame.md
```

Required sections:
- Decision question
- Why this decision matters
- Scope and exclusions
- Key assumptions
- Stakeholders
- What would change the decision
- Known uncertainties
- Research acceptance criteria

The workflow must identify ambiguity before research begins.

---

### Stage 2 — Perspective Scan

Default perspectives:

1. **Practitioner**  
   Focus: operational constraints, implementation reality, failure modes, adoption friction.

2. **Academic**  
   Focus: peer-reviewed evidence, theoretical assumptions, reproducibility, methodological limits.

3. **Skeptic**  
   Focus: unsupported claims, alternative explanations, weak assumptions, incentive problems.

4. **Economist**  
   Focus: cost, incentives, externalities, opportunity cost, distributional effects.

5. **Historian**  
   Focus: precedent, historical analogies, repeated failure patterns, institutional context.

These are configurable research lenses, not fixed “official STORM agents.”

Output artifact:

```text
02_perspective_scan.md
```

For each perspective provide:
- Role charter
- Priority questions
- Expected evidence types
- Likely blind spots
- Potential conflicts with other perspectives
- Escalation triggers

Also output machine-readable metadata:

```text
02_perspective_scan.json
```

---

### Stage 3 — Evidence-Grounded Inquiry

Each perspective must generate an evidence plan and then a structured research record.

Output artifacts:

```text
03_evidence_plan.md
03_claims.jsonl
03_sources.bib
03_source_registry.csv
```

Every claim record must include:

```json
{
  "claim_id": "C-001",
  "perspective": "academic",
  "claim_text": "string",
  "claim_type": "fact|inference|forecast|recommendation|assumption",
  "confidence": 0.0,
  "evidence_status": "supported|partially_supported|unsupported|contested",
  "source_ids": ["S-001"],
  "counterevidence_ids": ["C-011"],
  "limitations": ["string"],
  "created_at": "ISO-8601"
}
```

Every source record must include:

```json
{
  "source_id": "S-001",
  "title": "string",
  "url": "string",
  "publisher": "string",
  "publication_date": "YYYY-MM-DD or null",
  "source_type": "primary|peer_reviewed|government|standards|industry|news|blog|other",
  "accessed_at": "ISO-8601",
  "credibility_notes": "string",
  "relevance_notes": "string"
}
```

Rules:
- Separate facts from inference.
- Do not silently convert weak evidence into conclusions.
- Do not permit citations that are not attached to specific claims.
- Sources must be traceable by stable IDs.
- Track negative evidence and absence of evidence explicitly.

---

### Stage 4 — Contradiction Ledger

This is the differentiating feature of Storm Council.

The system must compare claims across perspectives and generate a structured contradiction ledger, not just a narrative summary.

Output artifacts:

```text
04_contradiction_ledger.md
04_contradictions.json
```

Each contradiction item must include:

```json
{
  "conflict_id": "X-001",
  "topic": "string",
  "claim_a_id": "C-001",
  "claim_b_id": "C-014",
  "relationship": "contradiction|tension|scope_difference|evidence_gap|definition_conflict",
  "why_it_matters": "string",
  "evidence_balance": "supports_a|supports_b|mixed|insufficient",
  "resolution_status": "resolved|partially_resolved|unresolved",
  "next_question": "string",
  "human_review_required": true
}
```

The Markdown ledger must make the following explicit:
- consensus,
- direct disagreements,
- disagreements caused by different definitions,
- disagreements caused by different time horizons,
- disagreements caused by different stakeholder objectives,
- weakly evidenced claims,
- missing evidence,
- unknown unknowns.

Do not force consensus.

---

### Stage 5 — Source-Mapped Synthesis

Output artifacts:

```text
05_synthesis.md
05_argument_map.mmd
05_decision_brief.md
```

The synthesis must include:

1. Executive summary
2. Decision context
3. Strongest evidence-backed findings
4. Main disagreements and why they remain unresolved
5. Confidence-ranked claims
6. Evidence gaps
7. Decision options and trade-offs
8. Recommended next actions
9. Frontier questions
10. Source map

The argument map must use Mermaid syntax and connect:
- central question,
- claims,
- supporting sources,
- counterclaims,
- unresolved tensions,
- recommended actions.

The decision brief should be concise and usable by a technical leader.

---

### Stage 6 — Adversarial Review

Output artifacts:

```text
06_adversarial_review.md
06_quality_gate.json
```

Create an independent reviewer stage that checks:
- claims without sufficient evidence,
- citation mismatch,
- overconfident wording,
- missing stakeholder perspectives,
- source concentration bias,
- excessive dependence on low-quality sources,
- unresolved contradictions hidden by synthesis,
- recommendations not justified by the evidence,
- missing time sensitivity,
- hidden value judgments.

The review must issue one of:

```text
PASS
PASS_WITH_CAVEATS
REVISE
BLOCKED_PENDING_EVIDENCE
```

The quality-gate JSON must contain:

```json
{
  "status": "PASS|PASS_WITH_CAVEATS|REVISE|BLOCKED_PENDING_EVIDENCE",
  "blocking_issues": [],
  "major_issues": [],
  "minor_issues": [],
  "coverage_score": 0,
  "traceability_score": 0,
  "contradiction_handling_score": 0,
  "recommendation_support_score": 0,
  "review_summary": "string"
}
```

---

## Agent Interaction Model

Implement two orchestration modes.

### 1. Hub-and-Spoke Mode

Independent specialist outputs go to a coordinator.

Use this when:
- the problem is low stakes,
- the research question is narrow,
- fast parallel coverage is sufficient.

### 2. Council Mode

Specialists must inspect selected claims from other specialists and explicitly respond to them.

Use this when:
- evidence is contested,
- trade-offs are significant,
- the user asks for a recommendation,
- the topic involves policy, finance, medicine, safety, research design, institutional decisions, or system architecture.

Council mode requirements:
- Each role receives a limited, selected set of other claims.
- Each role can produce:
  - support,
  - challenge,
  - qualification,
  - request for evidence,
  - reframing.
- Preserve all exchanges in:

```text
04_council_deliberation.md
04_council_deliberation.jsonl
```

Avoid an unrestricted “agents talk forever” architecture. Use bounded rounds, structured messages, and termination criteria.

Default:
- maximum 2 deliberation rounds,
- maximum 5 cross-examination items per perspective,
- stop when no new high-impact contradiction appears.

---

## Repository Structure

Create this structure:

```text
storm-council/
├── README.md
├── LICENSE
├── NOTICE.md
├── CONTRIBUTING.md
├── pyproject.toml
├── Makefile
├── .gitignore
├── .pre-commit-config.yaml
├── docs/
│   ├── methodology.md
│   ├── architecture.md
│   ├── claim-traceability.md
│   ├── safety-and-limitations.md
│   └── examples.md
├── skills/
│   └── storm-council/
│       ├── SKILL.md
│       ├── templates/
│       └── examples/
├── src/
│   └── storm_council/
│       ├── __init__.py
│       ├── cli.py
│       ├── config.py
│       ├── models.py
│       ├── orchestrator.py
│       ├── workflow.py
│       ├── persistence.py
│       ├── validators.py
│       ├── adapters/
│       │   ├── __init__.py
│       │   ├── base.py
│       │   └── mock.py
│       ├── agents/
│       │   ├── __init__.py
│       │   ├── base.py
│       │   ├── practitioner.py
│       │   ├── academic.py
│       │   ├── skeptic.py
│       │   ├── economist.py
│       │   ├── historian.py
│       │   └── moderator.py
│       ├── stages/
│       │   ├── __init__.py
│       │   ├── frame.py
│       │   ├── perspectives.py
│       │   ├── evidence.py
│       │   ├── contradictions.py
│       │   ├── synthesis.py
│       │   └── review.py
│       └── renderers/
│           ├── __init__.py
│           ├── markdown.py
│           ├── json.py
│           └── mermaid.py
├── tests/
│   ├── test_models.py
│   ├── test_validators.py
│   ├── test_contradictions.py
│   ├── test_workflow_mock.py
│   └── fixtures/
├── examples/
│   └── university_timetabling/
│       ├── input.yaml
│       └── expected_artifacts/
└── scripts/
    ├── run_example.sh
    └── validate_artifacts.sh
```

---

## Technical Standards

Use:

- Python 3.11+
- `pydantic` for schemas and validation
- `typer` for the CLI
- `pytest` for tests
- `ruff` for linting
- `mypy` where practical
- standard-library-first design outside of clearly justified dependencies
- deterministic mock adapter for tests and examples

Do not make the initial repository dependent on a specific LLM vendor.

Create an adapter interface such as:

```python
class LLMAdapter(Protocol):
    def generate_structured(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        schema: type[BaseModel],
        context: dict[str, object],
    ) -> BaseModel:
        ...
```

Create a `MockAdapter` that deterministically produces valid fixture-grade outputs for the university-timetabling example.

---

## Claude Code Skill Requirements

Create `skills/storm-council/SKILL.md`.

The skill should:

1. Explain when to use the skill.
2. Ask only necessary framing questions.
3. Default to evidence traceability.
4. Require explicit separation of fact, inference, and recommendation.
5. Create all six output artifacts.
6. Escalate to Council Mode when the topic is contested or high-impact.
7. Never claim browsing, retrieval, or verification happened unless tools actually supplied evidence.
8. Require URLs or source identifiers for external factual claims.
9. Require a final quality gate.
10. Avoid presenting output as professional, legal, medical, financial, or policy advice without clear caveats.

The invocation examples should include:

```text
Use Storm Council in hub-and-spoke mode to compare OR-Tools CP-SAT and MIP for university course timetabling.

Use Storm Council in council mode to evaluate whether a deep-RL controller should replace rule-based routing in an underwater sensor network.

Use Storm Council to prepare a decision brief on [TOPIC].
```

---

## README Requirements

Write a polished, concise README with:

- Value proposition
- Architecture diagram in Mermaid
- Six-stage workflow
- Hub-and-spoke vs Council Mode comparison
- Installation
- CLI examples
- Claude Code skill usage
- Output artifact table
- Example folder walkthrough
- Limitations
- Attribution and non-affiliation
- Roadmap

Use this exact one-sentence positioning:

> Storm Council is a contradiction-aware research workflow that turns a question into traceable evidence, competing perspectives, explicit disagreements, and a decision-ready brief.

Include this disclaimer:

> This tool supports research and deliberation. It does not replace domain expertise, source verification, or accountable human decision-making.

---

## Documentation Requirements

### `docs/methodology.md`

Explain:
- research-first workflow,
- perspective diversity,
- evidence/claim separation,
- contradiction ledger logic,
- bounded deliberation,
- source-mapped synthesis,
- adversarial review.

### `docs/safety-and-limitations.md`

Explain:
- model hallucination risk,
- retrieval quality risk,
- source bias,
- false consensus,
- over-automation risk,
- domain-expert review,
- sensitive/high-stakes uses,
- personal data restrictions.

### `docs/claim-traceability.md`

Explain:
- claim IDs,
- source IDs,
- evidence status,
- confidence,
- counterevidence,
- recommendation support.

---

## Testing Requirements

Implement at least:

1. Schema validation tests
2. Invalid source/claim linkage tests
3. Contradiction classification tests
4. Artifact generation test with `MockAdapter`
5. Quality gate behavior tests
6. CLI smoke test
7. Example project regression test

The demo example should concern:

> Whether and when reinforcement learning should complement CP-SAT/MIP in university course timetabling.

This example should demonstrate:
- operational concerns,
- academic evidence limits,
- skepticism about hype,
- cost/infrastructure trade-offs,
- historical lessons from heuristic/metaheuristic systems,
- at least three explicit contradictions,
- an inconclusive but useful final recommendation.

---

## Design Constraints

- Prefer a clean, inspectable architecture over agent-framework hype.
- No autonomous endless loops.
- No hidden scoring.
- No fake citations.
- No invented sources.
- No hard-coded claims masquerading as evidence.
- No “AI replaces researchers” framing.
- Make every major claim traceable.
- Make uncertainty visible.
- Make disagreement first-class.

---

## Deliverable Procedure

1. Inspect the two mandatory sources.
2. Briefly summarize the implementation plan in `docs/architecture.md`.
3. Scaffold the repository.
4. Implement schemas, workflow, mock adapter, validators, and artifact renderers.
5. Implement the CLI.
6. Write the Claude Code skill.
7. Add the university timetabling example.
8. Add tests and run them.
9. Run linting and formatting.
10. Create a concise final report containing:
   - files created,
   - tests run and results,
   - unresolved design decisions,
   - next steps for adding real retrieval and model adapters.

Do not stop at a design document. Produce a working, testable first release.
