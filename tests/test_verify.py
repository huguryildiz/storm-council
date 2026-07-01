import csv
import importlib.util
import io
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("verify", ROOT / "scripts" / "verify.py")
verify_mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(verify_mod)


def _write_run(base: Path, *, claims=None, sources=None, contradictions=None,
               evidence=None, report=None):
    if claims is not None:
        (base / "03_claims.jsonl").write_text(
            "\n".join(json.dumps(c) for c in claims) + "\n", encoding="utf-8")
    if evidence is not None:
        (base / "03_evidence.jsonl").write_text(
            "\n".join(json.dumps(e) for e in evidence) + "\n", encoding="utf-8")
    if sources is not None:
        buf = io.StringIO()
        cols = ["source_id", "title", "url", "publisher", "publication_date",
                "source_type", "accessed_at", "credibility_notes", "relevance_notes",
                "doi", "full_text_status", "publication_status", "source_class"]
        w = csv.DictWriter(buf, fieldnames=cols)
        w.writeheader()
        for s in sources:
            w.writerow({k: s.get(k, "") for k in cols})
        (base / "03_source_registry.csv").write_text(buf.getvalue(), encoding="utf-8")
    if contradictions is not None:
        (base / "04_contradictions.json").write_text(
            json.dumps(contradictions), encoding="utf-8")
    if report is not None:
        (base / "report_data.json").write_text(json.dumps(report), encoding="utf-8")


class HelperTest(unittest.TestCase):
    def test_normalize_doi_strips_prefixes(self):
        self.assertEqual(verify_mod.normalize_doi("https://doi.org/10.1145/3230543.3230551"),
                         "10.1145/3230543.3230551")
        self.assertEqual(verify_mod.normalize_doi("doi:10.1145/ABC"), "10.1145/abc")
        self.assertEqual(verify_mod.normalize_doi("  10.1000/xyz  "), "10.1000/xyz")

    def test_normalize_doi_rejects_malformed(self):
        self.assertIsNone(verify_mod.normalize_doi("not-a-doi"))
        self.assertIsNone(verify_mod.normalize_doi("10.x/abc"))
        self.assertIsNone(verify_mod.normalize_doi(""))

    def test_placeholder_url_detection(self):
        self.assertTrue(verify_mod.is_placeholder_url("https://example.invalid/p"))
        self.assertTrue(verify_mod.is_placeholder_url("http://localhost:8080/x"))
        self.assertTrue(verify_mod.is_placeholder_url("https://example.com/paper"))
        self.assertFalse(verify_mod.is_placeholder_url("https://arxiv.org/abs/2004.11986"))
        self.assertFalse(verify_mod.is_placeholder_url("https://developers.google.com/optimization"))

    def test_find_overclaims_hits_hard_terms(self):
        terms = verify_mod.find_overclaims("This proves the method is superior on all benchmarks.")
        self.assertIn("proves", terms)
        self.assertIn("superior", terms)
        self.assertIn("all", terms)

    def test_find_overclaims_respects_word_boundary(self):
        # "overall" must not match "all"; "smaller" must not match "all".
        self.assertEqual(verify_mod.find_overclaims("Overall the smaller model helps."), [])


class BackwardCompatTest(unittest.TestCase):
    def test_committed_example_remains_pass_with_caveats(self):
        gate = verify_mod.verify(ROOT / "examples" / "network_flow_rl")
        self.assertEqual(gate["status"], "PASS_WITH_CAVEATS")
        self.assertEqual(gate["blocking_issues"], [])

    def test_v1_clean_run_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            _write_run(
                base,
                claims=[{"claim_id": "C-001", "perspective": "academic",
                         "claim_text": "Solvers are mature for min-cost flow.",
                         "claim_type": "fact", "evidence_status": "supported",
                         "source_ids": ["S-001"]}],
                sources=[{"source_id": "S-001", "title": "OR-Tools",
                          "url": "https://developers.google.com/optimization",
                          "source_type": "industry",
                          "credibility_notes": "Official docs"}],
                contradictions=[],
            )
            gate = verify_mod.verify(base)
            self.assertEqual(gate["blocking_issues"], [])
            self.assertIn(gate["status"], {"PASS", "PASS_WITH_CAVEATS"})


