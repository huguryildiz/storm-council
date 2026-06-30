import csv
import importlib.util
import io
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures" / "domain"

SPEC = importlib.util.spec_from_file_location(
    "metadata_adapters", ROOT / "scripts" / "metadata_adapters.py"
)
metadata_adapters = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(metadata_adapters)

VERIFY_SPEC = importlib.util.spec_from_file_location("verify", ROOT / "scripts" / "verify.py")
verify_mod = importlib.util.module_from_spec(VERIFY_SPEC)
VERIFY_SPEC.loader.exec_module(verify_mod)


class FakeFetcher:
    def __init__(self, mapping):
        self.mapping = mapping
        self.calls = []

    def __call__(self, url, headers=None, timeout=20):
        self.calls.append(url)
        for key, fixture in self.mapping.items():
            if key in url:
                return (FIXTURES / fixture).read_text(encoding="utf-8").encode("utf-8")
        raise OSError("unexpected URL: " + url)


def _write_sources(base, rows):
    cols = [
        "source_id", "title", "url", "publisher", "publication_date",
        "source_type", "accessed_at", "credibility_notes", "relevance_notes",
        "doi", "arxiv_id", "pmid", "pmcid", "full_text_status", "publication_status",
    ]
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=cols)
    writer.writeheader()
    for row in rows:
        writer.writerow({k: row.get(k, "") for k in cols})
    (base / "03_source_registry.csv").write_text(buf.getvalue(), encoding="utf-8")


def _read_jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


class DomainAdapterTest(unittest.TestCase):
    def test_arxiv_published_doi_sets_superseded_identity_and_records_version(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            _write_sources(base, [{
                "source_id": "S-001",
                "title": "arXiv source",
                "source_type": "preprint",
                "arxiv_id": "2401.00001",
            }])
            fetcher = FakeFetcher({"export.arxiv.org/api/query?id_list=2401.00001": "arxiv_published_doi.xml"})

            result = metadata_adapters.verify_publication_identity(base, fetcher=fetcher)

        record = result["source_versions"][0]
        self.assertEqual(record["identifiers"]["arxiv_id"], "2401.00001v2")
        self.assertEqual(record["identifiers"]["doi_normalized"], "10.1000/j.journal.2024.01.001")
        self.assertTrue(record["flags"]["superseded"])
        self.assertEqual(record["publication_identity"]["status"], "SUPERSEDED")
        self.assertEqual(record["publication_identity"]["version"], "preprint")
        self.assertEqual(record["publication_identity"]["superseded_by"], "10.1000/j.journal.2024.01.001")
        self.assertEqual(record["publication_identity"]["related_versions"][0]["version"], "v2")

    def test_arxiv_preprint_only_stays_preprint_verified(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            _write_sources(base, [{
                "source_id": "S-001",
                "title": "arXiv source",
                "source_type": "preprint",
                "arxiv_id": "2401.00002",
            }])
            fetcher = FakeFetcher({"export.arxiv.org/api/query?id_list=2401.00002": "arxiv_preprint_only.xml"})

            result = metadata_adapters.verify_publication_identity(base, fetcher=fetcher)

        record = result["source_versions"][0]
        self.assertEqual(record["publication_identity"]["status"], "PREPRINT_VERIFIED")
        self.assertEqual(record["publication_identity"]["version"], "preprint")
        self.assertFalse(record["flags"]["superseded"])
        self.assertEqual(record["identifiers"]["arxiv_id"], "2401.00002v1")

    def test_pubmed_and_pmc_parse_retraction_correction_and_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            _write_sources(base, [
                {"source_id": "S-001", "title": "Retracted", "pmid": "11111111"},
                {"source_id": "S-002", "title": "Corrected", "pmid": "22222222"},
                {"source_id": "S-003", "title": "PMC", "pmcid": "PMC3333333"},
            ])
            fetcher = FakeFetcher({
                "db=pubmed&id=11111111": "pubmed_retracted.xml",
                "db=pubmed&id=22222222": "pubmed_corrected.xml",
                "db=pmc&id=3333333": "pmc_record.xml",
            })

            result = metadata_adapters.verify_publication_identity(base, fetcher=fetcher)

        by_id = {row["source_id"]: row for row in result["source_versions"]}
        self.assertTrue(by_id["S-001"]["flags"]["retracted"])
        self.assertEqual(by_id["S-001"]["publication_identity"]["status"], "RETRACTED")
        self.assertEqual(by_id["S-001"]["identifiers"]["pmid"], "11111111")
        self.assertTrue(by_id["S-002"]["flags"]["corrected"])
        self.assertEqual(by_id["S-002"]["publication_identity"]["status"], "CORRECTED")
        self.assertEqual(by_id["S-003"]["publication_identity"]["status"], "PUBLISHED_VERIFIED")
        self.assertEqual(by_id["S-003"]["identifiers"]["pmcid"], "PMC3333333")
        self.assertEqual(by_id["S-003"]["identifiers"]["pmid"], "33333333")

    def test_unresolved_and_stubbed_domain_sources_log_gap_without_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            _write_sources(base, [
                {"source_id": "S-001", "title": "Unknown source", "url": "https://example.org/no-id"},
                {"source_id": "S-002", "title": "ACM paper", "url": "https://dl.acm.org/doi/abs/no-doi"},
                {"source_id": "S-003", "title": "Missing PubMed", "pmid": "99999999"},
            ])
            fetcher = FakeFetcher({"db=pubmed&id=99999999": "unresolved_404.xml"})

            result = metadata_adapters.verify_publication_identity(base, fetcher=fetcher)
            logs = _read_jsonl(base / "retrieval_log.jsonl")

        by_id = {row["source_id"]: row for row in result["source_versions"]}
        self.assertEqual(by_id["S-001"]["publication_identity"]["status"], "UNRESOLVED")
        self.assertEqual(by_id["S-002"]["publication_identity"]["status"], "UNRESOLVED")
        self.assertEqual(by_id["S-003"]["publication_identity"]["status"], "UNRESOLVED")
        self.assertTrue(any(row["adapter"] == "domain" and "no domain identifier" in row["error"] for row in logs))
        self.assertTrue(any(row["adapter"] == "acm" and "not yet wired" in row["error"] for row in logs))

    def test_pubmed_retracted_fixture_blocks_through_existing_verify_merge(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            _write_sources(base, [{"source_id": "S-001", "title": "Retracted", "pmid": "11111111"}])
            (base / "03_claims.jsonl").write_text(
                json.dumps({
                    "claim_id": "C-001",
                    "perspective": "academic",
                    "claim_text": "The retracted study reports a result.",
                    "claim_type": "fact",
                    "evidence_status": "supported",
                    "source_ids": ["S-001"],
                }) + "\n",
                encoding="utf-8",
            )
            (base / "04_contradictions.json").write_text("[]", encoding="utf-8")
            fetcher = FakeFetcher({"db=pubmed&id=11111111": "pubmed_retracted.xml"})

            metadata_adapters.verify_publication_identity(base, fetcher=fetcher)
            gate = verify_mod.verify(base)

        self.assertTrue(any("retracted source S-001" in issue for issue in gate["blocking_issues"]))


if __name__ == "__main__":
    unittest.main()
