import importlib.util
import json
import re
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "render_report", ROOT / "scripts" / "render_report.py"
)
render_report = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(render_report)


class RenderReportTest(unittest.TestCase):
    def test_report_includes_brand_logo_and_project_links(self):
        html = render_report.build({"title": "A decision", "bottom_line": "Use care."})
        icon_svg = (ROOT / "assets" / "icon.svg").read_text(encoding="utf-8").strip()

        self.assertIn('<div class="brand-logo"', html)
        self.assertIn(icon_svg, html)
        self.assertIn('href="https://oval.cs.stanford.edu/"', html)
        self.assertIn('href="https://storm.genie.stanford.edu/"', html)
        self.assertIn('href="https://github.com/stanford-oval/storm"', html)
        self.assertIn(
            'href="https://storm-project.stanford.edu/research/storm/"',
            html,
        )
        self.assertIn("independently developed", html)
        self.assertNotIn("Anthropic", html)
        self.assertNotIn("Claude Code", html)
        self.assertNotIn("YouMind", html)

    def test_report_omits_lens_radar_without_snapshot_data(self):
        html = render_report.build(
            {
                "title": "A decision",
                "contradictions": [
                    {
                        "id": "X-001",
                        "kind": "tension",
                        "stake": "speed versus reliability",
                        "status": "unresolved",
                    }
                ],
            }
        )

        self.assertNotIn('class="lens-radar"', html)
        self.assertNotIn("Lens posture snapshot", html)

    def test_report_renders_lens_radar_before_disagreement_table(self):
        html = render_report.build(
            {
                "title": "A decision",
                "lens_snapshot": {
                    "summary": "Skeptic pressure is high; hybrid support remains bounded.",
                    "scale_label": "0 low emphasis · 1 high emphasis",
                    "lenses": [
                        {
                            "name": "academic",
                            "score": 0.82,
                            "stance": "hybrid evidence",
                            "tone": "support",
                            "note": "Surveys support learned components.",
                        },
                        {
                            "name": "skeptic",
                            "score": 0.91,
                            "stance": "production caution",
                            "tone": "challenge",
                            "note": "Simulator transfer remains unresolved.",
                        },
                        {
                            "name": "economist",
                            "score": 0.63,
                            "stance": "ROI conditional",
                            "tone": "mixed",
                            "note": "Value depends on workload frequency.",
                        },
                        {
                            "name": "historian",
                            "score": 0.74,
                            "stance": "hybrid precedent",
                            "tone": "caution",
                            "note": "Advisory deployment comes first.",
                        },
                        {
                            "name": "practitioner",
                            "score": 0.78,
                            "stance": "bounded pilot",
                            "tone": "support",
                            "note": "Shadow mode is operationally tractable.",
                        },
                    ],
                },
                "contradictions": [
                    {
                        "id": "X-001",
                        "kind": "tension",
                        "stake": "speed versus reliability",
                        "status": "unresolved",
                    }
                ],
            }
        )

        self.assertIn('class="lens-radar"', html)
        self.assertIn("Lens posture snapshot", html)
        self.assertIn("Skeptic pressure is high; hybrid support remains bounded.", html)
        self.assertIn("0 low emphasis · 1 high emphasis", html)
        self.assertIn("Academic", html)
        self.assertIn("production caution", html)
        self.assertIn("This is a council posture map, not a quality score.", html)
        self.assertLess(html.index('class="lens-radar"'), html.index("<table>"))

    def test_claim_refs_render_as_clickable_chips(self):
        html = render_report.build(
            {
                "title": "A decision",
                "strongest_findings": [
                    {
                        "text": "The baseline should remain explicit.",
                        "claims": ["C-001"],
                    }
                ],
                "next_actions": [
                    {
                        "text": "Re-check the benchmark before shipping.",
                        "refs": ["C-001"],
                    }
                ],
            }
        )

        self.assertIn(
            '<a id="ref-C-001" class="cid clink" href="#ref-C-001">C-001</a>',
            html,
        )
        self.assertIn(
            '<a class="cid clink" href="#ref-C-001">C-001</a>',
            html,
        )
        self.assertNotIn('<span class="cid">C-001</span>', html)

    def test_strongest_findings_are_ranked_by_score_descending(self):
        html = render_report.build(
            {
                "title": "A decision",
                "strongest_findings": [
                    {"text": "Eight-point finding.", "score": 8, "claims": ["C-001"]},
                    {"text": "Nine-point finding.", "score": 9, "claims": ["C-002"]},
                    {"text": "Also eight-point finding.", "score": 8, "claims": ["C-003"]},
                    {"text": "Unscored finding.", "claims": ["C-004"]},
                ],
            }
        )

        self.assertLess(html.index("Nine-point finding."), html.index("Eight-point finding."))
        self.assertLess(html.index("Eight-point finding."), html.index("Also eight-point finding."))
        self.assertLess(html.index("Also eight-point finding."), html.index("Unscored finding."))
        self.assertIn('<span class="fnum">1</span>', html)

    def test_inline_claim_ids_render_as_clickable_chips(self):
        html = render_report.build(
            {
                "title": "A decision",
                "bottom_line": "Validate C-123 before relying on the result.",
            }
        )

        self.assertIn(
            'Validate <a id="ref-C-123" class="cid clink" href="#ref-C-123">C-123</a> before relying',
            html,
        )

    def test_lens_charters_section_renders(self):
        html = render_report.build(
            {
                "title": "A decision",
                "lens_charters": [
                    {
                        "name": "skeptic",
                        "role_charter": "Stress-test claims about safety and generalization.",
                        "priority_questions": ["Are hard constraints guaranteed?"],
                        "expected_evidence_types": ["Negative results", "Limitations sections"],
                        "likely_blind_spots": ["Reflexive dismissal of useful designs."],
                        "potential_conflicts": ["Challenges practitioner optimism."],
                        "escalation_triggers": ["Any claim lacking a fallback."],
                    }
                ],
            }
        )

        self.assertIn("The five council lenses", html)
        self.assertIn('class="charter charter--skeptic"', html)
        self.assertIn("Stress-test claims about safety", html)
        self.assertIn("Priority questions", html)
        self.assertIn("Are hard constraints guaranteed?", html)
        self.assertIn("Likely blind spots", html)
        self.assertIn("Escalation triggers", html)

    def test_lens_charters_omitted_when_absent(self):
        html = render_report.build({"title": "A decision"})
        self.assertNotIn("The five council lenses", html)
        self.assertNotIn('class="charter charter--', html)

    def test_claims_ledger_renders_and_owns_anchor(self):
        html = render_report.build(
            {
                "title": "A decision",
                "bottom_line": "The mature baseline C-001 still holds.",
                "claims": [
                    {
                        "claim_id": "C-001",
                        "perspective": "practitioner",
                        "claim_type": "fact",
                        "evidence_status": "supported",
                        "claim_text": "Classical solvers are mature.",
                        "source_ids": ["S-001"],
                        "counterevidence_ids": ["C-031"],
                        "limitations": ["Library support is not suitability."],
                    },
                    {
                        "claim_id": "C-022",
                        "perspective": "skeptic",
                        "claim_type": "assumption",
                        "evidence_status": "unsupported",
                        "claim_text": "Reward misspecification could harm tail latency.",
                        "source_ids": [],
                    },
                ],
            }
        )

        self.assertIn("Claims &amp; evidence ledger", html)
        self.assertIn('class="claims-table"', html)
        # The ledger row owns the single C-001 anchor target...
        self.assertEqual(html.count('id="ref-C-001"'), 1)
        self.assertIn('<tr id="ref-C-001">', html)
        # ...and the inline mention in the bottom line links to it without minting
        # a duplicate id.
        self.assertIn('<a class="cid clink" href="#ref-C-001">C-001</a>', html)
        # Evidence status is colour-coded like the other tags.
        self.assertIn('<span class="tag done">supported</span>', html)
        self.assertIn('<span class="tag open">unsupported</span>', html)
        self.assertIn("Classical solvers are mature.", html)
        self.assertIn("Library support is not suitability.", html)

    def test_claims_ledger_renders_confidence_and_created_timestamp(self):
        html = render_report.build(
            {
                "title": "A decision",
                "claims": [
                    {
                        "claim_id": "C-001",
                        "perspective": "practitioner",
                        "claim_type": "fact",
                        "evidence_status": "supported",
                        "claim_text": "Classical solvers are mature.",
                        "confidence": 0.88,
                        "created_at": "2026-06-30T00:01:00+03:00",
                    }
                ],
            }
        )

        self.assertIn("claim-chip", html)
        self.assertIn("0.88", html)
        self.assertIn("2026-06-30", html)

    def test_claims_ledger_renders_structured_details(self):
        html = render_report.build(
            {
                "title": "A decision",
                "claims": [
                    {
                        "claim_id": "C-001",
                        "perspective": "academic",
                        "claim_type": "fact",
                        "claim_strength": "comparative",
                        "evidence_status": "supported",
                        "claim_text": "Benchmark gains are scoped.",
                        "evidence_ids": ["E-001"],
                        "support_scope": "Trace replay only.",
                        "scope_risk_flags": ["simulation_to_production"],
                        "atomicity": {"is_atomic": True},
                        "content_verification": {
                            "status": "direct_support",
                            "full_text_status": "full_text",
                            "entailment_rationale": "The section states the scoped result.",
                            "evidence_locator": {"section": "Evaluation"},
                            "adversarial_check": "passed",
                        },
                    }
                ],
            }
        )

        self.assertIn("Claim details", html)
        self.assertIn("comparative", html)
        self.assertIn("E-001", html)
        self.assertIn("Trace replay only.", html)
        self.assertIn("simulation_to_production", html)
        self.assertIn("direct_support", html)
        self.assertIn("section Evaluation", html)

    def test_evidence_registry_renders_record_details_and_judged_claim(self):
        html = render_report.build(
            {
                "title": "A decision",
                "evidence": [
                    {
                        "evidence_id": "E-001",
                        "source_id": "S-001",
                        "locator": {"section": "Methods"},
                        "evidence_excerpt": "The method uses a solver.",
                        "extraction_method": "full_text",
                        "extracted_by": "academic",
                        "supports_candidate_claims": ["C-001"],
                        "notes": "Used for content verification.",
                    }
                ],
                "evidence_verdicts": [
                    {
                        "evidence_id": "E-001",
                        "claim_id": "C-001",
                        "judged_claim": "The method uses a solver.",
                        "verdict": "entails",
                        "scope_preserved": "yes",
                        "rationale": "Directly stated.",
                    }
                ],
            }
        )

        self.assertIn("Evidence details", html)
        self.assertIn("academic", html)
        self.assertIn("Used for content verification.", html)
        self.assertIn("Judged: The method uses a solver.", html)

    def test_source_registry_metadata_is_merged_and_rendered(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            (base / "03_source_registry.csv").write_text(
                "source_id,title,authors,year,venue,publisher,source_type,url,doi,arxiv_id,"
                "publication_status,full_text_status,credibility_notes,relevance_notes\n"
                "S-001,Paper,A. Author,2025,SIGCOMM,ACM,peer_reviewed,https://example.test,"
                "10.1000/test,2501.00001,active,full_text,Strong venue,Direct support\n",
                encoding="utf-8",
            )
            data = {"title": "A decision", "sources": [{"id": "S-001", "title": "Paper"}]}
            render_report._enrich_source_urls(data, base)

        html = render_report.build(data)
        self.assertIn("A. Author", html)
        self.assertIn("SIGCOMM", html)
        self.assertIn("10.1000/test", html)
        self.assertIn("2501.00001", html)
        self.assertIn("active", html)
        self.assertIn("full_text", html)

    def test_abstract_only_badge_renders(self):
        # Phase 3: source_class + abstract-only render as badges in the source list.
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            (base / "03_source_registry.csv").write_text(
                "source_id,title,authors,year,venue,publisher,source_type,url,doi,arxiv_id,"
                "publication_status,full_text_status,source_class,credibility_notes,relevance_notes\n"
                "S-001,Robot Tax,A. Author,2022,RESTUD,OUP,peer_reviewed,https://example.test,"
                "10.1000/test,,active,abstract_only,peer_reviewed,Bot-challenged,Formal model\n"
                "S-002,Run log,Storm Council,2026,Run evidence,Local,primary,,,,active,full_text,"
                "run_log,Run-local audit,Retrieval log\n",
                encoding="utf-8",
            )
            data = {"title": "A decision",
                    "sources": [{"id": "S-001", "title": "Robot Tax"},
                                {"id": "S-002", "title": "Run log"}]}
            render_report._enrich_source_urls(data, base)

        html = render_report.build(data)
        self.assertIn("abstract-only", html)
        self.assertIn("peer-reviewed", html)
        self.assertIn("run log", html)

    def test_source_without_class_renders_no_class_badge(self):
        # Back-compat: a source with no source_class shows no provenance badge.
        html = render_report.build(
            {"title": "A decision", "sources": [{"id": "S-001", "title": "Paper"}]})
        self.assertNotIn("gray literature", html)
        self.assertNotIn("abstract-only", html)

    def test_argument_map_renders_inline_svg_with_links(self):
        mmd = (
            "flowchart TD\n"
            '  Q["Should we adopt X?"]\n'
            '  Q --> A["Use the classical baseline<br/>C-001 C-012"]\n'
            '  A -.->|counters| Q\n'
        )
        html = render_report.build({"title": "A decision", "argument_map": mmd})

        self.assertIn("Argument map", html)
        self.assertIn('<svg class="argmap"', html)
        self.assertNotIn("mermaid", html.lower())
        self.assertIn("Use the classical", html)
        # C-### references inside node labels become clickable anchors.
        self.assertIn('<a href="#ref-C-001"><text class="am-ref"', html)
        # The dotted counter edge renders as a dashed path.
        self.assertIn("am-edge am-dotted", html)

    def test_argument_map_parses_stadium_and_hex_nodes(self):
        nodes, solid, dotted = render_report._parse_mmd(
            "graph TD\n"
            '  C020["C-020 (skeptic): vendor claims"]\n'
            '  S010(["S-010: blog post"])\n'
            '  C020 --> S010\n'
            '  X001{{"X-001 tension: optimism vs skepticism"}}\n'
            '  X001 --> C020\n'
            '  C020 -.->|counters| C004\n'
        )
        self.assertIn("C020", nodes)
        self.assertIn("S010", nodes)
        self.assertIn("X001", nodes)
        self.assertIn(("C020", "S010"), solid)
        self.assertIn(("X001", "C020"), solid)
        self.assertIn(("C020", "C004"), dotted)

    def test_argument_map_degrades_on_unparseable_input(self):
        self.assertEqual(render_report._argument_map_svg("not a graph at all"), "")
        self.assertEqual(render_report._argument_map_svg(""), "")
        # A garbage argument_map must never crash the whole report.
        html = render_report.build({"title": "A decision", "argument_map": "%% comment\n???"})
        self.assertNotIn('<svg class="argmap"', html)

    def test_argument_map_cyto_builds_classified_elements(self):
        mmd = (
            "flowchart TD\n"
            '  Q["Should we adopt X?"]\n'
            '  Q --> A["Option A: status quo"]\n'
            '  Q --> B["Option B: hybrid"]\n'
            '  C002["C-002 benchmark gains"] --> S001["S-001 Teal"]\n'
            '  C002 --> X001["X-001 benchmark vs production"]\n'
            '  X001 --> B\n'
            '  B --> N1["Shadow-mode pilot"]\n'
            '  C002 -.->|counters| A\n'
        )
        data = {
            "sources": [{"id": "S-001", "title": "Teal: WAN TE", "note": "WAN traffic engineering."}],
            "contradictions": [{"id": "X-001", "kind": "scope_difference",
                                "stake": "Benchmark vs production", "status": "partially_resolved"}],
        }
        g = render_report._argument_map_cyto(mmd, data)
        node_ids = {n["data"]["id"] for n in g["nodes"]}
        self.assertEqual(node_ids, {"Q", "A", "B", "C002", "S001", "X001", "N1"})
        self.assertEqual(len(g["edges"]), 7)  # 6 solid + 1 dotted

        by_id = {n["data"]["id"]: n for n in g["nodes"]}
        self.assertIn("am-q", by_id["Q"]["classes"])
        self.assertIn("am-src", by_id["S001"]["classes"])
        self.assertIn("am-x", by_id["X001"]["classes"])
        self.assertIn("am-claim", by_id["C002"]["classes"])
        self.assertIn("am-opt", by_id["A"]["classes"])
        self.assertIn("am-act", by_id["N1"]["classes"])

        dotted = [edge for edge in g["edges"] if edge.get("classes") == "dotted"]
        self.assertEqual(len(dotted), 1)
        self.assertEqual(dotted[0]["data"]["source"], "C002")
        self.assertEqual(dotted[0]["data"]["target"], "A")

        # Tooltip note enriched from report_data.json, falling back to the label.
        self.assertIn("Teal", by_id["S001"]["data"]["note"])
        self.assertIn("Benchmark vs production", by_id["X001"]["data"]["note"])
        self.assertEqual(by_id["N1"]["data"]["label"], "Shadow-mode pilot")

    def test_argument_map_cyto_empty_on_no_nodes(self):
        g = render_report._argument_map_cyto("not a graph", {})
        self.assertEqual(g, {"nodes": [], "edges": []})

    def test_cytoscape_js_reads_vendored_library(self):
        lib = render_report._cytoscape_js()
        self.assertIn("cytoscape", lib)
        self.assertGreater(len(lib), 100000)

    def test_interactive_map_has_canvas_filters_and_static_fallback(self):
        mmd = (
            "flowchart TD\n"
            '  Q["Q?"]\n'
            '  Q --> A["Option A"]\n'
            '  C002["C-002 x"] --> S001["S-001 y"]\n'
            '  C002 --> X001["X-001 z"]\n'
        )
        html = render_report._argument_map_interactive_html(mmd, {})
        self.assertIn('class="am-cy"', html)              # interactive canvas
        self.assertIn('type="application/json"', html)    # embedded elements
        self.assertIn("cytoscape(", html)                 # init call
        self.assertIn("am-filter", html)                  # filter UI
        self.assertIn('class="am-static"', html)          # fallback wrapper
        self.assertIn('<svg class="argmap"', html)        # static SVG kept

    def test_interactive_map_falls_back_to_static_without_library(self):
        mmd = 'flowchart TD\n  Q["Q?"]\n  Q --> A["Option A"]\n'
        orig = render_report._cytoscape_js
        render_report._cytoscape_js = lambda: ""
        try:
            html = render_report._argument_map_interactive_html(mmd, {})
        finally:
            render_report._cytoscape_js = orig
        self.assertIn('<svg class="argmap"', html)        # static SVG still present
        self.assertNotIn("cytoscape(", html)              # no init when lib absent
        self.assertNotIn('class="am-cy"', html)           # no interactive canvas

    def test_interactive_map_empty_on_no_nodes(self):
        self.assertEqual(render_report._argument_map_interactive_html("garbage", {}), "")

    def test_interactive_map_has_flow_and_network_layout_toggle(self):
        mmd = (
            "flowchart TD\n"
            '  Q["Q?"]\n'
            '  Q --> A["Option A"]\n'
            '  C002["C-002 x"] --> S001["S-001 y"]\n'
        )
        html = render_report._argument_map_interactive_html(mmd, {})
        self.assertIn('data-layout="flow"', html)
        self.assertIn('data-layout="network"', html)
        self.assertIn("breadthfirst", html)   # flow layout config in the init
        self.assertIn("name: 'cose'", html)    # network (force-directed) layout config

    def test_council_deliberation_renders_move_log(self):
        html = render_report.build(
            {
                "title": "A decision",
                "deliberation": [
                    {
                        "round": 1,
                        "perspective": "academic",
                        "move_type": "challenge",
                        "target_claim_id": "C-004",
                        "conflict_id": "X-001",
                        "text": "Do not generalize from one task to all tasks.",
                    },
                    {
                        "round": 2,
                        "perspective": "historian",
                        "move_type": "support",
                        "target_claim_id": "C-043",
                        "text": "Start advisory, then expand.",
                    },
                ],
            }
        )

        self.assertIn("Council deliberation", html)
        self.assertIn("Round 1", html)
        self.assertIn("Round 2", html)
        self.assertIn('class="move"', html)
        self.assertIn('<span class="tag open">challenge</span>', html)
        self.assertIn('<span class="tag done">support</span>', html)
        self.assertIn("Move metadata", html)
        self.assertIn("Do not generalize", html)

    def test_council_deliberation_keeps_raw_move_value(self):
        html = render_report.build(
            {
                "title": "A decision",
                "deliberation": [
                    {
                        "round": "round_2",
                        "lens": "academic",
                        "move": "request_for_evidence",
                        "target_id": "X-008",
                        "statement": "Find production evidence.",
                        "created_at": "2026-06-30T16:36:32+00:00",
                    }
                ],
            }
        )

        self.assertIn("request evidence", html)
        self.assertIn("request_for_evidence", html)
        self.assertIn("round_2", html)
        self.assertIn("2026-06-30T16:36:32+00:00", html)

    def test_council_deliberation_omitted_when_absent(self):
        html = render_report.build({"title": "A decision"})
        self.assertNotIn("Council deliberation", html)

    def test_contradiction_detail_expands_positions(self):
        html = render_report.build(
            {
                "title": "A decision",
                "contradictions": [
                    {"id": "X-001", "kind": "tension", "stake": "speed vs safety", "status": "unresolved"}
                ],
                "contradiction_detail": {
                    "X-001": {
                        "conflict_id": "X-001",
                        "why_it_matters": "Replacing solvers is riskier than augmenting them.",
                        "claim_a_id": "C-012",
                        "claim_b_id": "C-004",
                        "evidence_balance": "supports_a",
                        "next_question": "Specify the target workload.",
                    }
                },
                "claims": [
                    {"claim_id": "C-012", "perspective": "academic", "claim_text": "Classical is the baseline."},
                    {"claim_id": "C-004", "perspective": "practitioner", "claim_text": "RL fits dynamic TE."},
                ],
            }
        )

        self.assertIn('<details class="cx-detail">', html)
        self.assertIn("Replacing solvers is riskier", html)
        self.assertIn("Classical is the baseline.", html)
        self.assertIn("RL fits dynamic TE.", html)
        self.assertIn("Specify the target workload.", html)

    def test_contradiction_detail_renders_review_metadata(self):
        html = render_report.build(
            {
                "title": "A decision",
                "contradictions": [
                    {"id": "X-001", "kind": "tension", "stake": "speed vs safety", "status": "partly"}
                ],
                "contradiction_detail": {
                    "X-001": {
                        "conflict_id": "X-001",
                        "topic": "Replacement versus augmentation",
                        "relationship": "scope_difference",
                        "resolution_status": "partially_resolved",
                        "human_review_required": True,
                    }
                },
            }
        )

        self.assertIn("Topic: Replacement versus augmentation", html)
        self.assertIn("Relationship: scope_difference", html)
        self.assertIn("Resolution: partially_resolved", html)
        self.assertIn("Human review required: yes", html)

    def test_contradiction_detail_renders_all_structured_fields(self):
        html = render_report.build(
            {
                "title": "A decision",
                "contradictions": [
                    {"id": "X-001", "kind": "tension", "stake": "speed vs safety", "status": "partly"}
                ],
                "contradiction_detail": {
                    "X-001": {
                        "conflict_id": "X-001",
                        "contradiction_id": "X-001",
                        "claim_ids": ["C-001", "C-002"],
                        "scope_dimension": "deployment_context",
                        "decisive_missing_evidence": "Shadow-mode trial.",
                    }
                },
            }
        )

        self.assertIn("Claims:", html)
        self.assertIn("C-001", html)
        self.assertIn("C-002", html)
        self.assertIn("Scope dimension: deployment_context", html)
        self.assertIn("Decisive missing evidence: Shadow-mode trial.", html)

    def test_evidence_plan_renders_markdown_subset(self):
        html = render_report.build(
            {
                "title": "A decision",
                "evidence_plan": (
                    "# 03 - Evidence\n\n"
                    "### Practitioner\n\n"
                    "- Use solver docs to establish tooling: S-001, S-002.\n"
                ),
                "sources": [{"id": "S-001", "title": "OR-Tools", "type": "industry"}],
            }
        )

        self.assertIn("Evidence plan", html)
        self.assertIn("<h4>Practitioner</h4>", html)
        self.assertIn("Use solver docs", html)
        # A reference whose source is registered links to its anchor...
        self.assertIn('href="#ref-S-001"', html)
        # ...while one that is not stays an honest, non-linked chip.
        self.assertIn('<span class="cid">S-002</span>', html)
        # The markdown top-level title is dropped (the section carries its own).
        self.assertNotIn("03 - Evidence", html)

    def test_quality_gate_summary_is_folded_into_review(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            (base / "06_quality_gate.json").write_text(
                json.dumps(
                    {
                        "status": "PASS_WITH_CAVEATS",
                        "coverage_score": 100,
                        "traceability_score": 100,
                        "contradiction_handling_score": 50,
                        "recommendation_support_score": 100,
                        "review_summary": "PASS_WITH_CAVEATS computed by verify.py.",
                    }
                ),
                encoding="utf-8",
            )
            data = {"title": "A decision", "review": {"verdict": "PASS_WITH_CAVEATS"}}
            render_report._fold_in_artifacts(data, base)

        html = render_report.build(data)
        self.assertIn("PASS_WITH_CAVEATS computed by verify.py.", html)

    def test_artifact_markdown_sections_render_missing_research_context(self):
        html = render_report.build(
            {
                "title": "A decision",
                "decision_frame": (
                    "# 01 - Decision Frame\n\n"
                    "## Acceptance criteria\n\n"
                    "RL is a credible production option only if it:\n\n"
                    "1. Meets or beats a strong classical baseline.\n"
                    "2. Can run in shadow mode.\n"
                ),
                "contradiction_ledger": (
                    "# 04 - Contradiction Ledger\n\n"
                    "## Decision impact\n\n"
                    "The ledger blocks only a broad replacement recommendation.\n"
                ),
                "source_mapped_synthesis": (
                    "# 05 - Source-Mapped Synthesis\n\n"
                    "## Confidence-ranked claims\n\n"
                    "- High confidence: classical flow optimization is the baseline.\n\n"
                    "## Final synthesis\n\n"
                    'The practical recommendation is "RL around the optimizer."\n'
                ),
                "decision_brief": (
                    "# 05 - Decision Brief\n\n"
                    "## Non-recommendation\n\n"
                    "Do not fund an end-to-end RL replacement.\n"
                ),
                "adversarial_review": (
                    "# 06 - Adversarial Review\n\n"
                    "## Checks performed\n\n"
                    "| Check | Result |\n"
                    "| --- | --- |\n"
                    "| Overconfident wording | ok |\n\n"
                    "## Human review required\n\n"
                    "This output supports deliberation.\n"
                ),
            }
        )

        self.assertIn("Decision frame", html)
        self.assertIn("Meets or beats a strong classical baseline.", html)
        self.assertIn("<ol>", html)
        self.assertIn("Contradiction ledger notes", html)
        self.assertIn("The ledger blocks only a broad replacement recommendation.", html)
        self.assertIn("Source-mapped synthesis notes", html)
        self.assertIn("RL around the optimizer", html)
        self.assertIn("Decision brief artifact", html)
        self.assertIn("Do not fund an end-to-end RL replacement.", html)
        self.assertIn("Adversarial review notes", html)
        self.assertIn("<table>", html)
        self.assertIn("Overconfident wording", html)
        self.assertIn("This output supports deliberation.", html)

    def test_fold_in_artifacts_reads_full_report_context_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            (base / "01_decision_frame.md").write_text(
                "# 01 - Decision Frame\n\n## Scope\n\n- In scope: traffic engineering.\n",
                encoding="utf-8",
            )
            (base / "04_contradiction_ledger.md").write_text(
                "# 04 - Contradiction Ledger\n\n## Decision impact\n\nNarrow the recommendation.\n",
                encoding="utf-8",
            )
            (base / "05_synthesis.md").write_text(
                "# 05 - Source-Mapped Synthesis\n\n## Confidence-ranked claims\n\n- High confidence: baseline first.\n",
                encoding="utf-8",
            )
            (base / "05_decision_brief.md").write_text(
                "# 05 - Decision Brief\n\n## Non-recommendation\n\nNo end-to-end replacement.\n",
                encoding="utf-8",
            )
            (base / "06_adversarial_review.md").write_text(
                "# 06 - Adversarial Review\n\n## Human review required\n\nNeeds SRE sign-off.\n",
                encoding="utf-8",
            )

            data = {"title": "A decision"}
            render_report._fold_in_artifacts(data, base)
            html = render_report.build(data)

        self.assertIn("In scope: traffic engineering.", html)
        self.assertIn("Narrow the recommendation.", html)
        self.assertIn("High confidence: baseline first.", html)
        self.assertIn("No end-to-end replacement.", html)
        self.assertIn("Needs SRE sign-off.", html)

    def test_source_registry_metadata_and_bibtex_are_rendered(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            (base / "03_source_registry.csv").write_text(
                "source_id,title,url,publisher,publication_date,source_type,accessed_at,credibility_notes,relevance_notes\n"
                "S-001,OR-Tools,https://example.test/flow,Google Developers,2026-01-02,industry,2026-06-30T00:00:00+03:00,Official solver documentation,Establishes mature tooling.\n",
                encoding="utf-8",
            )
            (base / "03_sources.bib").write_text(
                "@misc{S001,\n"
                "  title = {OR-Tools},\n"
                "  author = {{Google Developers}},\n"
                "  year = {2026}\n"
                "}\n",
                encoding="utf-8",
            )

            data = {
                "title": "A decision",
                "sources": [{"id": "S-001", "title": "OR-Tools", "type": "industry"}],
            }
            render_report._enrich_source_urls(data, base)
            render_report._fold_in_artifacts(data, base)
            html = render_report.build(data)

        # APA citation rendered from BibTeX
        self.assertIn("Google Developers. (2026). OR-Tools.", html)
        self.assertIn('href="https://example.test/flow"', html)
        # Source registry metadata
        self.assertIn("Publisher: Google Developers", html)
        self.assertIn("Published: 2026-01-02", html)
        # accessed_at has a time component → wrapped in <time class="ts-local">
        self.assertIn('data-ts="2026-06-30T00:00:00+03:00"', html)
        self.assertIn('class="ts-local"', html)
        self.assertIn("Credibility: Official solver documentation", html)
        self.assertIn("Relevance: Establishes mature tooling.", html)
        # Raw BibTeX still available in the accordion
        self.assertIn("BibTeX records", html)
        self.assertIn("author = {{Google Developers}}", html)

    def test_section_numbers_are_sequential(self):
        html = render_report.build(
            {
                "title": "A decision",
                "bottom_line": "Use care.",
                "lens_charters": [{"name": "skeptic", "role_charter": "Stress-test."}],
                "strongest_findings": [{"title": "Finding", "text": "A backed finding.", "claims": ["C-001"]}],
                "claims": [{"claim_id": "C-001", "claim_text": "x", "evidence_status": "supported"}],
                "argument_map": 'flowchart TD\n  Q["Q?"]\n  Q --> A["A"]\n',
                "contradictions": [{"id": "X-001", "kind": "tension", "stake": "s", "status": "unresolved"}],
                "deliberation": [{"round": 1, "perspective": "academic", "move_type": "support", "text": "ok"}],
                "options": [{"name": "A", "strength": "strong", "points": ["p"]}],
                "next_actions": [{"text": "do C-001", "refs": ["C-001"]}],
                "gaps": [{"text": "gap"}],
                "evidence_plan": "### Plan\n\n- step one\n",
                "sources": [{"id": "S-001", "title": "Doc", "type": "industry"}],
                "review": {"verdict": "PASS", "blocking": [], "major": [], "minor": []},
            }
        )

        nums = re.findall(r'<span class="num">(\d+)</span>', html)
        self.assertEqual(nums, [f"{i:02d}" for i in range(1, len(nums) + 1)])
        self.assertEqual(len(nums), 13)

    def test_evidence_registry_renders_locators_and_excerpts(self):
        html = render_report.build(
            {
                "title": "A decision",
                "evidence": [
                    {
                        "evidence_id": "E-001",
                        "source_id": "S-001",
                        "locator": {"page": 5, "section": "4.2", "table": "Table 1"},
                        "evidence_excerpt": "Latency improved by 12% on Benchmark A.",
                    }
                ],
            }
        )

        self.assertIn("Evidence registry", html)
        self.assertIn('id="ref-E-001"', html)
        self.assertIn("page 5", html)
        self.assertIn("section 4.2", html)
        self.assertIn("Table 1", html)
        self.assertIn("Latency improved by 12%", html)

    def test_evidence_registry_renders_entailment_verdicts(self):
        html = render_report.build(
            {
                "title": "A decision",
                "evidence": [
                    {
                        "evidence_id": "E-001",
                        "source_id": "S-001",
                        "locator": {"section": "4.2"},
                        "evidence_excerpt": "The table reports throughput, not tail latency.",
                    }
                ],
                "evidence_verdicts": [
                    {
                        "claim_id": "C-001",
                        "evidence_id": "E-001",
                        "verdict": "does_not_entail",
                        "scope_preserved": "overclaimed",
                        "rationale": "The cited row is a different metric.",
                        "human_review_required": True,
                    }
                ],
            }
        )

        self.assertIn("does_not_entail", html)
        self.assertIn("scope: overclaimed", html)
        self.assertIn("verdict-bad", html)
        self.assertIn("The cited row is a different metric.", html)

    def test_fold_in_artifacts_reads_evidence_jsonl(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            (base / "03_evidence.jsonl").write_text(
                json.dumps({
                    "evidence_id": "E-001",
                    "source_id": "S-001",
                    "locator": {"section": "Abstract"},
                    "evidence_excerpt": "A compact abstract excerpt.",
                }) + "\n",
                encoding="utf-8",
            )
            data = {}
            render_report._fold_in_artifacts(data, base)
            self.assertEqual(data["evidence"][0]["evidence_id"], "E-001")

    def test_fold_in_artifacts_reads_evidence_verdicts_jsonl(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            (base / "03_evidence_verdicts.jsonl").write_text(
                json.dumps({
                    "claim_id": "C-001",
                    "evidence_id": "E-001",
                    "verdict": "does_not_entail",
                    "scope_preserved": "overclaimed",
                    "rationale": "Wrong metric.",
                    "human_review_required": True,
                }) + "\n",
                encoding="utf-8",
            )
            data = {}
            render_report._fold_in_artifacts(data, base)
            self.assertEqual(data["evidence_verdicts"][0]["verdict"], "does_not_entail")

    def test_evidence_source_status_badges(self):
        ev_abstract = {"evidence_id": "E-001", "source_id": "S-001", "extraction_method": "abstract"}
        ev_retracted = {"evidence_id": "E-002", "source_id": "S-002", "extraction_method": "full_text"}
        ev_corrected = {"evidence_id": "E-003", "source_id": "S-003", "extraction_method": "full_text"}
        ev_superseded = {"evidence_id": "E-004", "source_id": "S-004", "extraction_method": "full_text"}
        sources_by_id = {
            "S-002": {"id": "S-002", "publication_identity": {"retraction_status": "retracted"}},
            "S-003": {"id": "S-003", "publication_identity": {"correction_status": "corrected"}},
            "S-004": {"id": "S-004", "publication_status": "superseded"},
        }
        self.assertIn("abstract-only", render_report._evidence_source_badges(ev_abstract, sources_by_id))
        self.assertIn("retracted", render_report._evidence_source_badges(ev_retracted, sources_by_id))
        self.assertIn("corrected", render_report._evidence_source_badges(ev_corrected, sources_by_id))
        self.assertIn("superseded", render_report._evidence_source_badges(ev_superseded, sources_by_id))

        html = render_report.build({
            "title": "T",
            "evidence": [{"evidence_id": "E-005", "source_id": "S-002",
                          "extraction_method": "full_text", "evidence_excerpt": "x"}],
            "sources": [{"id": "S-002", "title": "Retracted Paper",
                         "publication_identity": {"retraction_status": "retracted"}}],
        })
        self.assertIn("retracted", html)


class LayerRenderingTest(unittest.TestCase):
    def _rich_data(self):
        mmd = "flowchart TD\n  C1[Claim C-001]:::claim --> D1[Decision]:::decision"
        return {
            "title": "Layered decision",
            "bottom_line": "Proceed with care.",
            "claims": [{"claim_id": "C-001", "perspective": "academic",
                        "claim_text": "A claim.", "claim_type": "fact",
                        "evidence_status": "supported", "confidence": 0.5,
                        "source_ids": ["S-001"]}],
            "sources": [{"id": "S-001", "title": "A source", "type": "peer_reviewed"}],
            "argument_map": mmd,
            "decision_frame": "# Frame\n\nRaw stage markdown.",
            "run_manifest": {"generated_at": "2026-06-30T22:45:00+00:00",
                             "dispatch_mode": "independent_subagents",
                             "models_per_lens": {"academic": "claude-opus-4-8"},
                             "retrieval_tools_used": ["web_search"],
                             "schema_version": "1.1"},
            "deliberation": [{"move_id": "M-001", "round": "R1", "lens": "skeptic",
                              "target_id": "C-001", "move": "challenge",
                              "statement": "Does the passage entail the claim?",
                              "effect": {"change_type": "confidence_delta",
                                         "field": "confidence", "before": 0.73,
                                         "after": 0.5, "resolves": ["X-001"]}}],
        }

    def test_layer_all_matches_default(self):
        data = self._rich_data()
        self.assertEqual(render_report.build(data), render_report.build(data, "all"))

    def test_layer_brief_excludes_registries(self):
        html = render_report.build(self._rich_data(), "brief")
        self.assertIn("Proceed with care.", html)
        self.assertNotIn("Claims &amp; evidence ledger", html)
        self.assertNotIn(">Sources<", html)
        self.assertNotIn("Run manifest", html)
        self.assertNotIn("Decision frame", html)

    def test_brief_has_no_cytoscape(self):
        html = render_report.build(self._rich_data(), "brief")
        self.assertNotIn("Cytoscape Consortium", html)
        self.assertNotIn("am-cy-data", html)  # the interactive-map data script

    def test_report_layer_keeps_ledger_drops_raw_and_cytoscape(self):
        html = render_report.build(self._rich_data(), "report")
        self.assertIn("Claims &amp; evidence ledger", html)
        self.assertNotIn("Cytoscape Consortium", html)
        self.assertNotIn("Run manifest", html)
        self.assertNotIn("Raw stage markdown.", html)

    def test_appendix_hosts_cytoscape_and_manifest(self):
        html = render_report.build(self._rich_data(), "appendix")
        self.assertIn("am-cy-data", html)
        self.assertIn("Run manifest", html)
        self.assertNotIn("Proceed with care.", html)

    def test_run_manifest_renders_in_appendix(self):
        html = render_report.build(self._rich_data(), "appendix")
        self.assertIn("Run manifest", html)
        self.assertIn("independent subagents", html)
        self.assertIn("web_search", html)

    def test_move_effect_updates_rendered_claim(self):
        html = render_report.build(self._rich_data(), "report")
        self.assertIn("claim-delta", html)
        self.assertIn("0.73", html)
        self.assertIn("after R1 challenge", html)

    def test_deliberation_renders_effect(self):
        html = render_report.build(self._rich_data(), "appendix")
        self.assertIn("mv-effect", html)
        self.assertIn("M-001", html)
        self.assertIn("resolves", html)

    def test_deliberation_without_effect_is_backward_compatible(self):
        moves = [{"round": "round_1", "lens": "academic", "target_id": "C-002",
                  "move": "support", "statement": "Agreed."}]
        html = render_report._deliberation_html(moves)
        self.assertIn("Agreed.", html)
        self.assertNotIn("mv-effect", html)

    def test_contradiction_resolution_renders_in_detail(self):
        detail = {"topic": "T", "resolution_status": "partially_resolved",
                  "resolution": {"basis": "deliberation", "evidence_ids": [],
                                 "move_ids": ["M-004"],
                                 "rationale": "Skeptic narrowed the tension."}}
        html = render_report._cx_detail_html(detail, {})
        self.assertIn("Resolution basis", html)
        self.assertIn("deliberation", html)
        self.assertIn("credited", html)
        self.assertIn("Skeptic narrowed the tension.", html)

    def test_baseless_resolution_renders_uncredited(self):
        detail = {"topic": "T", "resolution": {"basis": "none",
                                               "evidence_ids": [], "move_ids": []}}
        html = render_report._cx_detail_html(detail, {})
        self.assertIn("uncredited", html)

    def test_confidence_requires_basis(self):
        # A claim that records its confidence provenance renders the basis/band
        # alongside the float, and does not raise the soft-warn.
        with_basis = render_report._claims_table_html([
            {"claim_id": "C-001", "perspective": "academic", "claim_type": "fact",
             "evidence_status": "supported", "confidence": 0.61,
             "confidence_basis": "one full-text safe-RL survey; scope-narrowed after M-001",
             "confidence_band": "moderate"}])
        self.assertIn("0.61", with_basis)
        self.assertIn("one full-text safe-RL survey", with_basis)
        self.assertIn("moderate", with_basis)
        self.assertNotIn("basis not recorded", with_basis)
        # A pre-Phase-4 claim (float, no basis) is never blocking — the row still
        # renders — but carries a visible soft-warn instead of a bare number.
        without_basis = render_report._claims_table_html([
            {"claim_id": "C-002", "perspective": "academic", "claim_type": "fact",
             "evidence_status": "supported", "confidence": 0.61}])
        self.assertIn("C-002", without_basis)
        self.assertIn("basis not recorded", without_basis)

    def test_kpi_copy_no_calibration_claim(self):
        html = render_report.build(self._rich_data(), "report")
        # The confidence KPI must explicitly disclaim calibration rather than let
        # a bare 2-decimal number read as a calibrated probability.
        self.assertIn("not a calibrated probability", html)
        self.assertIn("basis", html)

    # --- 07a provenance seal ------------------------------------------------- #
    _PROVENANCE = {
        "sealed_at": "2026-07-01T14:32:07+00:00",
        "verdict_at_seal_time": {"status": "PASS_WITH_CAVEATS"},
        "hash_algorithm": "sha256",
        "schema_version": "1.0",
        "generator_version": "storm-council/verify.py",
        "artifacts": [{"path": "03_claims.jsonl", "sha256": "abc123def456", "bytes": 42}],
    }

    def test_provenance_section_renders_in_appendix(self):
        html = render_report.build(
            {"title": "A decision",
             "status": {"level": "unverified", "pill": "UNVERIFIED", "headline": "H"},
             "provenance": self._PROVENANCE}, "appendix")
        self.assertIn("Provenance", html)
        self.assertIn("2026-07-01T14:32:07+00:00", html)
        # Integrity-not-authenticity caveat must appear in the rendered copy.
        self.assertIn("integrity, not authenticity", html)
        # Status panel gains a neutral "sealed provenance" integrity chip.
        self.assertIn("sealed", html)

    def test_provenance_absent_renders_nothing(self):
        html = render_report.build({"title": "A decision"})
        self.assertNotIn("Provenance &amp; integrity", html)

    def test_provenance_omitted_from_brief_layer(self):
        html = render_report.build(
            {"title": "A decision", "provenance": self._PROVENANCE}, "brief")
        self.assertNotIn("Provenance &amp; integrity", html)


if __name__ == "__main__":
    unittest.main()
