# Storm Council — Report & System Improvement Audit

> Historical improvement snapshot, not the current product contract. Some line
> counts, module boundaries, and gap descriptions may be stale after later
> renderer, verifier, provenance, and documentation changes. Use
> `docs/CLAIMS_VS_IMPLEMENTATION.md` and
> `docs/DOCUMENTATION_ALIGNMENT_REPORT.md` for current release-audit wording.

*Goal of this audit: move Storm Council from a "multi-agent debate tool" to an
evidence-traceable, contradiction-aware, high-trust decision-support system.*

Scope: the whole pipeline (six stages, data schemas, retrieval, claim/evidence/
contradiction model, `verify.py`, agent orchestration, `render_report.py`) and
the two shipped example reports (`examples/ai_jobs_policy`, `examples/network_flow_rl`).
Every finding below cites a real file/line or a real record ID.

---

## 1. Executive assessment

Storm Council is **stronger than most "AI council" tools and honest about its own
limits** — but three structural gaps keep it in "debate theater" territory rather
than "high-trust decision support."

What is genuinely good and should be protected:

- **The deterministic quality gate is real.** [`verify.py`](../scripts/verify.py)
  computes scores from the artifacts, not from model self-assertion, and enforces
  a wide set of publication/content guards (DOI normalization, retraction/supersession,
  abstract-only gating, comparative-scope fields, an overclaim lexicon, evidence-verdict
  shape). This is the backbone and it works.
- **The claim schema is sophisticated.** A claim record already carries
  `content_verification` (status, `full_text_status`, `entailment_rationale`,
  `evidence_locator`, `adversarial_check`), `support_scope` (metric/baseline/dataset/
  deployment_context/limitations), `atomicity`, and `scope_risk_flags`. Very few
  systems model evidence this carefully.
