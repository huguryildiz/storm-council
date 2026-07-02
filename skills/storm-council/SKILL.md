---
name: storm-council
description: Contradiction-aware, evidence-grounded multi-agent research workflow. Use when a question needs competing expert perspectives, source-traceable claims, an explicit contradiction ledger, and a decision-ready brief — especially for contested, high-impact, policy, finance, medicine, safety, security, research-design, institutional, or architecture decisions.
---

# Storm Council

Turn one research question into competing expert perspectives, source-grounded
claims, an explicit contradiction ledger, a source-mapped synthesis, an
adversarial review, and a decision-ready brief.

> **Core principle: parallel answers are not the same as collective reasoning.**
> Do not produce five independent persona answers and concatenate them. Make the
> perspectives inspect one another's claims, evidence, assumptions, and
> uncertainties before synthesising.

## 1. When to use this skill

Use Storm Council when the user wants a researched decision, not a quick answer —
when perspectives genuinely differ, trade-offs are real, or the topic is
contested or high-stakes. If the request is a simple factual lookup, do not use
this skill.

## 2. Ask only the necessary framing questions

Before researching, confirm just enough to frame the decision. Ask at most a few
short questions, and only for what you cannot infer:

- What decision will this inform, and who is the audience?
- What is in and out of scope?
- Time horizon and risk tolerance?

If the user already gave these, do not re-ask. Then write **`01_decision_frame.md`**.

### Default perspectives (the research lenses)

Run these five lenses unless the user specifies others. They are configurable
research lenses, **not** fixed personas — each is chartered to seek different
evidence and to name its own blind spots. In `02_perspective_scan.md`, give each
a role charter, priority questions, expected evidence types, likely blind spots,
potential conflicts with other lenses, and escalation triggers.

| Lens | Focus | Likely blind spot |
| --- | --- | --- |
| **practitioner** | Operational constraints, implementation reality, failure modes, adoption friction | Discounting advances not yet productized |
| **academic** | Peer-reviewed evidence, theoretical assumptions, reproducibility, methodological limits | Under-weighting deployment/maintenance reality |
| **skeptic** | Unsupported claims, alternative explanations, weak assumptions, incentive problems | Reflexive dismissal of genuinely novel methods |
| **economist** | Cost, incentives, externalities, opportunity cost, distributional effects | Measuring only what is quantifiable |
| **historian** | Precedent, historical analogies, repeated failure patterns, institutional context | Assuming the past fully constrains a new method |

The whole point is that these lenses **inspect one another** (Council Mode) — not
that they answer in parallel.

Each lens is also shipped as a **subagent** (`storm-council:practitioner`, `…:academic`, `…:skeptic`, `…:economist`, `…:historian`). In Council Mode you may dispatch each as its own subagent so they research and reason in independent contexts before cross-examining one another; then assemble their claims into the shared ledger. If you do not dispatch independent subagents, do not claim independent lens contexts; record the actual dispatch mode in `run_manifest.json` when present.

## The six stages — run in order

This is the runbook. Execute the stages in sequence; each writes its artifact(s)
into the output folder before the next begins.

1. **Decision Frame** → `01_decision_frame.md`
   Frame the decision, scope, exclusions, stakeholders, acceptance criteria, and
   what would change the answer. Surface ambiguity before researching.
2. **Perspective Scan** → `02_perspective_scan.md` + `02_perspective_scan.json`
   Charter each lens (see the table above): priority questions, expected evidence,
   blind spots, conflicts with other lenses, escalation triggers.
3. **Evidence-Grounded Inquiry** → `03_evidence_plan.md`, `03_claims.jsonl`,
   `03_sources.bib`, `03_source_registry.csv`, `03_evidence.jsonl`
   Each lens produces an evidence plan and source-grounded claims (fact / inference
   / forecast / assumption / recommendation kept distinct; sources and exact
   evidence locators by ID). You may dispatch each lens as its subagent so they
   reason in independent contexts.
   Optional Phase-4 content verification writes `03_evidence_verdicts.jsonl`,
   an LLM-assisted entailment/scope verdict artifact. `verify.py` checks verdict
   presence, shape, and declared outcomes; it does not decide entailment itself.
4. **Contradiction Ledger** → `04_contradiction_ledger.md` + `04_contradictions.json`
   Compare claims across lenses and classify each conflict. In **Council Mode**, run
   bounded cross-examination and log it in `04_council_deliberation.md` / `.jsonl`.
