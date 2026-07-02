import contextlib
import csv
import hashlib
import importlib.util
import io
import json
import os
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("verify", ROOT / "scripts" / "verify.py")
verify_mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(verify_mod)


def _write_run(base: Path, *, claims=None, sources=None, contradictions=None,
               evidence=None, report=None, tripwires=None, support_packets=None,
               verdicts=None):
    if claims is not None:
        (base / "03_claims.jsonl").write_text(
            "\n".join(json.dumps(c) for c in claims) + "\n", encoding="utf-8")
    if evidence is not None:
        (base / "03_evidence.jsonl").write_text(
            "\n".join(json.dumps(e) for e in evidence) + "\n", encoding="utf-8")
    if support_packets is not None:
        (base / "03_support_packets.jsonl").write_text(
            "\n".join(json.dumps(p) for p in support_packets) + "\n", encoding="utf-8")
    if verdicts is not None:
        (base / "03_evidence_verdicts.jsonl").write_text(
            "\n".join(json.dumps(v) for v in verdicts) + "\n", encoding="utf-8")
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
    if tripwires is not None:
        (base / "decision_tripwires.json").write_text(
            json.dumps(tripwires), encoding="utf-8")


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


class PassageSupportPacketTest(unittest.TestCase):
    """Passage support audit: source identity/relevance is separate from
    claim-passage entailment. Existing bundles without packets stay readable;
    packeted bundles get deterministic quote/hash checks."""

    def _material(self, base: Path, text: str, name: str = "S-001.txt") -> tuple[str, str]:
        mat_dir = base / "source_material"
        mat_dir.mkdir()
        rel = f"source_material/{name}"
        path = base / rel
        path.write_text(text, encoding="utf-8")
        return rel, hashlib.sha256(text.encode("utf-8")).hexdigest()

    def _claim(self, **kw):
        out = {
            "claim_id": "C-001",
            "perspective": "academic",
            "claim_text": "Method X outperforms baseline Y on Benchmark Z.",
            "claim_type": "fact",
            "claim_strength": "comparative",
            "confidence": 0.81,
            "evidence_status": "supported",
            "source_ids": ["S-001"],
            "evidence_ids": ["E-001"],
            "content_verification": {
                "status": "direct_support",
                "full_text_status": "full_text",
            },
            "support_scope": {
                "metric": "score",
                "comparison_baseline": "baseline Y",
                "dataset_or_benchmark": "Benchmark Z",
            },
        }
        out.update(kw)
        return out

    def _source(self, **kw):
        out = {
            "source_id": "S-001",
            "title": "Benchmark Paper",
            "url": "https://doi.org/10.5555/benchmark.paper",
            "doi": "10.5555/benchmark.paper",
            "source_type": "peer_reviewed",
            "source_class": "peer_reviewed",
            "full_text_status": "full_text",
            "publication_status": "PUBLISHED_VERIFIED",
            "credibility_notes": "ok",
        }
        out.update(kw)
        return out

    def _evidence(self, **kw):
        out = {
            "evidence_id": "E-001",
            "source_id": "S-001",
            "locator": {"table": "Table 1"},
            "evidence_excerpt": "Method X reports a higher score than baseline Y on Benchmark Z.",
        }
        out.update(kw)
        return out

    def _packet(self, rel: str, sha: str, quote: str, **kw):
        out = {
            "packet_id": "P-001",
            "claim_id": "C-001",
            "evidence_id": "E-001",
            "source_id": "S-001",
            "source_material_path": rel,
            "source_material_sha256": sha,
            "locator": {"table": "Table 1"},
            "quoted_passage": quote,
            "source_access": "full_text",
            "extraction_method": "manual",
            "retrieval_log_id": "R-001",
            "context_note": "Table row used for the comparison.",
        }
        out.update(kw)
        return out

    def _verdict(self, **kw):
        out = {
            "claim_id": "C-001",
            "evidence_id": "E-001",
            "packet_id": "P-001",
            "judged_claim": "Method X outperforms baseline Y on Benchmark Z.",
            "claim_atoms": ["Method X has a higher score than baseline Y on Benchmark Z."],
            "entailed_atoms": ["Method X has a higher score than baseline Y on Benchmark Z."],
            "unsupported_atoms": [],
            "verdict": "entails",
            "scope_preserved": "yes",
            "rationale": "The table reports the same metric, baseline, and benchmark.",
            "human_review_required": False,
            "judge_type": "llm_assisted",
            "judge_prompt_version": "stage_content_verification.v2",
        }
        out.update(kw)
        return out

    def test_doi_verified_source_without_packet_is_not_passage_checked(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            _write_run(
                base,
                claims=[self._claim()],
                evidence=[self._evidence()],
                sources=[self._source()],
                contradictions=[],
                verdicts=[self._verdict(packet_id=None)],
            )
            gate = verify_mod.verify(base)
            self.assertEqual(gate["argument_support_status"], "not_checked")
            self.assertEqual(gate["argument_support_score"], 0)
            self.assertEqual(gate["blocking_issues"], [])

    def test_clean_packet_with_quote_present_counts_as_passage_checked(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            quote = "Method X reports a higher score than baseline Y on Benchmark Z."
            rel, sha = self._material(base, f"Intro.\n{quote}\nLimitations.")
            _write_run(
                base,
                claims=[self._claim()],
                evidence=[self._evidence(evidence_excerpt=quote)],
                sources=[self._source()],
                contradictions=[],
                support_packets=[self._packet(rel, sha, quote)],
                verdicts=[self._verdict()],
            )
            gate = verify_mod.verify(base)
            self.assertEqual(gate["argument_support_status"], "passage_checked")
            self.assertEqual(gate["argument_support_score"], 100)
            self.assertFalse(any("support packet" in m.lower()
                                 for m in gate["blocking_issues"] + gate["major_issues"]))

    def test_quote_missing_from_source_material_is_blocking_for_direct_support(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            quote = "Method X reports a higher score than baseline Y on Benchmark Z."
            rel, sha = self._material(base, "The source talks about a different experiment.")
            _write_run(
                base,
                claims=[self._claim()],
                evidence=[self._evidence(evidence_excerpt=quote)],
                sources=[self._source()],
                contradictions=[],
                support_packets=[self._packet(rel, sha, quote)],
                verdicts=[self._verdict()],
            )
            gate = verify_mod.verify(base)
            self.assertEqual(gate["argument_support_status"], "partial_review")
            self.assertTrue(any("quoted passage not found" in b.lower()
                                for b in gate["blocking_issues"]))

    def test_missing_source_material_hash_cannot_count_as_clean_support(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            quote = "Method X reports a higher score than baseline Y on Benchmark Z."
            rel, _ = self._material(base, f"Intro.\n{quote}\nLimitations.")
            _write_run(
                base,
                claims=[self._claim()],
                evidence=[self._evidence(evidence_excerpt=quote)],
                sources=[self._source()],
                contradictions=[],
                support_packets=[self._packet(rel, "", quote)],
                verdicts=[self._verdict()],
            )
            gate = verify_mod.verify(base)
            self.assertEqual(gate["argument_support_score"], 0)
            self.assertEqual(gate["argument_support_status"], "partial_review")
            self.assertTrue(any("missing source_material_sha256" in b
                                for b in gate["blocking_issues"]))

    def test_abstract_only_packet_does_not_count_as_clean_support(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            quote = "The abstract says Method X is evaluated on Benchmark Z."
            rel, sha = self._material(base, quote)
            _write_run(
                base,
                claims=[self._claim(content_verification={"status": "direct_support",
                                                          "full_text_status": "abstract_only"})],
                evidence=[self._evidence(locator={"section": "Abstract"},
                                         evidence_excerpt=quote,
                                         extraction_method="abstract")],
                sources=[self._source(full_text_status="abstract_only")],
                contradictions=[],
                support_packets=[self._packet(rel, sha, quote, source_access="abstract_only")],
                verdicts=[self._verdict(rationale="Only abstract-level evidence is available.")],
            )
            gate = verify_mod.verify(base)
            self.assertEqual(gate["argument_support_score"], 0)
            self.assertEqual(gate["argument_support_status"], "partial_review")
            self.assertTrue(any("abstract" in b.lower() for b in gate["blocking_issues"]))

    def test_metadata_only_packet_sets_metadata_status_not_passage_checked(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            quote = "Crossref metadata confirms a paper title about Method X."
            rel, sha = self._material(base, quote)
            _write_run(
                base,
                claims=[self._claim(content_verification={"status": "partial_support",
                                                          "full_text_status": "metadata_only"})],
                evidence=[self._evidence(locator={"section": "DOI metadata"},
                                         evidence_excerpt=quote,
                                         extraction_method="metadata")],
                sources=[self._source(full_text_status="metadata_only")],
                contradictions=[],
                support_packets=[self._packet(rel, sha, quote, source_access="metadata_only",
                                              extraction_method="metadata")],
                verdicts=[self._verdict(verdict="partial", scope_preserved="uncertain",
                                        human_review_required=True,
                                        rationale="Metadata identifies the paper, not the claim.")],
            )
            gate = verify_mod.verify(base)
            self.assertEqual(gate["argument_support_status"], "metadata_only")
            self.assertEqual(gate["argument_support_score"], 0)

    def test_packet_path_must_stay_under_source_material(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            quote = "Method X reports a higher score than baseline Y on Benchmark Z."
            _write_run(
                base,
                claims=[self._claim()],
                evidence=[self._evidence(evidence_excerpt=quote)],
                sources=[self._source()],
                contradictions=[],
                support_packets=[self._packet("../outside.txt", "0" * 64, quote)],
                verdicts=[self._verdict()],
            )
            gate = verify_mod.verify(base)
            self.assertTrue(any("outside source_material" in b.lower()
                                for b in gate["blocking_issues"]))


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


class LensIndependenceTest(unittest.TestCase):
    """Phase 5: an optional, minor-only read of whether the lens *outputs*
    actually diverged — complementing run_manifest.json, which only attests the
    claim of independent contexts."""

    _SOURCES = [{"source_id": "S-001", "title": "Real",
                 "url": "https://arxiv.org/abs/2004.11986",
                 "source_type": "peer_reviewed", "credibility_notes": "ok"}]

    def _claim(self, cid, perspective, text):
        return {"claim_id": cid, "perspective": perspective, "claim_text": text,
                "claim_type": "fact", "evidence_status": "supported",
                "source_ids": ["S-001"]}

    def test_converged_lens_output_flagged(self):
        # Two lenses producing near-identical claim text ⇒ minor advisory.
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            shared = "Reinforcement learning does not replace exact min-cost-flow solvers."
            _write_run(base, sources=self._SOURCES, contradictions=[], claims=[
                self._claim("C-001", "economist", shared),
                self._claim("C-002", "historian", shared),
            ])
            gate = verify_mod.verify(base)
            self.assertTrue(any("lens outputs converged" in m.lower()
                                for m in gate["minor_issues"]))
            self.assertEqual(gate["blocking_issues"], [])

    def test_distinct_lens_output_not_flagged(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            _write_run(base, sources=self._SOURCES, contradictions=[], claims=[
                self._claim("C-001", "economist",
                            "Total cost of ownership favors the incumbent solver by 3x."),
                self._claim("C-002", "historian",
                            "Prior optimization-ML waves stalled at the integration boundary."),
            ])
            gate = verify_mod.verify(base)
            self.assertFalse(any("lens outputs converged" in m.lower()
                                 for m in gate["minor_issues"]))

    def test_examples_do_not_trip_convergence(self):
        # Guard against over-fitting: the shipped bundles must not converge.
        for name in ("network_flow_rl", "ai_jobs_policy"):
            gate = verify_mod.verify(ROOT / "examples" / name)
            self.assertFalse(any("lens outputs converged" in m.lower()
                                 for m in gate["minor_issues"]), name)


class SealTest(unittest.TestCase):
    """07a tamper-evident provenance bundle (verify.py --seal / --check-seal)."""

    _VERDICT_FIELDS = ("status", "coverage_score", "traceability_score",
                       "argument_support_score",
                       "contradiction_handling_score", "recommendation_support_score")

    def _make_bundle(self, base: Path):
        """A minimal, gradeable bundle plus one text artifact to tamper with."""
        _write_run(
            base,
            claims=[{"claim_id": "C-001", "perspective": "academic",
                     "claim_text": "The solver converges.", "claim_type": "fact",
                     "evidence_status": "supported", "source_ids": ["S-001"]}],
            sources=[{"source_id": "S-001", "title": "A paper",
                      "url": "https://arxiv.org/abs/2004.11986",
                      "source_type": "preprint", "source_class": "preprint"}],
            contradictions=[],
        )
        (base / "05_decision_brief.md").write_text("original brief\n", encoding="utf-8")

    def _run(self, argv):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = verify_mod.main(argv)
        return rc, buf.getvalue()

    def test_seal_refuses_without_quality_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            self._make_bundle(base)  # no --write, so no 06_quality_gate.json
            rc = verify_mod.main([str(base), "--seal"])
            self.assertEqual(rc, 3)
            self.assertFalse((base / "provenance_manifest.json").exists())

    def test_seal_writes_manifest_with_verdict_copied_from_quality_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            self._make_bundle(base)
            self.assertEqual(verify_mod.main([str(base), "--write"]), 0)
            gate = json.loads((base / "06_quality_gate.json").read_text(encoding="utf-8"))
            self.assertEqual(verify_mod.main([str(base), "--seal"]), 0)
            manifest = json.loads((base / "provenance_manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["verdict_at_seal_time"],
                             {k: gate[k] for k in self._VERDICT_FIELDS})
            self.assertEqual(manifest["hash_algorithm"], "sha256")

    def test_check_seal_passes_on_unmodified_bundle(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            self._make_bundle(base)
            verify_mod.main([str(base), "--write"])
            verify_mod.main([str(base), "--seal"])
            rc, out = self._run([str(base), "--check-seal"])
            self.assertEqual(rc, 0)
            self.assertIn("PASS", out)

    def test_check_seal_detects_single_byte_tamper(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            self._make_bundle(base)
            verify_mod.main([str(base), "--write"])
            verify_mod.main([str(base), "--seal"])
            (base / "05_decision_brief.md").write_text("Original brief\n", encoding="utf-8")
            rc, out = self._run([str(base), "--check-seal"])
            self.assertEqual(rc, 4)
            self.assertIn("altered: 05_decision_brief.md", out)
            self.assertNotIn("altered: 03_claims.jsonl", out)

    def test_check_seal_detects_deleted_artifact(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            self._make_bundle(base)
            verify_mod.main([str(base), "--write"])
            verify_mod.main([str(base), "--seal"])
            os.remove(base / "03_source_registry.csv")
            rc, out = self._run([str(base), "--check-seal"])
            self.assertEqual(rc, 4)
            self.assertIn("missing: 03_source_registry.csv", out)

    def test_check_seal_ignores_added_file_since_seal(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            self._make_bundle(base)
            verify_mod.main([str(base), "--write"])
            verify_mod.main([str(base), "--seal"])
            (base / "07_addendum.md").write_text("added later\n", encoding="utf-8")
            rc, out = self._run([str(base), "--check-seal"])
            self.assertEqual(rc, 0)
            self.assertIn("PASS", out)
            self.assertIn("added since seal: 07_addendum.md", out)

    def test_reseal_of_unchanged_bundle_reproduces_identical_hashes(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            self._make_bundle(base)
            verify_mod.main([str(base), "--write"])
            m1 = verify_mod.compute_seal(base, sealed_at="2026-07-01T00:00:00+00:00")
            m2 = verify_mod.compute_seal(base, sealed_at="2026-07-02T00:00:00+00:00")
            self.assertEqual(m1["artifacts"], m2["artifacts"])
            self.assertNotEqual(m1["sealed_at"], m2["sealed_at"])

    def test_artifacts_sorted_by_path_not_filesystem_order(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            # Deliberately create files out of alphabetical order.
            (base / "zz_last.md").write_text("z\n", encoding="utf-8")
            (base / "aa_first.md").write_text("a\n", encoding="utf-8")
            self._make_bundle(base)
            verify_mod.main([str(base), "--write"])
            manifest = verify_mod.compute_seal(base)
            paths = [a["path"] for a in manifest["artifacts"]]
            self.assertEqual(paths, sorted(paths))
            self.assertLess(paths.index("aa_first.md"), paths.index("zz_last.md"))

    def test_manifest_excludes_itself_from_hashed_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            self._make_bundle(base)
            verify_mod.main([str(base), "--write"])
            verify_mod.main([str(base), "--seal"])
            manifest = json.loads((base / "provenance_manifest.json").read_text(encoding="utf-8"))
            self.assertFalse(any(a["path"] == "provenance_manifest.json"
                                 for a in manifest["artifacts"]))

    def test_signature_field_is_null_in_mvp(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            self._make_bundle(base)
            verify_mod.main([str(base), "--write"])
            manifest = verify_mod.compute_seal(base)
            self.assertIsNone(manifest["signature"])


# --------------------------------------------------------------------------- #
# 07b — living, re-verifiable brief (verify.py --recheck)
# --------------------------------------------------------------------------- #

FIXTURES = ROOT / "tests" / "fixtures" / "metadata"


class _FakeFetcher:
    """Maps URL substrings to fixture files (bytes). A None mapping raises
    OSError (simulating an offline/404 adapter). Unmapped URLs raise too, which
    cached_json/cached_text catch and log as offline."""
    def __init__(self, mapping):
        self.mapping = mapping
        self.calls = []

    def __call__(self, url, headers=None, timeout=20):
        self.calls.append(url)
        for key, fixture in self.mapping.items():
            if key in url:
                if fixture is None:
                    raise OSError("offline or 404")
                return (FIXTURES / fixture).read_text(encoding="utf-8").encode("utf-8")
        raise OSError("unexpected URL: " + url)


_CLEAN_VERSION = {
    "source_id": "S-001", "canonical_source_id": "S-001", "duplicate_of": None,
    "identifiers": {"doi_normalized": "10.5555/retracted.paper"},
    "publication_identity": {"status": "PUBLISHED_VERIFIED", "retraction_status": "not_retracted"},
    "flags": {"retracted": False, "superseded": False, "corrected": False, "duplicate_version": False},
}

_RETRACTED_FETCHER = {
    "10.5555%2Fretracted.paper": "crossref_retracted.json",
    "doi.org/10.5555/retracted.paper": "crossref_retracted.json",
    "openalex.org/works/doi:10.5555%2Fretracted.paper": "openalex_retracted.json",
}

_CLEAN_FETCHER = {
    "10.5555%2Fretracted.paper": "crossref_duplicate.json",
    "doi.org/10.5555/retracted.paper": "crossref_duplicate.json",
}


class RecheckTest(unittest.TestCase):
    def _bundle(self, base, *, with_prior_versions=None, with_gate=False):
        _write_run(
            base,
            sources=[{"source_id": "S-001", "title": "Paper",
                      "doi": "10.5555/retracted.paper", "source_type": "peer_reviewed"}],
            claims=[{"claim_id": "C-001", "perspective": "academic", "claim_text": "A.",
                     "claim_type": "fact", "evidence_status": "supported",
                     "source_ids": ["S-001"]}],
            contradictions=[],
        )
        if with_prior_versions is not None:
            (base / "source_versions.jsonl").write_text(
                "\n".join(json.dumps(v) for v in with_prior_versions) + "\n", encoding="utf-8")
        if with_gate:
            verify_mod._write_quality_gate(base, verify_mod.verify(base))

    def test_recheck_offline_never_reports_unchanged(self):
        # THE most important assertion of this phase. --offline, fresh cache, a
        # source WITH a DOI: every row must be not_rechecked, none "unchanged".
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            self._bundle(base)
            diff = verify_mod.recheck(base, no_retrieve=True, cache_dir=str(base / "cache"))
        classes = [r["change_class"] for r in diff["source_changes"]]
        self.assertTrue(classes)
        self.assertTrue(all(c == "not_rechecked" for c in classes), classes)
        self.assertNotIn("unchanged", classes)

    def test_recheck_detects_new_retraction_and_downgrades_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            self._bundle(base, with_prior_versions=[_CLEAN_VERSION], with_gate=True)
            gate_before_status = verify_mod.verify(base)["status"]
            fetcher = _FakeFetcher(_RETRACTED_FETCHER)
            diff = verify_mod.recheck(base, fetcher=fetcher, cache_dir=str(base / "cache_new"))

        self.assertEqual(len(diff["source_changes"]), 1)
        self.assertEqual(diff["source_changes"][0]["change_class"], "retracted")
        weakened = [c for c in diff["claim_changes"] if c["direction"] == "weakened"]
        self.assertEqual([c["claim_id"] for c in weakened], ["C-001"])
        self.assertEqual(weakened[0]["source_ids"], ["S-001"])
        self.assertIn(diff["gate_after"]["status"], {"REVISE", "BLOCKED_PENDING_EVIDENCE"})
        self.assertNotEqual(diff["gate_after"]["status"], gate_before_status)
        self.assertTrue(diff["gate_changed"])
        # verify.py must NOT auto-rewrite the claim's evidence_status.
        self.assertEqual(weakened[0]["before_evidence_status"],
                         weakened[0]["after_evidence_status"])

    def test_recheck_unchanged_source_is_explicit_not_implicit(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            self._bundle(base, with_prior_versions=[_CLEAN_VERSION])
            fetcher = _FakeFetcher(_CLEAN_FETCHER)
            diff = verify_mod.recheck(base, fetcher=fetcher, cache_dir=str(base / "cache"))
        row = diff["source_changes"][0]
        self.assertEqual(row["change_class"], "unchanged")
        self.assertIn("as of this recheck", row["detail"])
        self.assertNotIn("permanent", row["detail"].lower())

    def test_recheck_source_with_no_identifier_is_not_rechecked(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            _write_run(
                base,
                sources=[{"source_id": "S-001", "title": "No identifier",
                          "url": "https://example.org/thing", "source_type": "gray"}],
                claims=[{"claim_id": "C-001", "perspective": "academic", "claim_text": "A.",
                         "claim_type": "fact", "evidence_status": "supported",
                         "source_ids": ["S-001"]}],
                contradictions=[],
            )
            diff = verify_mod.recheck(base, no_retrieve=True, cache_dir=str(base / "cache"))
        self.assertEqual(diff["source_changes"][0]["change_class"], "not_rechecked")

    def test_recheck_missing_prior_gate_computes_before_without_fabrication(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            self._bundle(base)  # no 06_quality_gate.json on disk
            self.assertFalse((base / "06_quality_gate.json").exists())
            diff = verify_mod.recheck(base, no_retrieve=True, cache_dir=str(base / "cache"))
            fresh_status = verify_mod.verify(base)["status"]
        self.assertIn("status", diff["gate_before"])
        # gate_before is a real deterministic verify() result, not a fabricated one.
        self.assertEqual(diff["gate_before"]["status"], fresh_status)

    def test_recheck_writes_source_versions_that_plain_verify_then_reads(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            self._bundle(base, with_prior_versions=[_CLEAN_VERSION], with_gate=True)
            fetcher = _FakeFetcher(_RETRACTED_FETCHER)
            verify_mod.recheck(base, fetcher=fetcher, cache_dir=str(base / "cache_new"))
            gate = verify_mod.verify(base)  # plain verify, reads refreshed source_versions.jsonl
        self.assertTrue(any("retracted source S-001" in m for m in gate["blocking_issues"]))

    def test_recheck_omits_tripwire_and_pivotal_keys_when_absent(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            self._bundle(base)
            diff = verify_mod.recheck(base, no_retrieve=True, cache_dir=str(base / "cache"))
        self.assertNotIn("tripwires_evaluated", diff)
        self.assertNotIn("pivotal_claims_touched", diff)

    def test_recheck_write_reseals_bundle(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            self._bundle(base, with_prior_versions=[_CLEAN_VERSION], with_gate=True)
            verify_mod.main([str(base), "--write"])  # seal-eligible gate exists

            class _Args:
                write, strict, offline = True, False, True
                as_of, cache = None, str(base / "cache")
            verify_mod._run_recheck(base, _Args())

            self.assertTrue((base / "refresh_diff.json").exists())
            self.assertTrue((base / "refresh_report.md").exists())
            rep = verify_mod.check_seal(base)
        # after re-seal the bundle is byte-consistent with its fresh manifest.
        self.assertTrue(rep["ok"], rep)

    def test_recheck_help_has_no_monitoring_language(self):
        import contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf), self.assertRaises(SystemExit):
            verify_mod.main(["--help"])
        text = buf.getvalue().lower()
        self.assertIn("--recheck", text)
        self.assertNotIn("monitoring", text)
        self.assertNotIn("live", text)


_DC_RULE = ("highest-strength option wins; ties broken by option order in options[]; "
            "strength order strong > conditional > moderate > weak > unsupported")


class DecisionCriticalityTest(unittest.TestCase):
    """07c: verify.py validates the *shape* and internal consistency of
    decision_criticality.json (all issues minor-only); it never re-derives the
    ranking. FLIP fixtures anchor the pivotal-vs-peripheral semantics."""

    def _base(self, tmp):
        base = Path(tmp)
        _write_run(
            base,
            claims=[
                {"claim_id": "C-001", "perspective": "economist",
                 "claim_text": "The targeted compact is the best-supported option.",
                 "claim_type": "recommendation", "evidence_status": "supported",
                 "source_ids": ["S-001"]},
                {"claim_id": "C-002", "perspective": "skeptic",
                 "claim_text": "A sector tax addresses a narrow distortion.",
                 "claim_type": "recommendation", "evidence_status": "supported",
                 "source_ids": ["S-002"]},
            ],
            sources=[
                {"source_id": "S-001", "title": "Transition compact study",
                 "url": "https://openalex.org/W1", "source_type": "peer_reviewed",
                 "source_class": "peer_reviewed", "full_text_status": "full_text"},
                {"source_id": "S-002", "title": "Sector tax study",
                 "url": "https://openalex.org/W2", "source_type": "peer_reviewed",
                 "source_class": "peer_reviewed", "full_text_status": "full_text"},
            ],
            contradictions=[],
            report={"options": [
                {"name": "C - Targeted transition compact", "strength": "strong"},
                {"name": "D - Narrow temporary tax", "strength": "moderate"},
            ]},
        )
        (base / "05_argument_map.mmd").write_text(
            "graph TD\n  Q[Question]\n"
            "  Q --> OPTC[C - Targeted transition compact]\n"
            "  Q --> OPTD[D - Narrow temporary tax]\n"
            "  OPTC --> CC001[C-001]\n"
            "  OPTD --> CC002[C-002]\n",
            encoding="utf-8")
        return base

    def _write_dc(self, base, doc):
        (base / "decision_criticality.json").write_text(
            json.dumps(doc), encoding="utf-8")

    def _crit_minors(self, gate):
        return [m for m in gate["minor_issues"] if "decision_criticality" in m]

    def test_pivotal_claim_flip_changes_option_ranking(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = self._base(tmp)
            self._write_dc(base, {
                "schema_version": 1,
                "options_considered": [
                    {"name": "C - Targeted transition compact", "strength": "strong"},
                    {"name": "D - Narrow temporary tax", "strength": "moderate"},
                ],
                "recommendation_rule": _DC_RULE,
                "rankings": [
                    {"claim_id": "C-001", "criticality": "pivotal",
                     "affects_options": ["C - Targeted transition compact"],
                     "flips_recommendation": True,
                     "rule_trace": "C-001 is option C's sole support; flipping it drops C "
                                   "below D, changing the winner."},
                    {"claim_id": "C-002", "criticality": "peripheral",
                     "affects_options": [], "flips_recommendation": False,
                     "rule_trace": "C-002 flip does not change the winner."},
                ],
                "most_load_bearing": "C-001",
            })
            gate = verify_mod.verify(base)
            self.assertEqual(self._crit_minors(gate), [])
            self.assertNotEqual(gate["status"], "BLOCKED_PENDING_EVIDENCE")

    def test_peripheral_claim_is_not_tagged_pivotal(self):
        # A negative-control ranking (peripheral, no flip) is well-formed.
        with tempfile.TemporaryDirectory() as tmp:
            base = self._base(tmp)
            self._write_dc(base, {
                "schema_version": 1,
                "options_considered": [{"name": "C - Targeted transition compact", "strength": "strong"}],
                "recommendation_rule": _DC_RULE,
                "rankings": [
                    {"claim_id": "C-002", "criticality": "peripheral",
                     "affects_options": [], "flips_recommendation": False,
                     "rule_trace": "no path to any option node."},
                ],
            })
            gate = verify_mod.verify(base)
            self.assertEqual(self._crit_minors(gate), [])

    def test_most_load_bearing_must_be_pivotal(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = self._base(tmp)
            self._write_dc(base, {
                "schema_version": 1,
                "options_considered": [{"name": "C - Targeted transition compact", "strength": "strong"}],
                "recommendation_rule": _DC_RULE,
                "rankings": [
                    {"claim_id": "C-001", "criticality": "contributing",
                     "affects_options": ["C - Targeted transition compact"],
                     "flips_recommendation": False, "rule_trace": "changes tier only."},
                ],
                "most_load_bearing": "C-001",
            })
            gate = verify_mod.verify(base)
            self.assertTrue(any("most_load_bearing" in m for m in gate["minor_issues"]))

    def test_pivotal_without_flips_recommendation_is_flagged(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = self._base(tmp)
            self._write_dc(base, {
                "schema_version": 1,
                "options_considered": [{"name": "C - Targeted transition compact", "strength": "strong"}],
                "recommendation_rule": _DC_RULE,
                "rankings": [
                    {"claim_id": "C-001", "criticality": "pivotal",
                     "affects_options": ["C - Targeted transition compact"],
                     "flips_recommendation": False, "rule_trace": "mislabeled."},
                ],
                "most_load_bearing": "C-001",
            })
            gate = verify_mod.verify(base)
            self.assertTrue(any("flips_recommendation" in m for m in gate["minor_issues"]))

    def test_numeric_importance_field_is_flagged(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = self._base(tmp)
            self._write_dc(base, {
                "schema_version": 1,
                "options_considered": [{"name": "C - Targeted transition compact", "strength": "strong"}],
                "recommendation_rule": _DC_RULE,
                "rankings": [
                    {"claim_id": "C-001", "criticality": "peripheral",
                     "affects_options": [], "flips_recommendation": False,
                     "importance": 0.9, "rule_trace": "x"},
                ],
            })
            gate = verify_mod.verify(base)
            self.assertTrue(any("importance" in m and "ordinal-only" in m
                                for m in gate["minor_issues"]))

    def test_absent_file_produces_no_new_issues(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = self._base(tmp)  # no decision_criticality.json written
            gate = verify_mod.verify(base)
            self.assertNotIn("decision_criticality", " ".join(gate["minor_issues"]))


class TripwireTest(unittest.TestCase):
    """08: decision_tripwires.json is optional, advisory-only, and must bind to
    real claims or option names before it counts as decision-relevant."""

    def _claim(self, cid="C-001"):
        return {"claim_id": cid, "perspective": "academic", "claim_text": "Claim.",
                "claim_type": "fact", "evidence_status": "supported",
                "source_ids": ["S-001"]}

    def _source(self, sid="S-001", doi="10.1145/3603269.3604857"):
        return {"source_id": sid, "title": "Source", "url": f"https://doi.org/{doi}",
                "doi": doi, "source_type": "peer_reviewed",
                "source_class": "peer_reviewed", "full_text_status": "full_text",
                "credibility_notes": "ok"}

    def _tripwire(self, **over):
        tw = {
            "id": "T-001",
            "condition": "A new source changes the claim.",
            "threshold_or_event": "Publisher metadata changes or a manual review finds contrary evidence.",
            "claim_ids": ["C-001"],
            "option": None,
            "direction": "weakens",
            "monitoring_source": "manual literature scan",
            "monitor_kind": "manual_watch",
            "refresh_cadence": "quarterly",
            "reversal_cost": "medium",
            "action": "Re-open the affected claim before relying on it.",
        }
        tw.update(over)
        return tw

    def _run(self, tmp, tripwires=None, *, claims=None, sources=None, report=None):
        base = Path(tmp)
        _write_run(
            base,
            claims=claims if claims is not None else [self._claim()],
            sources=sources if sources is not None else [self._source()],
            contradictions=[],
            report=report if report is not None else {"options": [{"name": "Option C"}]},
            tripwires=tripwires,
        )
        return verify_mod.verify(base)

    def _tripwire_minors(self, gate):
        return [m for m in gate["minor_issues"] if "tripwire" in m.lower() or "T-" in m]

    def test_tripwire_bound_to_real_claim_is_clean(self):
        with tempfile.TemporaryDirectory() as tmp:
            gate = self._run(tmp, [self._tripwire()])
            self.assertFalse(any("T-001" in m for m in self._tripwire_minors(gate)))

    def test_unbound_tripwire_raises_decorative_advisory(self):
        with tempfile.TemporaryDirectory() as tmp:
            gate = self._run(tmp, [self._tripwire(claim_ids=[], option=None)])
            self.assertTrue(any("T-001 is unbound" in m and "decorative" in m
                                for m in gate["minor_issues"]))

    def test_tripwire_with_unresolved_claim_id_is_flagged(self):
        with tempfile.TemporaryDirectory() as tmp:
            gate = self._run(tmp, [self._tripwire(claim_ids=["C-999"])])
            self.assertTrue(any("T-001 references missing claim C-999" in m
                                for m in gate["minor_issues"]))

    def test_tripwire_bound_to_option_name_is_clean(self):
        with tempfile.TemporaryDirectory() as tmp:
            gate = self._run(tmp, [self._tripwire(claim_ids=[], option="Option C")])
            self.assertFalse(any("unbound" in m for m in self._tripwire_minors(gate)))

    def test_tripwire_with_unresolved_option_is_flagged(self):
        with tempfile.TemporaryDirectory() as tmp:
            gate = self._run(tmp, [self._tripwire(option="Missing Option")])
            self.assertTrue(any("T-001 references missing option 'Missing Option'" in m
                                for m in gate["minor_issues"]))

    def test_invalid_direction_enum_is_flagged(self):
        with tempfile.TemporaryDirectory() as tmp:
            gate = self._run(tmp, [self._tripwire(direction="maybe")])
            self.assertTrue(any("T-001 has invalid/missing direction" in m
                                for m in gate["minor_issues"]))

    def test_invalid_reversal_cost_enum_is_flagged(self):
        with tempfile.TemporaryDirectory() as tmp:
            gate = self._run(tmp, [self._tripwire(reversal_cost="extreme")])
            self.assertTrue(any("T-001 has invalid/missing reversal_cost" in m
                                for m in gate["minor_issues"]))

    def test_auto_recheckable_with_resolvable_source_is_clean(self):
        with tempfile.TemporaryDirectory() as tmp:
            gate = self._run(tmp, [self._tripwire(
                monitor_kind="auto_recheckable", monitoring_source="S-001")])
            self.assertFalse(any("not actually auto-recheckable" in m
                                 for m in self._tripwire_minors(gate)))

    def test_auto_recheckable_with_doi_is_clean(self):
        with tempfile.TemporaryDirectory() as tmp:
            gate = self._run(tmp, [self._tripwire(
                monitor_kind="auto_recheckable",
                monitoring_source="https://doi.org/10.1145/3603269.3604857")])
            self.assertFalse(any("not actually auto-recheckable" in m
                                 for m in self._tripwire_minors(gate)))

    def test_auto_recheckable_with_unresolvable_source_is_flagged(self):
        with tempfile.TemporaryDirectory() as tmp:
            gate = self._run(tmp, [self._tripwire(
                monitor_kind="auto_recheckable",
                monitoring_source="next literature scan")])
            self.assertTrue(any("not actually auto-recheckable" in m
                                for m in gate["minor_issues"]))

    def test_absent_tripwires_file_produces_zero_new_issues(self):
        with tempfile.TemporaryDirectory() as tmp:
            gate = self._run(tmp)
            self.assertEqual(self._tripwire_minors(gate), [])

    def test_tripwires_never_affect_scores(self):
        with tempfile.TemporaryDirectory() as tmp_b, tempfile.TemporaryDirectory() as tmp_c:
            broken = self._run(tmp_b, [self._tripwire(
                id="bad", claim_ids=["C-999"], option="Missing Option",
                direction="maybe", reversal_cost="extreme",
                monitor_kind="auto_recheckable", monitoring_source="not resolvable")])
            clean = self._run(tmp_c, [self._tripwire()])
            keys = ("coverage_score", "traceability_score", "argument_support_score",
                    "contradiction_handling_score", "recommendation_support_score")
            self.assertEqual(broken["blocking_issues"], [])
            self.assertEqual(broken["major_issues"], clean["major_issues"])
            for key in keys:
                self.assertEqual(broken[key], clean[key], f"{key} moved")


class TripwireRecheckInterfaceTest(unittest.TestCase):
    def test_auto_recheckable_tripwire_monitoring_source_resolves_inside_bundle(self):
        source = {"source_id": "S-004", "doi": "10.1145/2486001.2486012"}
        tripwire = {"id": "T-001", "monitor_kind": "auto_recheckable",
                    "monitoring_source": "S-004"}
        source_ids = {source["source_id"]}
        self.assertIn(tripwire["monitoring_source"], source_ids)


class ResolutionPlanTest(unittest.TestCase):
    """07d: verify.py validates the *shape* and internal consistency of a
    contradiction's resolution_plan (all issues minor-only). It never gates the
    score, never derives resolution_status from status, and never computes VOI."""

    def _run(self, tmp, contradictions, *, dc=None, tripwires=None):
        base = Path(tmp)
        _write_run(
            base,
            claims=[{"claim_id": cid, "perspective": "academic", "claim_text": "c",
                     "claim_type": "inference", "evidence_status": "supported",
                     "source_ids": ["S-001"]}
                    for cid in ("C-001", "C-002", "C-003", "C-016")],
            sources=[{"source_id": "S-001", "title": "t", "url": "https://openalex.org/W1",
                      "source_type": "peer_reviewed", "source_class": "peer_reviewed",
                      "full_text_status": "full_text"}],
            contradictions=contradictions,
            report={"options": [{"name": "A", "strength": "strong"}]},
        )
        if dc is not None:
            (base / "decision_criticality.json").write_text(json.dumps(dc), encoding="utf-8")
        if tripwires is not None:
            (base / "decision_tripwires.json").write_text(json.dumps(tripwires), encoding="utf-8")
        return verify_mod.verify(base)

    def _plan(self, **over):
        p = dict(evidence_type_needed="head_to_head_benchmark",
                 proposed_experiment_or_source="Run the benchmark.",
                 approx_effort="medium", decision_impact="might_flip",
                 linked_claims=["C-001"], status="proposed")
        p.update(over)
        return p

    def _cx(self, **over):
        x = dict(id="X-001", claim_ids=["C-001", "C-016"], resolution_status="unresolved")
        x.update(over)
        return x

    def _plan_minors(self, gate):
        return [m for m in gate["minor_issues"] if "resolution_plan" in m]

    def test_resolution_plan_absent_is_silent(self):
        # A record without a resolution_plan that is NOT open produces none of the
        # new minors — additive/optional: absence ⇒ current behavior.
        with tempfile.TemporaryDirectory() as tmp:
            gate = self._run(tmp, [self._cx(
                resolution_status="partially_resolved",
                resolution={"basis": "evidence", "evidence_ids": ["E-001"],
                            "rationale": "narrowed by benchmark"})])
            self.assertEqual(self._plan_minors(gate), [])

    def test_resolution_plan_invalid_enum_is_minor(self):
        with tempfile.TemporaryDirectory() as tmp:
            gate = self._run(tmp, [self._cx(resolution_plan=self._plan(
                approx_effort="huge", decision_impact="definitely"))])
            minors = gate["minor_issues"]
            self.assertTrue(any("approx_effort" in m for m in minors))
            self.assertTrue(any("decision_impact" in m for m in minors))
            self.assertEqual(gate["blocking_issues"], [])
            self.assertFalse(any("resolution_plan" in m for m in gate["major_issues"]))

    def test_resolution_plan_missing_evidence_type_is_minor(self):
        with tempfile.TemporaryDirectory() as tmp:
            gate = self._run(tmp, [self._cx(resolution_plan=self._plan(evidence_type_needed=""))])
            self.assertTrue(any("missing evidence_type_needed" in m for m in gate["minor_issues"]))

    def test_resolution_plan_no_experiment_or_source_is_minor(self):
        with tempfile.TemporaryDirectory() as tmp:
            gate = self._run(tmp, [self._cx(resolution_plan=self._plan(
                proposed_experiment_or_source="", data_source=""))])
            self.assertTrue(any("names no proposed experiment or data source" in m
                                for m in gate["minor_issues"]))

    def test_resolution_plan_linked_claims_must_resolve(self):
        with tempfile.TemporaryDirectory() as tmp:
            gate = self._run(tmp, [self._cx(resolution_plan=self._plan(linked_claims=["C-999"]))])
            self.assertTrue(any("linked_claims references missing claim C-999" in m
                                for m in gate["minor_issues"]))

    def test_resolution_plan_linked_tripwires_skipped_without_08_artifact(self):
        with tempfile.TemporaryDirectory() as tmp:
            gate = self._run(tmp, [self._cx(resolution_plan=self._plan(linked_tripwires=["T-001"]))])
            self.assertFalse(any("linked_tripwires" in m for m in gate["minor_issues"]))

    def test_resolution_plan_linked_tripwires_must_resolve_when_08_present(self):
        with tempfile.TemporaryDirectory() as tmp:
            gate = self._run(
                tmp,
                [self._cx(resolution_plan=self._plan(linked_tripwires=["T-001"]))],
                tripwires={"tripwires": [{"id": "T-002", "monitoring_source": "S-001"}]})
            self.assertTrue(any("linked_tripwires references missing tripwire T-001" in m
                                for m in gate["minor_issues"]))

    def test_resolution_plan_would_flip_consistent_with_pivotal_07c(self):
        with tempfile.TemporaryDirectory() as tmp:
            gate = self._run(
                tmp,
                [self._cx(resolution_plan=self._plan(
                    linked_claims=["C-016"], decision_impact="would_flip"))],
                dc={"rankings": [{"claim_id": "C-016", "criticality": "pivotal",
                                  "flips_recommendation": True, "rule_trace": "x"}]})
            self.assertFalse(any("would_flip but none of its linked claims are ranked pivotal" in m
                                 for m in gate["minor_issues"]))

    def test_resolution_plan_would_flip_inconsistent_with_07c_is_minor(self):
        with tempfile.TemporaryDirectory() as tmp:
            gate = self._run(
                tmp,
                [self._cx(resolution_plan=self._plan(
                    linked_claims=["C-001"], decision_impact="would_flip"))],
                dc={"rankings": [{"claim_id": "C-016", "criticality": "pivotal",
                                  "flips_recommendation": True, "rule_trace": "x"},
                                 {"claim_id": "C-001", "criticality": "peripheral",
                                  "flips_recommendation": False}]})
            self.assertTrue(any("would_flip but none of its linked claims are ranked pivotal" in m
                                for m in gate["minor_issues"]))

    def test_resolution_plan_missing_on_would_flip_unresolved_is_minor(self):
        with tempfile.TemporaryDirectory() as tmp:
            gate = self._run(tmp, [self._cx()])  # unresolved, no resolution_plan
            self.assertTrue(any("is unresolved but has no resolution_plan" in m
                                for m in gate["minor_issues"]))

    def test_resolution_plan_rejects_evsi_numeric_field(self):
        with tempfile.TemporaryDirectory() as tmp:
            gate = self._run(tmp, [self._cx(resolution_plan=self._plan(evsi=0.42))])
            self.assertTrue(any("VOI field (evsi)" in m for m in gate["minor_issues"]))
        # A numeric decision_impact trips BOTH the VOI rejection and the enum check.
        with tempfile.TemporaryDirectory() as tmp:
            gate = self._run(tmp, [self._cx(resolution_plan=self._plan(decision_impact=0.8))])
            minors = gate["minor_issues"]
            self.assertTrue(any("VOI field (decision_impact)" in m for m in minors))
            self.assertTrue(any("decision_impact is missing or invalid" in m for m in minors))

    def test_resolution_plan_never_moves_verdict_or_scores(self):
        broken = self._plan(approx_effort="huge", decision_impact="definitely",
                            evidence_type_needed="", proposed_experiment_or_source="",
                            data_source="", linked_claims=["C-999"], evsi=0.42,
                            probability=0.3)
        clean = self._plan()
        keys = ("status", "blocking_issues", "coverage_score", "traceability_score",
                "argument_support_score",
                "contradiction_handling_score", "recommendation_support_score")
        with tempfile.TemporaryDirectory() as tmp_b, tempfile.TemporaryDirectory() as tmp_c:
            gb = self._run(tmp_b, [self._cx(resolution_plan=broken)])
            gc = self._run(tmp_c, [self._cx(resolution_plan=clean)])
            self.assertEqual(gb["blocking_issues"], [])
            for k in keys:
                self.assertEqual(gb[k], gc[k], f"{k} moved between broken and clean plan")


class WorkflowHonestyAdvisoryTest(unittest.TestCase):
    """Phase B2 — full-text-over-snippet, templated verdicts, recommendation
    overreach, and thin-retrieval advisories. All must be MINOR only."""

    def test_full_text_over_snippet_flags_short_full_text_packet(self):
        short = {"packet_id": "P-001", "source_access": "full_text",
                 "quoted_passage": "A two-sentence snippet, far under the threshold."}
        long_ok = {"packet_id": "P-002", "source_access": "full_text",
                   "quoted_passage": "x" * (verify_mod._FULL_TEXT_MIN_CHARS + 1)}
        abstract = {"packet_id": "P-003", "source_access": "abstract_only",
                    "quoted_passage": "short abstract excerpt"}
        issues = verify_mod._full_text_over_snippet_issues([short, long_ok, abstract])
        self.assertEqual(len(issues), 1)
        self.assertIn("P-001", issues[0])
        self.assertNotIn("P-002", issues[0])
        self.assertNotIn("P-003", issues[0])

    def test_full_text_over_snippet_empty_when_none(self):
        self.assertEqual(verify_mod._full_text_over_snippet_issues([]), [])

    def test_templated_verdict_flags_id_varying_rationales(self):
        verdicts = [
            {"rationale": "Packet P-1 supports the narrowed claim scope for C-1."},
            {"rationale": "Packet P-2 supports the narrowed claim scope for C-2."},
            {"rationale": "Packet P-3 supports the narrowed claim scope for C-3."},
        ]
        issue = verify_mod._templated_verdict_issue(verdicts, identical_max_repeat=1)
        self.assertIsNotNone(issue)
        self.assertIn("templated", issue.lower())

    def test_templated_verdict_defers_to_identical_check(self):
        verdicts = [{"rationale": "same"}] * 3
        # identical check already fired (>=3) → templated advisory stays silent.
        self.assertIsNone(verify_mod._templated_verdict_issue(verdicts, identical_max_repeat=3))

    def test_recommendation_overreach_flags_self_marked_claim(self):
        claims = [
            {"claim_id": "C-010", "claim_type": "recommendation",
             "content_verification": {"status": "direct_support"},
             "limitations": "This is the brief's recommendation, not quoted from a source."},
            {"claim_id": "C-011", "claim_type": "recommendation",
             "content_verification": {"status": "direct_support"},
             "limitations": "Bounded to simulation results."},
            {"claim_id": "C-012", "claim_type": "fact",
             "content_verification": {"status": "direct_support"},
             "limitations": "not quoted"},
        ]
        issues = verify_mod._recommendation_overreach_issues(claims)
        self.assertEqual(len(issues), 1)
        self.assertIn("C-010", issues[0])
        self.assertNotIn("C-011", issues[0])
        self.assertNotIn("C-012", issues[0])  # fact, not recommendation

    def _write_log(self, base: Path, rows):
        (base / "retrieval_log.jsonl").write_text(
            "\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")

    def test_retrieval_coverage_flags_rate_limit(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            self._write_log(base, [
                {"offline": False, "error": None},
                {"offline": False, "error": "HTTP Error 429: Too Many Requests"},
            ])
            partial, msg = verify_mod._retrieval_coverage(base)
            self.assertTrue(partial)
            self.assertIn("rate-limited", msg)

    def test_retrieval_coverage_flags_thin_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            self._write_log(base, [
                {"offline": False, "error": None},
                {"offline": False, "error": "connection reset"},
                {"offline": False, "error": "timeout"},
            ])
            partial, msg = verify_mod._retrieval_coverage(base)
            self.assertTrue(partial)
            self.assertIn("thin", msg)

    def test_retrieval_coverage_healthy_is_not_partial(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            self._write_log(base, [
                {"offline": False, "error": None},
                {"offline": False, "error": None},
                {"offline": False, "error": "timeout"},
            ])
            partial, msg = verify_mod._retrieval_coverage(base)
            self.assertFalse(partial)
            self.assertIsNone(msg)

    def test_retrieval_coverage_absent_log_is_not_partial(self):
        with tempfile.TemporaryDirectory() as tmp:
            partial, msg = verify_mod._retrieval_coverage(Path(tmp))
            self.assertFalse(partial)
            self.assertIsNone(msg)

    def test_verify_exposes_retrieval_partial_field(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            _write_run(
                base,
                claims=[{"claim_id": "C-001", "perspective": "academic",
                         "claim_text": "Solvers are mature.", "claim_type": "fact",
                         "evidence_status": "supported", "source_ids": ["S-001"]}],
                sources=[{"source_id": "S-001", "title": "OR-Tools",
                          "url": "https://developers.google.com/optimization",
                          "source_type": "industry", "credibility_notes": "Official"}],
                contradictions=[],
            )
            self._write_log(base, [{"offline": False, "error": "HTTP 429 rate limit"}])
            gate = verify_mod.verify(base)
            self.assertTrue(gate["retrieval_partial"])
            self.assertTrue(any("rate-limited" in m for m in gate["minor_issues"]))

    def test_advisories_stay_minor_on_committed_example(self):
        # The committed example has no retrieval_log / support packets, so the new
        # advisories must not change its verdict or emit a partial-retrieval flag.
        gate = verify_mod.verify(ROOT / "examples" / "network_flow_rl")
        self.assertEqual(gate["status"], "PASS_WITH_CAVEATS")
        self.assertEqual(gate["blocking_issues"], [])
        self.assertFalse(gate["retrieval_partial"])


if __name__ == "__main__":
    unittest.main()