class NegativeControlTest(unittest.TestCase):
    def test_fabricated_overclaiming_run_does_not_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            _write_run(
                base,
                claims=[{"claim_id": "C-001", "perspective": "academic",
                         "claim_text": "A fabricated paper proves deep RL is superior on all benchmarks.",
                         "claim_type": "fact", "confidence": 0.99,
                         "evidence_status": "supported", "source_ids": ["S-001"]}],
                sources=[{"source_id": "S-001", "title": "Totally Plausible Paper",
                          "url": "https://example.invalid/not-a-paper",
                          "source_type": "peer_reviewed",
                          "credibility_notes": "peer reviewed"}],
                contradictions=[],
            )
            gate = verify_mod.verify(base)
            self.assertIn(gate["status"], {"REVISE", "BLOCKED_PENDING_EVIDENCE"})
            self.assertTrue(gate["blocking_issues"])


class PublicationIdentityTest(unittest.TestCase):
    def test_duplicate_doi_is_flagged_major(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            _write_run(
                base,
                claims=[{"claim_id": "C-001", "perspective": "academic",
                         "claim_text": "Reported result holds in the cited study.",
                         "claim_type": "fact", "evidence_status": "supported",
                         "source_ids": ["S-001"]}],
                sources=[
                    {"source_id": "S-001", "title": "Paper (publisher)",
                     "url": "https://dl.acm.org/doi/10.1145/3230543.3230551",
                     "source_type": "peer_reviewed", "credibility_notes": "ok"},
                    {"source_id": "S-002", "title": "Paper (arXiv mirror)",
                     "url": "https://arxiv.org/abs/1807.00001",
                     "doi": "10.1145/3230543.3230551",
                     "source_type": "peer_reviewed", "credibility_notes": "ok"},
                ],
                contradictions=[],
            )
            gate = verify_mod.verify(base)
            self.assertTrue(any("duplicate" in m.lower() for m in gate["major_issues"]))

    def test_supported_claim_on_retracted_source_blocks(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            _write_run(
                base,
                claims=[{"claim_id": "C-001", "perspective": "academic",
                         "claim_text": "The retracted study reports an effect.",
                         "claim_type": "fact", "evidence_status": "supported",
                         "source_ids": ["S-001"]}],
                sources=[{"source_id": "S-001", "title": "Retracted Paper",
                          "url": "https://example.org/real-looking",
                          "source_type": "peer_reviewed",
                          "publication_status": "RETRACTED",
                          "credibility_notes": "ok"}],
                contradictions=[],
            )
            gate = verify_mod.verify(base)
            self.assertIn(gate["status"], {"REVISE", "BLOCKED_PENDING_EVIDENCE"})
            self.assertTrue(any("retract" in b.lower() for b in gate["blocking_issues"]))


class ContentVerificationTest(unittest.TestCase):
    def _base_source(self):
        return {"source_id": "S-001", "title": "Real Paper",
                "url": "https://arxiv.org/abs/2004.11986",
                "source_type": "peer_reviewed", "credibility_notes": "ok"}

    def test_direct_support_without_locator_blocks(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            _write_run(
                base,
                claims=[{"claim_id": "C-001", "perspective": "academic",
                         "claim_text": "Method X reduces latency.",
                         "claim_type": "fact", "evidence_status": "supported",
                         "source_ids": ["S-001"], "evidence_ids": ["E-001"],
                         "content_verification": {"status": "direct_support",
                                                  "full_text_status": "full_text"}}],
                evidence=[{"evidence_id": "E-001", "source_id": "S-001",
                           "locator": {}, "evidence_excerpt": "Latency improved."}],
                sources=[self._base_source()],
                contradictions=[],
            )
            gate = verify_mod.verify(base)
            self.assertIn(gate["status"], {"REVISE", "BLOCKED_PENDING_EVIDENCE"})
            self.assertTrue(any("locator" in b.lower() for b in gate["blocking_issues"]))

    def test_direct_support_with_locator_clears(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            _write_run(
                base,
                claims=[{"claim_id": "C-001", "perspective": "academic",
                         "claim_text": "Method X reduces latency in the cited evaluation.",
                         "claim_type": "fact", "evidence_status": "supported",
                         "source_ids": ["S-001"], "evidence_ids": ["E-001"],
                         "content_verification": {"status": "direct_support",
                                                  "full_text_status": "full_text"}}],
                evidence=[{"evidence_id": "E-001", "source_id": "S-001",
                           "locator": {"page": 5, "section": "4.2"},
                           "evidence_excerpt": "Latency improved by 12% (Table 2)."}],
                sources=[self._base_source()],
                contradictions=[],
            )
            gate = verify_mod.verify(base)
            self.assertEqual(gate["blocking_issues"], [])

    def test_abstract_only_cannot_directly_support_strong_claim(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            _write_run(
                base,
                claims=[{"claim_id": "C-001", "perspective": "academic",
                         "claim_text": "Method X causes a large improvement over the baseline.",
                         "claim_type": "fact", "claim_strength": "causal",
                         "evidence_status": "supported", "source_ids": ["S-001"],
                         "evidence_ids": ["E-001"],
                         "content_verification": {"status": "direct_support",
                                                  "full_text_status": "abstract_only"}}],
                evidence=[{"evidence_id": "E-001", "source_id": "S-001",
                           "locator": {"section": "Abstract"},
                           "evidence_excerpt": "We study method X."}],
                sources=[self._base_source()],
                contradictions=[],
            )
            gate = verify_mod.verify(base)
            self.assertIn(gate["status"], {"REVISE", "BLOCKED_PENDING_EVIDENCE"})
            self.assertTrue(any("abstract" in b.lower() for b in gate["blocking_issues"]))

    def test_comparative_claim_requires_scope_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            _write_run(
                base,
                claims=[{"claim_id": "C-001", "perspective": "academic",
                         "claim_text": "Method X outperforms the baseline.",
                         "claim_type": "fact", "claim_strength": "comparative",
                         "evidence_status": "supported", "source_ids": ["S-001"],
                         "evidence_ids": ["E-001"],
                         "content_verification": {"status": "direct_support",
                                                  "full_text_status": "full_text"},
                         "support_scope": {"metric": "", "comparison_baseline": "",
                                           "dataset_or_benchmark": ""}}],
                evidence=[{"evidence_id": "E-001", "source_id": "S-001",
                           "locator": {"table": "Table 1"},
                           "evidence_excerpt": "X beats Y."}],
                sources=[self._base_source()],
                contradictions=[],
            )
            gate = verify_mod.verify(base)
            self.assertTrue(any("scope" in m.lower() for m in gate["major_issues"]))


class EvidenceRegistryTest(unittest.TestCase):
    def test_evidence_id_must_resolve(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            _write_run(
                base,
                claims=[{"claim_id": "C-001", "perspective": "academic",
                         "claim_text": "A claim with a dangling evidence reference.",
                         "claim_type": "fact", "evidence_status": "supported",
                         "source_ids": ["S-001"], "evidence_ids": ["E-999"]}],
                evidence=[{"evidence_id": "E-001", "source_id": "S-001",
                           "locator": {"page": 1}}],
                sources=[{"source_id": "S-001", "title": "Real",
                          "url": "https://arxiv.org/abs/2004.11986",
                          "source_type": "peer_reviewed", "credibility_notes": "ok"}],
                contradictions=[],
            )
            gate = verify_mod.verify(base)
            self.assertTrue(any("E-999" in b for b in gate["blocking_issues"]))


class StatusBannerHonestyTest(unittest.TestCase):
    def test_positive_status_level_without_gate_file_is_flagged(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            _write_run(
                base,
                claims=[{"claim_id": "C-001", "perspective": "academic",
                         "claim_text": "Solvers are mature.",
                         "claim_type": "fact", "evidence_status": "supported",
                         "source_ids": ["S-001"]}],
                sources=[{"source_id": "S-001", "title": "OR-Tools",
                          "url": "https://developers.google.com/optimization",
                          "source_type": "industry", "credibility_notes": "ok"}],
                contradictions=[],
                report={"status": {"level": "pass", "pill": "PASS", "headline": "All good."}},
            )
            gate = verify_mod.verify(base)
            self.assertTrue(
                any("06_quality_gate" in m for m in gate["major_issues"]),
                msg=f"Expected banner honesty major issue, got: {gate['major_issues']}"
            )

    def test_positive_status_level_with_gate_file_is_clean(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            _write_run(
                base,
                claims=[{"claim_id": "C-001", "perspective": "academic",
                         "claim_text": "Solvers are mature.",
                         "claim_type": "fact", "evidence_status": "supported",
                         "source_ids": ["S-001"]}],
                sources=[{"source_id": "S-001", "title": "OR-Tools",
                          "url": "https://developers.google.com/optimization",
                          "source_type": "industry", "credibility_notes": "ok"}],
                contradictions=[],
                report={"status": {"level": "pass", "pill": "PASS", "headline": "All good."}},
            )
            (Path(tmp) / "06_quality_gate.json").write_text(
                '{"status": "PASS", "blocking_issues": [], "major_issues": [], "minor_issues": []}',
                encoding="utf-8",
            )
            gate = verify_mod.verify(base)
            self.assertFalse(
                any("06_quality_gate" in m for m in gate["major_issues"]),
                msg=f"No banner issue expected when gate file exists, got: {gate['major_issues']}"
            )


class ContradictionShapeTest(unittest.TestCase):
    def test_accepts_claim_ids_list_shape(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            _write_run(
                base,
                claims=[
                    {"claim_id": "C-001", "perspective": "academic",
                     "claim_text": "A.", "claim_type": "fact",
                     "evidence_status": "supported", "source_ids": ["S-001"]},
                    {"claim_id": "C-002", "perspective": "skeptic",
                     "claim_text": "B.", "claim_type": "inference",
                     "evidence_status": "partially_supported", "source_ids": ["S-001"]},
                ],
                sources=[{"source_id": "S-001", "title": "Real",
                          "url": "https://arxiv.org/abs/2004.11986",
                          "source_type": "peer_reviewed", "credibility_notes": "ok"}],
                contradictions=[{"contradiction_id": "X-001",
                                 "claim_ids": ["C-001", "C-002"],
                                 "resolution_status": "unresolved"}],
            )
            gate = verify_mod.verify(base)
            self.assertFalse(any("missing claim" in b.lower() for b in gate["blocking_issues"]))


class ContradictionResolutionGateTest(unittest.TestCase):
    def _two_claim_run(self, base, contradictions):
        _write_run(
            base,
            claims=[
                {"claim_id": "C-001", "perspective": "academic", "claim_text": "A.",
                 "claim_type": "fact", "evidence_status": "supported", "source_ids": ["S-001"]},
                {"claim_id": "C-002", "perspective": "skeptic", "claim_text": "B.",
                 "claim_type": "inference", "evidence_status": "partially_supported",
                 "source_ids": ["S-001"]},
            ],
            sources=[{"source_id": "S-001", "title": "Real",
                      "url": "https://arxiv.org/abs/2004.11986",
                      "source_type": "peer_reviewed", "credibility_notes": "ok"}],
            contradictions=contradictions,
        )

    def test_resolution_requires_basis(self):
        # A "resolved" status with no basis is flagged and does not count as handled.
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            self._two_claim_run(base, [
                {"id": "X-001", "claim_ids": ["C-001", "C-002"],
                 "resolution_status": "resolved"},
            ])
            gate = verify_mod.verify(base)
            self.assertEqual(gate["contradiction_handling_score"], 0)
            self.assertTrue(any("without an evidence/move basis" in m
                                for m in gate["minor_issues"]))

    def test_contradiction_score_ignores_baseless_resolution(self):
        # Identical run except for a credited resolution -> score jumps 0 -> 100.
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            self._two_claim_run(base, [
                {"id": "X-001", "claim_ids": ["C-001", "C-002"],
                 "resolution_status": "resolved",
                 "resolution": {"basis": "none", "evidence_ids": [], "move_ids": []}},
            ])
            baseless = verify_mod.verify(base)["contradiction_handling_score"]

        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            self._two_claim_run(base, [
                {"id": "X-001", "claim_ids": ["C-001", "C-002"],
                 "resolution_status": "resolved",
                 "resolution": {"basis": "deliberation", "evidence_ids": [],
                                "move_ids": ["M-004"],
                                "rationale": "Skeptic conceded the scoped point."}},
            ])
            credited = verify_mod.verify(base)["contradiction_handling_score"]

        self.assertEqual(baseless, 0)
        self.assertEqual(credited, 100)

    def test_canonical_id_alias_still_resolves(self):
        # `id` is preferred, but the deprecated `conflict_id` alias still resolves.
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            self._two_claim_run(base, [
                {"conflict_id": "X-001", "claim_ids": ["C-001", "C-002"],
                 "resolution_status": "unresolved"},
            ])
            gate = verify_mod.verify(base)
            self.assertFalse(any("missing claim" in b.lower()
                                 for b in gate["blocking_issues"]))


class AntiRubberStampTest(unittest.TestCase):
    """Phase 2: surface a verifier that never pushes back (minor-only advisories)."""

    _CLAIMS = [
        {"claim_id": "C-001", "perspective": "academic", "claim_text": "A.",
         "claim_type": "fact", "evidence_status": "supported", "source_ids": ["S-001"],
         "evidence_ids": ["E-001"]},
        {"claim_id": "C-002", "perspective": "skeptic", "claim_text": "B.",
         "claim_type": "inference", "evidence_status": "supported", "source_ids": ["S-001"],
         "evidence_ids": ["E-002"]},
        {"claim_id": "C-003", "perspective": "economist", "claim_text": "C.",
         "claim_type": "fact", "evidence_status": "supported", "source_ids": ["S-001"],
         "evidence_ids": ["E-003"]},
    ]
    _SOURCES = [{"source_id": "S-001", "title": "Real",
                 "url": "https://arxiv.org/abs/2004.11986",
                 "source_type": "peer_reviewed", "credibility_notes": "ok"}]
    _EVIDENCE = [{"evidence_id": f"E-00{i}", "source_id": "S-001"} for i in (1, 2, 3)]
    _CONTRADICTIONS = [{"id": "X-001", "claim_ids": ["C-001", "C-002"],
                        "resolution_status": "unresolved"}]

    def _verdict(self, cid, eid, rationale, verdict="entails"):
        return {"claim_id": cid, "evidence_id": eid, "verdict": verdict,
                "scope_preserved": "yes", "rationale": rationale,
                "human_review_required": False}

    def test_identical_rationale_flagged(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            _write_run(base, claims=self._CLAIMS, sources=self._SOURCES,
                       evidence=self._EVIDENCE, contradictions=self._CONTRADICTIONS)
            (base / "03_evidence_verdicts.jsonl").write_text(
                "\n".join(json.dumps(v) for v in [
                    self._verdict("C-001", "E-001", "Same rationale."),
                    self._verdict("C-002", "E-002", "Same rationale."),
                    self._verdict("C-003", "E-003", "Same rationale."),
                ]) + "\n", encoding="utf-8")
            gate = verify_mod.verify(base)
            self.assertTrue(any("not individually reasoned" in m.lower()
                                for m in gate["minor_issues"]))
            self.assertEqual(gate["blocking_issues"], [])

    def test_zero_rejection_flagged(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            _write_run(base, claims=self._CLAIMS, sources=self._SOURCES,
                       evidence=self._EVIDENCE, contradictions=self._CONTRADICTIONS)
            (base / "03_evidence_verdicts.jsonl").write_text(
                "\n".join(json.dumps(v) for v in [
                    self._verdict("C-001", "E-001", "Distinct reasoning one."),
                    self._verdict("C-002", "E-002", "Distinct reasoning two."),
                ]) + "\n", encoding="utf-8")
            gate = verify_mod.verify(base)
            self.assertTrue(any("did not push back" in m.lower()
                                for m in gate["minor_issues"]))
            self.assertEqual(gate["blocking_issues"], [])

    def test_diverse_rationales_not_flagged(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            claims = [dict(c) for c in self._CLAIMS]
            claims[2]["evidence_status"] = "unsupported"  # a rejection: no zero-rejection flag
            _write_run(base, claims=claims, sources=self._SOURCES,
                       evidence=self._EVIDENCE, contradictions=self._CONTRADICTIONS)
            (base / "03_evidence_verdicts.jsonl").write_text(
                "\n".join(json.dumps(v) for v in [
                    self._verdict("C-001", "E-001", "First distinct rationale."),
                    self._verdict("C-002", "E-002", "Second distinct rationale."),
                ]) + "\n", encoding="utf-8")
            gate = verify_mod.verify(base)
            self.assertFalse(any("not individually reasoned" in m.lower()
                                 for m in gate["minor_issues"]))
            self.assertFalse(any("did not push back" in m.lower()
                                 for m in gate["minor_issues"]))


class SourceClassIntegrityTest(unittest.TestCase):
    """Phase 3: a run's own retrieval log is not interchangeable with external
    evidence at the support layer."""

    def test_run_log_only_support_is_major(self):
        # A supported claim whose only source is a run_log ⇒ major (never blocking).
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            _write_run(
                base,
                claims=[{"claim_id": "C-001", "perspective": "skeptic",
                         "claim_text": "Live queries returned no production RL replacement.",
                         "claim_type": "fact", "evidence_status": "supported",
                         "source_ids": ["S-009"]}],
                sources=[{"source_id": "S-009", "title": "Run query log",
                          "url": "", "source_type": "primary",
                          "source_class": "run_log", "credibility_notes": "run-local audit"}],
                contradictions=[],
            )
            gate = verify_mod.verify(base)
            self.assertTrue(any("run-log provenance" in m and "C-001" in m
                                for m in gate["major_issues"]))
            self.assertEqual(gate["blocking_issues"], [])

    def test_missing_source_class_is_not_run_log_only(self):
        # Back-compat: a registry with no source_class must never trip the gate.
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            _write_run(
                base,
                claims=[{"claim_id": "C-001", "perspective": "academic",
                         "claim_text": "Solvers are mature.", "claim_type": "fact",
                         "evidence_status": "supported", "source_ids": ["S-001"]}],
                sources=[{"source_id": "S-001", "title": "OR-Tools",
                          "url": "https://developers.google.com/optimization",
                          "source_type": "industry", "credibility_notes": "Official docs"}],
                contradictions=[],
            )
            gate = verify_mod.verify(base)
            self.assertFalse(any("run-log provenance" in m for m in gate["major_issues"]))

    def test_run_log_plus_external_source_is_clean(self):
        # A supported claim also citing a real source is not run-log-only.
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            _write_run(
                base,
                claims=[{"claim_id": "C-001", "perspective": "academic",
                         "claim_text": "Result holds.", "claim_type": "fact",
                         "evidence_status": "supported", "source_ids": ["S-001", "S-009"]}],
                sources=[{"source_id": "S-001", "title": "Paper",
                          "url": "https://arxiv.org/abs/2004.11986",
                          "source_type": "peer_reviewed", "source_class": "peer_reviewed",
                          "credibility_notes": "ok"},
                         {"source_id": "S-009", "title": "Run log", "url": "",
                          "source_type": "primary", "source_class": "run_log",
                          "credibility_notes": "run-local audit"}],
                contradictions=[],
            )
            gate = verify_mod.verify(base)
            self.assertFalse(any("run-log provenance" in m for m in gate["major_issues"]))

    def test_committed_examples_stay_pass_with_caveats(self):
        # The backfilled example bundles raise the run-log-only major but the
        # verdict tier must remain PASS_WITH_CAVEATS.
        for name in ("network_flow_rl", "ai_jobs_policy"):
            gate = verify_mod.verify(ROOT / "examples" / name)
            self.assertEqual(gate["status"], "PASS_WITH_CAVEATS", name)
            self.assertTrue(any("run-log provenance" in m for m in gate["major_issues"]), name)


if __name__ == "__main__":
    unittest.main()