5. **Source-Mapped Synthesis** → `05_synthesis.md`, `05_argument_map.mmd`,
   `05_decision_brief.md`
   Integrate without erasing disagreement: strongest findings, confidence-ranked
   claims, evidence gaps, decision options, argument map, one-page brief.
6. **Adversarial Review** → `06_adversarial_review.md` + `06_quality_gate.json`
   Run the independent review (do not let the synthesis grade itself) and emit the
   verdict.

**Then render the report** → `storm_council_report.html` (see "Final deliverable").

The numbered requirements (1–10) in this skill are cross-cutting rules that apply
across all six stages.

### Stage prompt library

Each stage has a ready-to-run prompt template in
[`prompts/`](prompts/README.md). They are the operational instructions for the
stage — substitute the `{{placeholders}}` and run them in order, carrying each
stage's question into a source-traceable, artifact-producing pipeline.

| Stage | Prompt template |
| --- | --- |
| 1 Decision Frame | [`prompts/stage1_decision_frame.md`](prompts/stage1_decision_frame.md) |
| 2 Perspective Scan | [`prompts/stage2_perspective_scan.md`](prompts/stage2_perspective_scan.md) |
| 3 Evidence | [`prompts/stage3_evidence_inquiry.md`](prompts/stage3_evidence_inquiry.md) |
| 4 Contradiction Ledger | [`prompts/stage4_contradiction_ledger.md`](prompts/stage4_contradiction_ledger.md) |
| 5 Synthesis | [`prompts/stage5_synthesis.md`](prompts/stage5_synthesis.md) |
| 6 Adversarial Review | [`prompts/stage6_adversarial_review.md`](prompts/stage6_adversarial_review.md) |

## 3. Default to evidence traceability

Every external factual claim must carry a stable source ID and (where it exists)
a URL. Sources get IDs like `S-001`; claims get IDs like `C-001`; contradictions
get `X-001`; evidence records get `E-001`; deliberation moves get `M-001`; and
optional tripwires get `T-001`. Claims reference sources and each other **only by ID**.

## 4. Separate fact, inference, and recommendation

Label every claim with a `claim_type`: `fact`, `inference`, `forecast`,
`assumption`, or `recommendation`, and an `evidence_status`: `supported`,
`partially_supported`, `unsupported`, or `contested`. Never silently turn weak
evidence into a conclusion. Record negative evidence and *absence* of evidence
explicitly.

## 5. Produce all six artifacts

Create these in the user's chosen output folder:

| Stage | Artifact(s) |
| --- | --- |
| 1 Decision Frame | `01_decision_frame.md` (+ optional `decision_tripwires.json`: flat `T-###` revisit conditions bound to real claims/options) |
| 2 Perspective Scan | `02_perspective_scan.md`, `02_perspective_scan.json` |
| 3 Evidence | `03_evidence_plan.md`, `03_claims.jsonl`, `03_sources.bib`, `03_source_registry.csv`, `03_evidence.jsonl` |
| 3b Content Verification | `03_evidence_verdicts.jsonl` |
| 4 Contradiction Ledger | `04_contradiction_ledger.md`, `04_contradictions.json` (+ `04_council_deliberation.md`/`.jsonl` in Council Mode) (+ optional `resolution_plan` on any non-`resolved` record) |
| 5 Synthesis | `05_synthesis.md`, `05_argument_map.mmd`, `05_decision_brief.md` (+ optional `decision_criticality.json`: ordinal `pivotal/contributing/peripheral` load-bearing ranking) |
| 6 Adversarial Review | `06_adversarial_review.md`, `06_quality_gate.json` |

Use the JSON shapes in [`templates/`](templates/). Keep IDs consistent across
all files.

### Final deliverable: verify, then render one polished report

The single shareable output is **`storm_council_report.html`**. Its scoring is
**computed deterministically** and its format is **rendered deterministically** —
neither is hand-asserted by the model. After stage 6:

1. Write the consolidated run as **`report_data.json`** (bottom line, strongest
   findings, contradictions, decision options with evidence strength, next actions,
   gaps, sources, counts), alongside the structured stage artifacts
   (`03_claims.jsonl`, `03_evidence.jsonl`, optional
   `03_evidence_verdicts.jsonl`, `04_contradictions.json`,
   `03_source_registry.csv`). See
   [the example](../../examples/network_flow_rl/report_data.json).

   For each entry in `strongest_findings`, optionally add perspective attribution:
   ```json
   {
     "text": "...",
     "claims": ["C-001"],
     "supported_by": { "perspectives": ["academic", "skeptic"], "note": "source note" },
     "challenged_by": { "perspectives": ["practitioner"], "note": "challenge note or resolution ref" }
   }
   ```
   `supported_by` lists perspectives that converge on the finding; `challenged_by` lists
   those that contest it, with a note on how/whether it was resolved. Both are optional.

   Optionally add `lens_snapshot` when the HTML report should show a compact five-lens
   radar above the contradiction table. These scores are **posture intensity**, not
   evidence quality or verification scores; derive them from the council synthesis and
   keep the summary honest about what the numbers mean:
   ```json
   {
     "lens_snapshot": {
       "summary": "Skeptic pressure is high; hybrid support remains bounded.",
       "scale_label": "0 low posture intensity · 1 high posture intensity",
       "lenses": [
         {
           "name": "academic",
           "score": 0.82,
           "stance": "hybrid evidence",
           "tone": "support",
           "note": "Surveys support learned components."
         }
       ]
     }
   }
   ```
   The renderer only displays the radar when this field is present; it must not infer
   posture scores from prose.
2. **Verify + score** (pure stdlib — no network, no LLM, no API key):

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/verify.py" <output_dir> --write
   ```

   This checks reference integrity (IDs resolve, supported facts cite sources,
   evidence IDs resolve, contradictions reference real claims), plus deterministic
   publication/content guards: duplicate/malformed DOI, retracted or superseded
   sources, direct-support locator requirements, abstract-only gating,
   comparative-claim scope fields, obvious overclaiming language, and
   LLM-assisted evidence-verdict presence/shape/outcome. It computes the four
   scores and the verdict, writes `06_quality_gate.json`, and patches
   `report_data.json`. **Do not hand-set the scores** — let `verify.py` compute them.
   Optionally, before this step, run the Phase-3 publication metadata adapters:

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/metadata_adapters.py" <output_dir>
   ```

   This writes `metadata_verification.jsonl`, `source_versions.jsonl`, and
   `retrieval_log.jsonl`. The adapters verify publication identity only
   (DOI/version/retraction/correction/supersession/duplicates), not passage to
   claim support. They are opt-in and cache-backed; `--no-retrieve` uses only
   cached responses. Domain adapters additionally resolve `arxiv_id` through
   arXiv and `pmid`/`pmcid` through PubMed/PMC; IEEE Xplore, ACM DL, SSRN,
   NBER, RePEc, and standards sources are logged as not yet wired when no
   native adapter exists. If no adapter run occurred, publication identity
   remains `UNRESOLVED` and must not be described as verified.
