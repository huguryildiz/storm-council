import csv
import importlib.util
import io
import json
import os
import tempfile
import unittest
from unittest import mock
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures" / "metadata"

SPEC = importlib.util.spec_from_file_location(
    "metadata_adapters", ROOT / "scripts" / "metadata_adapters.py"
)
metadata_adapters = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(metadata_adapters)

VERIFY_SPEC = importlib.util.spec_from_file_location("verify", ROOT / "scripts" / "verify.py")
verify_mod = importlib.util.module_from_spec(VERIFY_SPEC)
VERIFY_SPEC.loader.exec_module(verify_mod)

RENDER_SPEC = importlib.util.spec_from_file_location(
    "render_report", ROOT / "scripts" / "render_report.py"
)
render_report = importlib.util.module_from_spec(RENDER_SPEC)
RENDER_SPEC.loader.exec_module(render_report)


class FakeFetcher:
    def __init__(self, mapping):
        self.mapping = mapping
        self.calls = []

    def __call__(self, url, headers=None, timeout=20):
        self.calls.append({"url": url, "headers": headers or {}})
        for key, fixture in self.mapping.items():
            if key in url:
                if fixture is None:
                    raise OSError("offline or 404")
                return (FIXTURES / fixture).read_text(encoding="utf-8").encode("utf-8")
        raise OSError("unexpected URL: " + url)


def _write_sources(base, rows):
    cols = [
        "source_id", "title", "url", "publisher", "publication_date",
        "source_type", "accessed_at", "credibility_notes", "relevance_notes",
        "doi", "full_text_status", "publication_status",
    ]
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=cols)
    writer.writeheader()
    for row in rows:
        writer.writerow({k: row.get(k, "") for k in cols})
    (base / "03_source_registry.csv").write_text(buf.getvalue(), encoding="utf-8")


def _read_jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