- **The status banner is the most calibrated layer.** Both examples use
  `status.level = "source_checked"` / `verdict = "PASS_WITH_CAVEATS"` (never a bare
  PASS), name their weaknesses inline ("some publisher full text was limited to
  abstract-level evidence"), and are backed by a real `06_quality_gate.json` that
  `verify.py` requires before allowing a positive banner ([`verify.py:556-561`](../scripts/verify.py#L556-L561)).

The three gaps that block "high trust":

1. **The council debate has no mechanical teeth.** Cross-examination is *logged*
   but never *applied*: the deliberation file is read only for display
   ([`render_report.py:2323-2328`](../scripts/render_report.py#L2323-L2328)), never
   diffed against claims or written back into contradictions. A challenged claim
   keeps its original confidence verbatim (C-016 stays `0.73` after a skeptic
   `challenge`). This is the literal definition of multi-agent theater.
2. **Verification never rejects anything.** Across both runs: **54 claims, 91
   evidence-verdicts → exactly 1 `partial`, 0 `unsupported`, 0 `does_not_entail`**,
   and every run shares a *single boilerplate rationale string*. A gate that always
   passes is confirmation, not adversarial review.
3. **Source quality is laundered.** Abstract-only sources and the run's own search
   logs are formatted identically to peer-reviewed full-text at the claim-support
   layer, so `evidence_status: supported` conflates "I read the paper," "I read the
   abstract," and "I searched and found nothing."

The single highest-leverage change is structural: **split the one 601 KB monolithic
report into the three-layer Executive Brief / Decision Report / Audit Appendix
structure** (assessed in §6 — recommended). It solves the length/repetition problem
*and* creates the natural home for the trust fixes above.

**Overall grade:** solid, honest engine; the "collective reasoning" promise is not
yet mechanically delivered. Fixable without a rewrite.

---

## 2. Current architecture map

```
                 ┌─────────────────── SKILL.md (runbook, 6 stages) ───────────────────┐
 Question ─▶ Stage 1 Decision Frame ─▶ 01_decision_frame.md
            Stage 2 Perspective Scan ─▶ 02_perspective_scan.{md,json}   (lens charters)
            Stage 3 Evidence         ─▶ 03_claims.jsonl  03_evidence.jsonl
                                        03_evidence_verdicts.jsonl  03_source_registry.csv
                                        03_sources.bib  03_evidence_plan.md
            Stage 4 Contradictions   ─▶ 04_contradictions.json  04_contradiction_ledger.md
                                        04_council_deliberation.{md,jsonl}  ← Council Mode
            Stage 5 Synthesis        ─▶ 05_synthesis.md  05_argument_map.mmd  05_decision_brief.md
            Stage 6 Adversarial Rev. ─▶ 06_adversarial_review.md
                 └─────────────────────────────────────────────────────────────────────┘
                                      │
  agents/*.md (5 lens subagents) ─────┘  (optional independent dispatch)
                                      │
                report_data.json  ◀───┤  (curated dashboard layer, ~13 KB)
                                      │
        scripts/verify.py  ──▶ 06_quality_gate.json  (4 deterministic scores + verdict)
                                      │
        scripts/metadata_adapters.py (opt-in: DOI/arXiv/PMID identity, cache-backed)
                                      │
        scripts/render_report.py ─────┴─▶ storm_council_report.html  (~601 KB, ~19 sections)
                 │
                 └─ _fold_in_artifacts(): re-reads all six stage .md files + JSONL
                    and injects them verbatim INTO the same HTML (source of repetition)
```

Key modules and sizes:

| Module | Lines | Role | Health |
|---|---|---|---|
| [`skills/storm-council/SKILL.md`](../skills/storm-council/SKILL.md) | 331 | Runbook / hard rules | Good, but independence is "may" not "must" |
| [`agents/*.md`](../agents/) | 53–103 | 5 lens subagents | 3 of 5 are noun-swapped templates |
| [`scripts/verify.py`](../scripts/verify.py) | 638 | Deterministic scorer | Strong; scores overstate; confidence barely used |
| [`scripts/render_report.py`](../scripts/render_report.py) | 2 396 | HTML renderer | Monolith; logic+CSS coupled; folds raw artifacts |
| [`scripts/metadata_adapters.py`](../scripts/metadata_adapters.py) | 898 | Publication identity | Opt-in; fine |
| `tests/` | 83 tests | verify 18, render 40, others 25 | Good coverage of *rendering*, thin on *semantics* |

The four scores ([`verify.py:491-521`](../scripts/verify.py#L491-L521)):

- **coverage** = distinct perspectives / expected lenses (−10 if <3 claim types)
- **traceability** = evidence-bearing claims whose `S-###` IDs resolve (−25 on link errors) — *resolves ≠ entails*
- **contradiction_handling** = (resolved + partially_resolved) / total; **50 when none logged**
- **recommendation_support** = options-with-strength + actions-with-refs

Both examples score **coverage 100 · traceability 100 · contradiction 50 · recommendation 100**.

---

## 3. Top problems and severity

| # | Severity | Problem | Anchor |
|---|---|---|---|
| P1 | **High (trust-critical)** | Council deliberation is display-only; no move ever changes a claim, confidence, or contradiction status | [`render_report.py:2323-2328`](../scripts/render_report.py#L2323-L2328); C-016 conf unchanged after challenge |
| P2 | **High** | Zero-rejection verification: 91 verdicts → 1 `partial`, 0 fails; one boilerplate rationale per run | `03_evidence_verdicts.jsonl` (both runs) |
| P3 | **High** | Source-quality laundering: abstract-only + self-referential run-logs look identical to full-text peer-reviewed | S-002/007/008/011, S-012, S-009 |
| P4 | **High** | Headline scores overstate: `traceability=100` = IDs resolve, not entail; `contradiction=50` is by design; both gameable | [`verify.py:499-510`](../scripts/verify.py#L499-L510) |
| P5 | Medium | Confidence is uncalibrated pseudo-precision (0.68–0.91, 2 decimals, no rubric, `grep calibrat` = 0 hits); only used as an overclaim heuristic | [`stage3_evidence_inquiry.md:60`](../skills/storm-council/prompts/stage3_evidence_inquiry.md#L60); [`verify.py:479-489`](../scripts/verify.py#L479-L489) |
| P6 | Medium | Lens independence is opt-in ("may dispatch"); 3/5 lens files are 81 % byte-identical templates | [`SKILL.md:54`](../skills/storm-council/SKILL.md#L54); `agents/{economist,historian,practitioner}.md` |
| P7 | Medium (UX) | 601 KB monolithic report; 373 KB (62 %) is inlined Cytoscape.js; C-006 rendered 32× | [`render_report.py:2267`](../scripts/render_report.py#L2267) |
| P8 | Low–Med | Accessibility: `--faint #8a8f99` ≈ 3.0:1 (fails WCAG AA), no table `scope`/`caption`, no skip-link, 7 aria uses total; 7–8-col tables have no scroll wrapper (mobile overflow) | [`render_report.py:26`](../scripts/render_report.py#L26), [`:98-100`](../scripts/render_report.py#L98-L100) |
| P9 | Low–Med | `render_report.py` is a 2 396-line monolith; `build()` ~390 lines; CSS inlined; score thresholds duplicate `verify.py` semantics | [`render_report.py:1825-2215`](../scripts/render_report.py#L1825-L2215) |

---

## 4. What to add

**A1 — A "debate effect" field so cross-examination has teeth (fixes P1).**
Give every deliberation move a recorded consequence and let the renderer/`verify.py`
read it. See §7 schema. Minimum: a move must declare `effect.change_type` ∈
`{none, confidence_delta, status_change, scope_narrowed, withdrawn}` and, when it
resolves a contradiction, list the `X-###`. Then the report can show
"C-016: confidence 0.73 → 0.61 after skeptic challenge (R1)" instead of an inert log.

**A2 — Evidence-linked contradiction resolution (fixes P4).**
A contradiction may only be `resolved`/`partially_resolved` if its new `resolution`
object cites an `E-###` (evidence), an `M-###` (move), or an explicit concession.
`verify.py` should refuse to count self-declared resolutions with no basis — today
0/8 resolutions cite any evidence yet the score still credits them.

**A3 — A source class that separates literature from run-logs (fixes P3).**
Add `source_class ∈ {peer_reviewed, preprint, official, gray, run_log}` to the
source registry. `run_log` sources (S-012, S-009) must not count as evidentiary
support for a `supported` claim, and must render with a distinct "search log, not a
citation" badge. Surface `full_text_status` as a visible badge on every source and
every claim's source chips ("abstract-only" in amber).

**A4 — An anti-rubber-stamp check (fixes P2).**
`verify.py` should flag when ≥N verdicts share an identical `rationale` string (today:
100 %), and when a run produces **zero** `does_not_entail`/`unsupported` outcomes on
a contested/high-stakes topic — surfaced as a "verification did not push back" minor
issue. Optionally require at least one skeptic `challenge` per K claims in Council Mode.

**A5 — A run manifest so independence is auditable (fixes P6).**
Emit `run_manifest.json` recording: dispatch mode (independent subagents vs single
context), model per lens, and which retrieval tools actually returned data. Without
this, "five independent perspectives" is unverifiable and the honesty rules can't be
checked after the fact.

**A6 — Confidence provenance (fixes P5).**
Either (a) demote per-claim confidence to coarse bands tied to evidence
(`low/moderate/high`, derived from evidence tier + verdict + full-text status), or
(b) keep the number but add `confidence_basis` explaining what drove it. Do not ship a
bare `0.86` that reads as calibrated when nothing calibrates it.

**A7 — A one-screen Executive Brief as a standalone artifact (fixes P7, enables §6).**
A ≤1-page HTML/PDF: bottom line, top 3 findings with reliability, the decision options,
the top unresolved contradictions, and the status banner. No registries, no Cytoscape.

---

## 5. What to remove / compress / move to appendix

The report currently renders the curated dashboard **and** re-injects the raw stage
markdown that the dashboard was derived from ([`_fold_in_artifacts`,
`render_report.py:2284-2296`](../scripts/render_report.py#L2284-L2296)). Result: the
same content three times. Concrete duplication in `ai_jobs_policy`:

- `C-001` appears **20×**, `C-006` appears **32×** across one HTML file.
- "Sources" rendered at ≥4 byte-offsets; "Contradiction" header at 6.
- Folded raw markdown adds **372 lines** (ai_jobs) / **320 lines** (network_flow) that
  largely restate structured sections — e.g. `05_decision_brief.md`'s "## Bottom Line"
  is a near-verbatim copy of `report_data.bottom_line`, and its "## Findings That
  Matter" restates `strongest_findings`.

Remove / compress:

1. **Stop folding raw stage markdown into the main report.** The sections
   "Decision brief artifact" (dup of Bottom line + Findings + Options), "Source-mapped
   synthesis notes" (dup of Findings/Options), "Contradiction ledger notes" (dup of the
   contradictions table), and "Adversarial review notes" (dup of Independent review)
   are redundant. Move the raw artifacts to the **Audit Appendix** only.
2. **Move the 373 KB Cytoscape.js out of the default payload.** It is 62 % of every
   report and is hidden in print anyway (static-SVG fallback at
   [`render_report.py:281`](../scripts/render_report.py#L281)). Lazy-load it, link it,
   or ship it only in the Audit Appendix / Decision Report layer.
3. **Collapse the double score display.** Scores appear in the top verdict panel
   *and* again in the "Independent review" section — keep one, cross-link.
4. **Trim Stage 5's 11 sections.** Sections 3 (strongest findings) and 5 (full
   confidence ranking) restate the same claims; §4 restates the contradiction ledger.
   Keep findings + options + gaps in the brief; push the full ranking to the appendix.

Net: a decision-maker should read the findings **once**, not three times.

---

## 6. Proposed new report structure — three layers (RECOMMENDED)

**Verdict: the Executive Brief / Decision Report / Audit Appendix split is the right
structure and is strongly recommended.** The system already contains all three layers
conceptually — they are just fused into one scroll with triple repetition. The curated
`report_data.json` is already ~95 % of Layer 1; the folded artifacts are already Layer 3.
The work is separation, not new authoring.

| Layer | Audience | Contents | Weight target |
|---|---|---|---|
| **1 · Executive Brief** | Decision-maker, ≤2 min | Status banner · Bottom line · Top 3–5 findings (with reliability) · Decision options & trade-offs · Top unresolved contradictions · Recommended next actions · the "how to read" caveat | **≤1 page, no JS, printable/emailable** |
| **2 · Decision Report** | Analyst / reviewer | Everything in L1 + lens charters · full contradictions table with cross-examination detail · argument map (interactive) · evidence gaps · decision-brief prose | Medium |
| **3 · Audit Appendix** | Auditor / skeptic | Claims ledger · evidence registry · entailment verdicts · council deliberation log · source registry + BibTeX · raw stage markdown · full `06_quality_gate.json` · run manifest | Heavy; Cytoscape lives here |

Implementation options (pick one):
- **(a) Three files** — `..._brief.html`, `..._report.html`, `..._appendix.html`,
  cross-linked. Simplest; best for email/PDF; Layer 1 stays tiny.
- **(b) One file, three tabs / progressive disclosure** — Layer 1 visible on load,
  Layers 2–3 behind `<details>`/tabs; Cytoscape lazy-loaded when Layer 2/3 opens.
- Recommendation: **(a)** for the shareable deliverable, with `render_report.py`
  gaining a `--layer {brief,report,appendix,all}` flag. It directly kills P7 and makes
  the trust story legible ("the appendix is where you check our work").

Target flow:

```
report_data.json ──┐
                   ├─▶ render_report.py --layer brief    ─▶ storm_council_brief.html   (≤1 page)
stage artifacts ───┤                    --layer report   ─▶ storm_council_report.html  (analyst)
run_manifest.json ─┘                    --layer appendix ─▶ storm_council_appendix.html(auditor)
```

---

## 7. Schema / data-model changes

Anchored to the real record shapes in `examples/ai_jobs_policy/`.

**7.1 Deliberation move — add an `effect` (currently: `round, lens, target_id, move,
statement, refs`).** Today a move cannot state what it changed.

```jsonc
{
  "move_id": "M-001",                 // NEW: stable ID so contradictions/claims can cite it
  "round": "R1", "lens": "skeptic", "target_id": "C-016", "move": "challenge",
  "statement": "...",
  "effect": {                          // NEW
    "change_type": "confidence_delta", // none|confidence_delta|status_change|scope_narrowed|withdrawn
    "field": "confidence",
    "before": 0.73, "after": 0.61,
    "resolves": []                     // X-### this move (partially) settles, if any
  }
}
```

**7.2 Contradiction — add an evidence-linked `resolution`; drop the duplicate id.**
Records carry **both** `conflict_id` and `contradiction_id` (redundant) and a bare
`resolution_status` with no basis.

```jsonc
{
  "id": "X-001",                       // canonical; remove the conflict_id/contradiction_id pair
  "claim_ids": ["C-006","C-007","C-008","C-025"],
  "resolution_status": "partially_resolved",
  "resolution": {                      // NEW — verify.py refuses "resolved" without a basis
    "basis": "deliberation",           // evidence|deliberation|concession|none
    "evidence_ids": [], "move_ids": ["M-004"],
    "rationale": "..."
  },
  "decisive_missing_evidence": "..."   // keep — this honesty field is good
}
```
Then in [`verify.py:505-510`](../scripts/verify.py#L505-L510): only count a
contradiction as handled when `resolution.basis != "none"` and it cites an `E-###`
or `M-###`. This removes the "mark everything resolved to inflate the score" hole.

**7.3 Source registry — add `source_class`; surface `full_text_status`.**

```jsonc
{ "source_id": "S-012", "source_class": "run_log",   // NEW: run_log|peer_reviewed|preprint|official|gray
  "full_text_status": "abstract_only", ... }
```
`verify.py`: a `supported` claim whose *only* sources are `run_log` → blocking/major
("no external source supports this claim"). The renderer badges `run_log` distinctly
so S-012/S-009 stop sitting in the same list as peer-reviewed papers.

**7.4 Claim — make confidence honest.** Add `confidence_basis` (free text) *or* replace
the float with `confidence_band ∈ {low, moderate, high}` derived from
(evidence tier × verdict × full_text_status). Keep the existing rich
`content_verification`/`support_scope` — they are assets.

**7.5 Evidence verdict — de-boilerplate.** No schema change needed; add a `verify.py`
check that flags identical `rationale` strings across ≥3 verdicts (today: all 43 / all
48 identical) as a "verdicts not individually reasoned" minor issue.

**7.6 New `run_manifest.json`.** `{ dispatch_mode, models_per_lens, retrieval_tools_used,
independent_contexts: bool }` — makes the independence and "never fake retrieval"
rules auditable rather than assumed.

---

## 8. Prioritized implementation roadmap

Ordered by trust-impact ÷ effort. Each step is independently shippable and testable.

**Phase 0 — Quick structural wins (≈1 day, no schema change)**
- Split rendering into `--layer {brief,report,appendix,all}`; make Layer 1 the default
  shareable file (P7, §6). *Verify:* brief HTML < 60 KB, no `<script src=cytoscape>`.
- Lazy-load / relocate Cytoscape.js to the appendix (P7). *Verify:* default payload
  drops ~373 KB.
- Add `overflow-x:auto` table wrapper; fix `--faint` to ≥4.5:1; add a skip-link and
  table `scope`/`<caption>` (P8). *Verify:* extend `tests/test_render_report.py`.
- Stop folding `05_decision_brief.md` / `05_synthesis.md` / `04_contradiction_ledger.md`
  / `06_adversarial_review.md` into non-appendix layers (P7/§5). *Verify:* assert
  `C-006` render count drops from 32 to ≤ a small bound.

**Phase 1 — Give the debate teeth (core trust fix, P1/P4)**
- Add `effect` to moves + `resolution` to contradictions (§7.1–7.2).
- `verify.py`: gate `contradiction_handling` on evidence/move-linked resolution.
- Renderer: show claim-state deltas ("0.73 → 0.61 after R1 challenge").
- *Verify:* a fixture where a move lowers confidence changes the rendered claim and
  the score; a self-declared resolution with `basis:none` no longer counts.

**Phase 2 — Anti-rubber-stamp (P2)**
- `verify.py`: flag identical verdict rationales; flag zero-rejection runs on
  high-stakes topics; optionally require ≥1 skeptic challenge per K claims.
- *Verify:* the two current examples both raise the new minor issue.

**Phase 3 — Source-class integrity (P3)**
- Add `source_class`; block `run_log`-only support; badge `abstract_only`.
- *Verify:* C-008 (abstract-only, standing as counterevidence to full-text IMF claims)
  surfaces a warning; C-026/C-012 (run-log-sourced headline findings) get flagged.

**Phase 4 — Confidence honesty (P5)**
- Ship `confidence_band` or `confidence_basis` (§7.4); update the KPI copy.
- *Verify:* no bare 2-decimal confidence renders without a basis.

**Phase 5 — Lens independence (P6)**
- Differentiate `economist`/`historian`/`practitioner` (unique method + per-lens
  retrieval steering, as `skeptic`/`academic` already have); emit `run_manifest.json`.
- *Verify:* the three files are no longer >80 % identical; manifest records dispatch mode.

**Phase 6 — Renderer maintainability (P9)**
- Split `render_report.py` into `layers/`, `components/`, `styles.css`; centralize the
  score-color thresholds so they don't drift from `verify.py`.
- *Verify:* existing 40 render tests stay green.

---

## 9. Red-team critique (of this system and of this audit)

**Against the system:**
- *"Five lenses" oversells.* In a single-context run, one model writes all five
  voices and then writes all five cross-examination moves against itself. Nothing
  detects this (P6). The convergence risk is real: 3/5 lens files are the same template.
- *The gate can be satisfied without being right.* `traceability=100` means IDs
  resolve, not that the source entails the claim; `contradiction=50` is a fixed "no
  data" reading; every verdict says `entails`. A run can look green while every
  "supported" claim rests on an abstract and a self-citation.
- *Honesty is load-bearing but optional.* The best behaviors (abstract-only caveats,
  `PASS_WITH_CAVEATS`, run-log disclosure) depend on the model choosing to be honest;
  the deterministic layer doesn't yet *force* most of them.

**Against this audit (steelman the status quo):**
- *"Zero rejections" may reflect careful pre-filtering,* not rubber-stamping — a model
  that only writes claims it can support will show a high pass rate. Fair; that's why
  the fix (P2) is a *signal to a reviewer*, not an automatic fail.
- *The three-layer split adds surface area* (three files to keep consistent). Mitigated
  by generating all three from the same `report_data.json` + artifacts in one pass.
- *Making confidence "honest" as bands loses information.* Possibly — hence the
  alternative (keep the number, add a basis) rather than forcing bands.
- *Independence enforcement can't be absolute* in a single-agent harness. True; the
  `run_manifest` makes the *claim* auditable even if it can't guarantee the *fact*.

The audit's own bias: it privileges verifiable mechanism over narrative quality. If the
primary value of Storm Council is helping a human *think*, some "theater" (structured
disagreement to read) is legitimately useful even without mechanical writeback — but it
must not be *scored* as if it were resolution.

---

## 10. Final recommendation

**Adopt the three-layer report (§6) as the flagship change, and use its Audit Appendix
as the forcing function for the trust fixes.** Concretely, in order:

1. **Phase 0 + Phase 1 first.** Split the report and give the debate mechanical teeth.
   These two together convert the biggest weakness (theater + monolith) into the biggest
   strength (a legible brief backed by an auditable appendix) and are low-risk.
2. **Keep the deterministic engine and the rich claim schema** — they are the moat.
   Do not simplify `content_verification`/`support_scope` away.
3. **Reframe the scores as what they are.** Rename/annotate `traceability` →
   "reference integrity" and `contradiction_handling` → "contradiction engagement," and
   never let the brief imply evidentiary resolution the appendix can't show.
4. **Make honesty mechanical, not optional** (source_class, run-log gating,
   verdict de-boilerplate, run manifest).

Do this and Storm Council stops being "five voices and a debate that changes nothing"
and becomes what it is aiming for: a brief a decision-maker can trust in two minutes
*because* an auditor can tear it apart in the appendix. The bones are good; the work is
separation and enforcement, not a rewrite.

*This audit supports — and does not replace — the maintainer's judgement and a live
re-run of the pipeline against these findings.*
