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


CONTENT_FIXTURES = {
    "wrong-paper/wrong-claim": "does_not_entail",
    "correct-topic/wrong-metric": "overclaimed",
    "simulation-to-deployment": "overclaimed",
    "association-to-causation": "overclaimed",
}


def _write_run(base: Path, *, claims, evidence, sources, verdicts=None):
    (base / "03_claims.jsonl").write_text(
        "\n".join(json.dumps(c) for c in claims) + "\n", encoding="utf-8")
    (base / "03_evidence.jsonl").write_text(
        "\n".join(json.dumps(e) for e in evidence) + "\n", encoding="utf-8")
    if verdicts is not None:
        (base / "03_evidence_verdicts.jsonl").write_text(
            "\n".join(json.dumps(v) for v in verdicts) + "\n", encoding="utf-8")
    buf = io.StringIO()
    cols = ["source_id", "title", "url", "publisher", "publication_date",
            "source_type", "accessed_at", "credibility_notes", "relevance_notes",
            "doi", "full_text_status", "publication_status"]
    w = csv.DictWriter(buf, fieldnames=cols)
    w.writeheader()
    for s in sources:
        w.writerow({k: s.get(k, "") for k in cols})
    (base / "03_source_registry.csv").write_text(buf.getvalue(), encoding="utf-8")
    (base / "04_contradictions.json").write_text("[]", encoding="utf-8")


class ContentVerificationFixtureTest(unittest.TestCase):
    def test_verdict_template_matches_required_field_list(self):
        template = json.loads(
            (ROOT / "skills/storm-council/templates/evidence_verdict.json").read_text(encoding="utf-8")
        )
        legacy_required = {
            "claim_id", "evidence_id", "judged_claim", "verdict",
            "scope_preserved", "rationale", "human_review_required",
        }
        v2_required = legacy_required | {
            "packet_id", "claim_atoms", "entailed_atoms", "unsupported_atoms",
            "judge_type", "judge_prompt_version",
        }
        self.assertEqual(set(template), v2_required)

        fixture = verify_mod._read_jsonl(
            ROOT / "tests/fixtures/content/wrong-paper/wrong-claim/03_evidence_verdicts.jsonl"
        )[0]
        self.assertTrue(legacy_required <= set(fixture))
        self.assertIn(fixture["verdict"], verify_mod._VERDICT_VALUES)
        self.assertIn(fixture["scope_preserved"], verify_mod._SCOPE_VERDICT_VALUES)
        self.assertIsInstance(fixture["human_review_required"], bool)

    def test_prompt_enumerates_verify_enums(self):
        prompt = (ROOT / "skills/storm-council/prompts/stage_content_verification.md").read_text(
            encoding="utf-8"
        )
        for verdict in verify_mod._VERDICT_VALUES:
            self.assertIn(verdict, prompt)
        for scope in verify_mod._SCOPE_VERDICT_VALUES:
            self.assertIn(scope, prompt)
        self.assertIn("uncertain is a first-class, non-fatal verdict", prompt)

    def test_adversarial_content_fixtures_never_pass_silently(self):
        for rel_path, expected_text in CONTENT_FIXTURES.items():
            with self.subTest(rel_path=rel_path):
                gate = verify_mod.verify(ROOT / "tests/fixtures/content" / rel_path)
                all_issues = "\n".join(
                    gate["blocking_issues"] + gate["major_issues"] + gate["minor_issues"]
                )
                self.assertNotEqual(gate["status"], "PASS")
                self.assertIn(expected_text, all_issues)

    def test_missing_verdict_on_located_direct_support_cannot_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            _write_run(
                base,
                claims=[{
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
                }],
                evidence=[{
                    "evidence_id": "E-001",
                    "source_id": "S-001",
                    "locator": {"table": "Table 1"},
                    "evidence_excerpt": "Method X reports a higher score than baseline Y on Benchmark Z.",
                }],
                sources=[{
                    "source_id": "S-001",
                    "title": "Benchmark Paper",
                    "url": "https://doi.org/10.5555/benchmark.paper",
                    "source_type": "peer_reviewed",
                    "doi": "10.5555/benchmark.paper",
                }],
                verdicts=None,
            )
            gate = verify_mod.verify(base)
            self.assertNotEqual(gate["status"], "PASS")
            self.assertTrue(any("no entailment verdict" in m for m in gate["major_issues"]))

    def test_uncertain_verdict_is_nonfatal_downgrade(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            _write_run(
                base,
                claims=[{
                    "claim_id": "C-001",
                    "perspective": "academic",
                    "claim_text": "Method X outperforms baseline Y on Benchmark Z.",
                    "claim_type": "fact",
                    "claim_strength": "comparative",
                    "confidence": 0.65,
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
                }],
                evidence=[{
                    "evidence_id": "E-001",
                    "source_id": "S-001",
                    "locator": {"section": "4.2"},
                    "evidence_excerpt": "The result table is ambiguous in the available excerpt.",
                }],
                sources=[{
                    "source_id": "S-001",
                    "title": "Ambiguous Benchmark Paper",
                    "url": "https://doi.org/10.5555/ambiguous.paper",
                    "source_type": "peer_reviewed",
                    "doi": "10.5555/ambiguous.paper",
                }],
                verdicts=[{
                    "claim_id": "C-001",
                    "evidence_id": "E-001",
                    "judged_claim": "Method X outperforms baseline Y on Benchmark Z.",
                    "verdict": "uncertain",
                    "scope_preserved": "uncertain",
                    "rationale": "The excerpt is too ambiguous to judge the comparison.",
                    "human_review_required": True,
                }],
            )
            gate = verify_mod.verify(base)
            self.assertEqual(gate["blocking_issues"], [])
            self.assertNotEqual(gate["status"], "PASS")
            self.assertTrue(any("uncertain" in m for m in gate["major_issues"]))


if __name__ == "__main__":
    unittest.main()