3. **Render** the report:

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/render_report.py" <output_dir>/report_data.json -o <output_dir>/storm_council_report.html
   ```

4. Give the user the path to the HTML.
5. **Optional — seal and re-check** (integrity, not authenticity):
   - `verify.py <output_dir> --seal` hashes every artifact into
     `provenance_manifest.json`; `--check-seal` later reports PASS / ALTERED.
     Run sealing as the true last step (composes with `--write`).
   - `verify.py <output_dir> --recheck` re-resolves each source's publication
     identity and emits a deterministic before/after diff (`refresh_diff.json`
     + `refresh_report.md`); `--write` re-seals afterward, `--offline` uses only
     cached responses. This is manual and point-in-time, not monitoring.

**Honesty rule for the status banner:** set `status.level` to reflect whether
sources were actually verified. Use a green / `PASS` state **only** if live
retrieval/verification actually happened; otherwise mark the report
`ILLUSTRATIVE` / `UNVERIFIED`. Never fake a verification badge.

## 6. Escalate to Council Mode when contested or high-impact

Two interaction modes:

- **Hub-and-Spoke** — perspectives research independently; you assemble. Use for
  narrow, low-stakes questions.
- **Council Mode** — perspectives cross-examine selected claims and respond with
  one structured move each (support / challenge / qualification /
  request-for-evidence / reframing). Use when evidence is contested, trade-offs
  are significant, a recommendation is requested, or the topic involves policy,
  finance, medicine, safety, research design, institutional decisions, or system
  architecture.

Council Mode is **bounded**: at most ~2 rounds, ~5 cross-examination items per
perspective, and stop when no new high-impact contradiction appears. Record the
exchanges in `04_council_deliberation.md`/`.jsonl`. Never loop indefinitely.

## 7. Never fake retrieval

Only claim that you browsed, retrieved, or verified something if a tool actually
returned that evidence. If you have no retrieval tool, say so plainly, mark
claims as `unsupported` or `partially_supported`, and do **not** invent sources
or URLs. Fabricated citations are a hard failure.

## 7.1 Use academic MCP servers for retrieval

Academic MCP servers are configured in this project (`.mcp.json`) for optional
retrieval. Prefer them over general web search whenever peer-reviewed evidence is
needed and the server actually launches in the current environment. They are not
guaranteed infrastructure; if a configured MCP is absent or fails to launch, mark
retrieval quality accordingly and do not invent sources. The `semantic-scholar`
server sources `.env` on launch, so set `SEMANTIC_SCHOLAR_API_KEY` there (see
`.env.example`) if you're hitting rate limits.
Always try `semantic-scholar` with `SEMANTIC_SCHOLAR_API_KEY` first for academic
retrieval, citation graph, or exact-paper metadata work. If no Semantic Scholar
API key is configured, fall back to `WebSearch` / `WebFetch` and record the
reduced retrieval quality.

### Tool selection guide

| Goal | Preferred MCP | Tool |
|---|---|---|
| Multi-source topic search (arXiv, OpenAlex, PubMed, CORE…) | `paper-search` | `search_papers` |
| Download / full-text retrieval | `paper-search` | `download_with_fallback` |
| Deep citation graph (who cites / what does it cite) | `semantic-scholar` | `paper_citations`, `paper_references` |
| Paper recommendations from a seed | `semantic-scholar` | `get_paper_recommendations_single` |
| Author profile + paper list | `semantic-scholar` | `author_search` → `author_papers` |
| Exact paper metadata by ID | `semantic-scholar` | `paper_details` |

**`paper-search`** (`uvx paper-search-mcp`) — configured as the preferred unified interface over 20+ sources
(arXiv, OpenAlex, PubMed, Semantic Scholar, CrossRef, bioRxiv, CORE, SSRN,
Zenodo, DOAJ, Europe PMC, and more) when it is available in the current
environment. Use `search_papers` as the default first call only after validating
the server exposes that tool.

**`semantic-scholar`** (`uvx semantic-scholar-fastmcp`) — paper metadata and
richer graph tools: citation chains, author graphs, recommendations. Use when
you need to trace evidence depth beyond a keyword hit and the server is
available.

Usage notes:
- For `semantic-scholar`, pass `fields=title,abstract,year,authors,citationCount,externalIds`.
- `externalIds` returns DOI, arXiv ID, PubMed ID — map `doi` /
  `doi_normalized` to DOI resolver, Crossref, and OpenAlex; `arxiv_id` to
  arXiv; `pmid` to PubMed; and `pmcid` to PMC / PubMed E-utilities. Do not
  treat Semantic Scholar alone as publication truth.
- If no Semantic Scholar API key is configured, or if MCPs are absent or fail to
  launch, fall back to `WebSearch` / `WebFetch` and mark retrieval quality
  accordingly in the status banner (`ILLUSTRATIVE`).

## 8. Require source identifiers for external facts

Any claim about the external world (`fact`/`inference`) presented as supported
must reference at least one `S-###` source, with a URL when available. A
supported claim with no source is invalid — downgrade it or cite it. A claim
marked `direct_support` must also reference at least one `E-###` evidence record
with an exact locator (page/section/table/figure/equation/clause/paragraph hint).
Relevance is not entailment: a real paper or similar title is not proof that the
source supports the specific atomic claim.

## 9. End with a quality gate

Run an independent review (do not let the synthesis grade itself). Check for:
claims without sufficient evidence, citation mismatch, overconfident wording,
missing stakeholder perspectives, source concentration, dependence on low-quality
sources, unresolved contradictions hidden by the synthesis, recommendations not
justified by evidence, missing time sensitivity, hidden value judgements,
abstract-only overclaiming, publication version/retraction warnings, missing
evidence locators, and scope expansion (`some → all`, `simulation → deployment`,
`associated with → causes`, `metric A → superior overall`).
Emit one verdict in `06_quality_gate.json`:

`PASS` · `PASS_WITH_CAVEATS` · `REVISE` · `BLOCKED_PENDING_EVIDENCE`

## 10. Caveat high-stakes output

Do not present output as professional, legal, medical, financial, or policy
advice. State that the brief supports — and does not replace — domain expertise,
source verification, and accountable human decision-making.

---

## Invocation examples

```text
Use Storm Council to investigate whether reinforcement learning is appropriate for university course timetabling.

Use Storm Council in hub-and-spoke mode to compare OR-Tools CP-SAT and MIP for university course timetabling.

Use Storm Council in council mode to evaluate whether a deep-RL controller should replace rule-based routing in an underwater sensor network.

Use Storm Council to prepare a decision brief on [TOPIC].
```
