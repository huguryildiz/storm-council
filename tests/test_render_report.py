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

        self.assertIn('<div class="brand-logo"', html)
        self.assertIn("<svg", html)
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

        self.assertIn("confidence 0.88", html)
        self.assertIn("created 2026-06-30T00:01:00+03:00", html)

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
        self.assertIn("Use the classical baseline", html)
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
        self.assertIn("Do not generalize", html)

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

        self.assertIn('href="https://example.test/flow"', html)
        self.assertIn("Publisher: Google Developers", html)
        self.assertIn("Published: 2026-01-02", html)
        self.assertIn("Accessed: 2026-06-30T00:00:00+03:00", html)
        self.assertIn("Credibility: Official solver documentation", html)
        self.assertIn("Relevance: Establishes mature tooling.", html)
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


if __name__ == "__main__":
    unittest.main()