class MetadataAdapterTest(unittest.TestCase):
    def test_load_env_file_reads_semantic_scholar_key_without_dotenv_dependency(self):
        with tempfile.TemporaryDirectory() as tmp:
            env_path = Path(tmp) / ".env"
            env_path.write_text(
                "# local secrets\n"
                "SEMANTIC_SCHOLAR_API_KEY=s2k-test-key\n"
                "IGNORED_LINE\n",
                encoding="utf-8",
            )

            loaded = metadata_adapters._load_env_file(env_path)

        self.assertEqual(loaded["SEMANTIC_SCHOLAR_API_KEY"], "s2k-test-key")

    def test_semantic_scholar_discovery_uses_api_key_header_from_environment(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache = metadata_adapters.MetadataCache(Path(tmp))
            fetcher = FakeFetcher({
                "semanticscholar.org/graph/v1/paper/DOI:10.5555%2Fexample.duplicate": "semantic_scholar_duplicate.json",
            })

            with mock.patch.dict(os.environ, {"SEMANTIC_SCHOLAR_API_KEY": "s2k-test-key"}):
                metadata_adapters.semantic_scholar_discovery(
                    "DOI:10.5555/example.duplicate",
                    cache,
                    fetcher=fetcher,
                )

        self.assertEqual(fetcher.calls[0]["headers"].get("x-api-key"), "s2k-test-key")

    def test_cache_returns_second_response_without_fetcher_call(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache = metadata_adapters.MetadataCache(Path(tmp))
            fetcher = FakeFetcher({"works/10.5555%2Fexample.duplicate": "crossref_duplicate.json"})

            first = metadata_adapters.cached_json(
                "https://api.crossref.org/works/10.5555%2Fexample.duplicate",
                cache,
                fetcher,
                "crossref",
            )
            second = metadata_adapters.cached_json(
                "https://api.crossref.org/works/10.5555%2Fexample.duplicate",
                cache,
                fetcher,
                "crossref",
            )

        self.assertEqual(first["data"]["message"]["DOI"], "10.5555/Example.Duplicate")
        self.assertEqual(second["data"]["message"]["DOI"], "10.5555/Example.Duplicate")
        self.assertFalse(first["cache_hit"])
        self.assertTrue(second["cache_hit"])
        self.assertEqual(len(fetcher.calls), 1)

    def test_crossref_and_openalex_parse_publication_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            _write_sources(base, [{
                "source_id": "S-001",
                "title": "A Duplicate Metadata Adapter Paper",
                "doi": "https://doi.org/10.5555/Example.Duplicate",
                "url": "https://publisher.example/paper",
                "source_type": "peer_reviewed",
            }])
            fetcher = FakeFetcher({
                "doi.org/10.5555/example.duplicate": "crossref_duplicate.json",
                "crossref.org/works/10.5555%2Fexample.duplicate": "crossref_duplicate.json",
                "openalex.org/works/doi:10.5555%2Fexample.duplicate": "openalex_duplicate.json",
                "semanticscholar.org/graph/v1/paper/DOI:10.5555%2Fexample.duplicate": "semantic_scholar_duplicate.json",
            })

            result = metadata_adapters.verify_publication_identity(base, fetcher=fetcher)

        record = result["source_versions"][0]
        self.assertEqual(record["identifiers"]["doi_normalized"], "10.5555/example.duplicate")
        self.assertEqual(record["identifiers"]["openalex_id"], "https://openalex.org/W123456789")
        self.assertEqual(record["identifiers"]["semantic_scholar_id"], "SS-DUPLICATE")
        self.assertEqual(record["publication_identity"]["status"], "PUBLISHED_VERIFIED")
        self.assertEqual(record["publication_identity"]["version"], "publisher_version")
        self.assertEqual(record["publication_identity"]["retraction_status"], "not_retracted")
        self.assertIn("crossref", record["publication_identity"]["metadata_sources_checked"])
        self.assertIn("openalex", record["publication_identity"]["metadata_sources_checked"])

    def test_retraction_correction_and_supersession_flags_are_parsed(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            _write_sources(base, [
                {"source_id": "S-001", "title": "Retracted", "doi": "10.5555/retracted.paper"},
                {"source_id": "S-002", "title": "Corrected", "doi": "10.5555/corrected.paper"},
                {"source_id": "S-003", "title": "Preprint", "doi": "10.5555/preprint.paper"},
            ])
            fetcher = FakeFetcher({
                "10.5555%2Fretracted.paper": "crossref_retracted.json",
                "doi.org/10.5555/retracted.paper": "crossref_retracted.json",
                "openalex.org/works/doi:10.5555%2Fretracted.paper": "openalex_retracted.json",
                "10.5555%2Fcorrected.paper": "crossref_corrected.json",
                "doi.org/10.5555/corrected.paper": "crossref_corrected.json",
                "10.5555%2Fpreprint.paper": "crossref_superseded_preprint.json",
                "doi.org/10.5555/preprint.paper": "crossref_superseded_preprint.json",
            })

            result = metadata_adapters.verify_publication_identity(base, fetcher=fetcher)

        by_id = {row["source_id"]: row for row in result["source_versions"]}
        self.assertTrue(by_id["S-001"]["flags"]["retracted"])
        self.assertEqual(by_id["S-001"]["publication_identity"]["status"], "RETRACTED")
        self.assertTrue(by_id["S-002"]["flags"]["corrected"])
        self.assertEqual(by_id["S-002"]["publication_identity"]["correction_status"], "corrected")
        self.assertTrue(by_id["S-003"]["flags"]["superseded"])
        self.assertEqual(by_id["S-003"]["publication_identity"]["superseded_by"], "10.5555/published.paper")

    def test_semantic_scholar_only_never_verifies_publication_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            _write_sources(base, [{
                "source_id": "S-001",
                "title": "Semantic Scholar Discovery Only",
                "url": "https://www.semanticscholar.org/paper/SS-ONLY",
            }])
            fetcher = FakeFetcher({
                "semanticscholar.org/graph/v1/paper/SS-ONLY": "semantic_scholar_only.json",
            })

            result = metadata_adapters.verify_publication_identity(base, fetcher=fetcher)

        record = result["source_versions"][0]
        self.assertEqual(record["identifiers"]["semantic_scholar_id"], "SS-ONLY")
        self.assertIn(record["publication_identity"]["status"], {"METADATA_PARTIAL", "UNRESOLVED"})
        self.assertNotEqual(record["publication_identity"]["status"], "PUBLISHED_VERIFIED")

    def test_duplicate_versions_collapse_to_one_canonical_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            _write_sources(base, [
                {"source_id": "S-001", "title": "Publisher", "doi": "10.5555/example.duplicate"},
                {"source_id": "S-002", "title": "arXiv mirror", "doi": "https://doi.org/10.5555/Example.Duplicate"},
                {"source_id": "S-003", "title": "Semantic Scholar", "url": "https://www.semanticscholar.org/paper/SS-DUPLICATE"},
            ])
            fetcher = FakeFetcher({
                "10.5555%2Fexample.duplicate": "crossref_duplicate.json",
                "doi.org/10.5555/example.duplicate": "crossref_duplicate.json",
                "SS-DUPLICATE": "semantic_scholar_duplicate.json",
            })

            result = metadata_adapters.verify_publication_identity(base, fetcher=fetcher)

        by_id = {row["source_id"]: row for row in result["source_versions"]}
        self.assertEqual(by_id["S-001"]["canonical_source_id"], "S-001")
        self.assertEqual(by_id["S-002"]["duplicate_of"], "S-001")
        self.assertEqual(by_id["S-003"]["duplicate_of"], "S-001")
        self.assertTrue(by_id["S-002"]["flags"]["duplicate_version"])
        self.assertTrue(by_id["S-003"]["flags"]["duplicate_version"])

    def test_writes_three_artifacts_with_documented_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            _write_sources(base, [{"source_id": "S-001", "title": "Unresolved", "doi": "10.5555/missing.paper"}])
            fetcher = FakeFetcher({
                "10.5555%2Fmissing.paper": None,
                "doi.org/10.5555/missing.paper": None,
            })

            metadata_adapters.verify_publication_identity(base, fetcher=fetcher)
            metadata_rows = _read_jsonl(base / "metadata_verification.jsonl")
            version_rows = _read_jsonl(base / "source_versions.jsonl")
            log_rows = _read_jsonl(base / "retrieval_log.jsonl")

        self.assertEqual(len(metadata_rows), 1)
        self.assertIn("source_id", metadata_rows[0])
        self.assertIn("checked", metadata_rows[0])
        self.assertIn("result", metadata_rows[0])
        self.assertIn("canonical_source_id", version_rows[0])
        self.assertIn("publication_identity", version_rows[0])
        self.assertIn("flags", version_rows[0])
        self.assertTrue({"request_id", "adapter", "url", "cache_hit", "offline"}.issubset(log_rows[0]))


class MetadataArtifactConsumerTest(unittest.TestCase):
    def test_verify_consumes_source_versions_retraction_and_supersession_flags(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            _write_sources(base, [
                {"source_id": "S-001", "title": "Retracted", "url": "https://publisher.example/retracted"},
                {"source_id": "S-002", "title": "Superseded", "url": "https://publisher.example/preprint"},
            ])
            (base / "03_claims.jsonl").write_text(
                json.dumps({"claim_id": "C-001", "perspective": "academic", "claim_text": "A.",
                            "claim_type": "fact", "evidence_status": "supported",
                            "source_ids": ["S-001"]}) + "\n" +
                json.dumps({"claim_id": "C-002", "perspective": "academic", "claim_text": "B.",
                            "claim_type": "fact", "evidence_status": "supported",
                            "source_ids": ["S-002"]}) + "\n",
                encoding="utf-8",
            )
            (base / "04_contradictions.json").write_text("[]", encoding="utf-8")
            (base / "source_versions.jsonl").write_text(
                json.dumps({"source_id": "S-001", "canonical_source_id": "S-001",
                            "duplicate_of": None,
                            "publication_identity": {"status": "RETRACTED", "retraction_status": "retracted"},
                            "flags": {"retracted": True}}) + "\n" +
                json.dumps({"source_id": "S-002", "canonical_source_id": "S-002",
                            "duplicate_of": None,
                            "publication_identity": {"status": "SUPERSEDED", "superseded_by": "S-009"},
                            "flags": {"superseded": True}}) + "\n",
                encoding="utf-8",
            )

            gate = verify_mod.verify(base)

        self.assertTrue(any("retracted source S-001" in m for m in gate["blocking_issues"]))
        self.assertTrue(any("superseded source S-002" in m for m in gate["major_issues"]))

    def test_verify_does_not_invent_flags_when_source_versions_absent(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            _write_sources(base, [{"source_id": "S-001", "title": "Plain", "url": "https://publisher.example/plain"}])
            (base / "03_claims.jsonl").write_text(
                json.dumps({"claim_id": "C-001", "perspective": "academic", "claim_text": "A.",
                            "claim_type": "fact", "evidence_status": "supported",
                            "source_ids": ["S-001"]}) + "\n",
                encoding="utf-8",
            )
            (base / "04_contradictions.json").write_text("[]", encoding="utf-8")

            gate = verify_mod.verify(base)

        self.assertFalse(any("retracted" in m.lower() for m in gate["blocking_issues"]))
        self.assertFalse(any("superseded" in m.lower() for m in gate["major_issues"]))

    def test_render_report_folds_source_versions_into_source_badges(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            (base / "source_versions.jsonl").write_text(
                json.dumps({"source_id": "S-001", "canonical_source_id": "S-001",
                            "publication_identity": {"status": "RETRACTED", "retraction_status": "retracted"},
                            "flags": {"retracted": True}}) + "\n",
                encoding="utf-8",
            )
            data = {
                "title": "A decision",
                "sources": [{"id": "S-001", "title": "Retracted Paper", "type": "peer_reviewed"}],
                "evidence": [{"evidence_id": "E-001", "source_id": "S-001", "evidence_excerpt": "x"}],
            }

            render_report._fold_in_artifacts(data, base)
            html = render_report.build(data)

        self.assertIn("retracted", html)
        self.assertEqual(data["sources"][0]["publication_identity"]["status"], "RETRACTED")

    def test_render_report_states_unresolved_identity_when_no_adapter_artifact_exists(self):
        html = render_report.build({
            "title": "A decision",
            "sources": [{"id": "S-001", "title": "Paper Without Adapter Run", "type": "peer_reviewed"}],
        })

        self.assertIn("UNRESOLVED", html)


if __name__ == "__main__":
    unittest.main()
