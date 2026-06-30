#!/usr/bin/env python3
"""Offline-safe publication metadata adapters for Storm Council runs.

The adapters verify publication identity, not claim support. They are opt-in:
this script only writes metadata artifacts when it is explicitly run. Network
retrieval uses the standard library, writes through a disk cache, and degrades
to UNRESOLVED/METADATA_PARTIAL when unavailable.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

_DOI_RE = re.compile(r"10\.\d{4,9}/\S+")


def normalize_doi(value) -> str | None:
    if not value:
        return None
    s = str(value).strip()
    s = re.sub(r"(?i)^https?://(dx\.)?doi\.org/", "", s)
    s = re.sub(r"(?i)^doi:\s*", "", s)
    s = s.strip().rstrip(".,;)")
    if not _DOI_RE.fullmatch(s):
        return None
    return s.lower()


def _doi_from_url(url) -> str | None:
    if not url:
        return None
    m = re.search(r"10\.\d{4,9}/[^\s?#]+", str(url))
    return normalize_doi(m.group(0)) if m else None


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _request_id(url: str) -> str:
    return hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]


class MetadataCache:
    def __init__(self, cache_dir: Path):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def path_for(self, url: str) -> Path:
        return self.cache_dir / (hashlib.sha256(url.encode("utf-8")).hexdigest() + ".json")

    def read(self, url: str):
        path = self.path_for(url)
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except ValueError:
            return None

    def write(self, url: str, data) -> None:
        path = self.path_for(url)
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _urllib_fetcher(url, headers=None, timeout=20):
    req = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def cached_json(url: str, cache: MetadataCache, fetcher=None, adapter: str = "metadata",
                headers=None, timeout=20, no_retrieve: bool = False, log: list | None = None) -> dict:
    cached = cache.read(url)
    rid = _request_id(url)
    if cached is not None:
        entry = {"request_id": rid, "adapter": adapter, "url": url, "cache_hit": True,
                 "offline": False, "timestamp": _now(), "error": None}
        if log is not None:
            log.append(entry)
        return {"data": cached, **entry}

    if no_retrieve:
        entry = {"request_id": rid, "adapter": adapter, "url": url, "cache_hit": False,
                 "offline": True, "timestamp": _now(), "error": "retrieval disabled"}
        if log is not None:
            log.append(entry)
        return {"data": None, **entry}

    fetch = fetcher or _urllib_fetcher
    try:
        raw = fetch(url, headers=headers or {}, timeout=timeout)
        if isinstance(raw, str):
            raw = raw.encode("utf-8")
        data = json.loads(raw.decode("utf-8"))
        cache.write(url, data)
        entry = {"request_id": rid, "adapter": adapter, "url": url, "cache_hit": False,
                 "offline": False, "timestamp": _now(), "error": None}
        if log is not None:
            log.append(entry)
        return {"data": data, **entry}
    except (OSError, urllib.error.URLError, TimeoutError, ValueError) as exc:
        entry = {"request_id": rid, "adapter": adapter, "url": url, "cache_hit": False,
                 "offline": True, "timestamp": _now(), "error": str(exc)}
        if log is not None:
            log.append(entry)
        return {"data": None, **entry}


def _quoted_doi(doi: str) -> str:
    return urllib.parse.quote(doi, safe="")


def resolve_doi(doi: str, cache: MetadataCache, fetcher=None, no_retrieve: bool = False,
                log: list | None = None) -> dict:
    url = "https://doi.org/" + doi
    return cached_json(url, cache, fetcher, "publisher", headers={"Accept": "application/json"},
                       no_retrieve=no_retrieve, log=log)


def crossref_lookup(doi: str, cache: MetadataCache, fetcher=None, no_retrieve: bool = False,
                    log: list | None = None) -> dict:
    url = "https://api.crossref.org/works/" + _quoted_doi(doi)
    return cached_json(url, cache, fetcher, "crossref", no_retrieve=no_retrieve, log=log)


def openalex_lookup(doi: str, cache: MetadataCache, fetcher=None, no_retrieve: bool = False,
                    log: list | None = None) -> dict:
    url = "https://api.openalex.org/works/doi:" + _quoted_doi(doi)
    return cached_json(url, cache, fetcher, "openalex", no_retrieve=no_retrieve, log=log)


def semantic_scholar_discovery(identifier: str, cache: MetadataCache, fetcher=None,
                               no_retrieve: bool = False, log: list | None = None) -> dict:
    fields = "title,year,authors,citationCount,referenceCount,externalIds"
    encoded = urllib.parse.quote(identifier, safe=":")
    url = f"https://api.semanticscholar.org/graph/v1/paper/{encoded}?fields={fields}"
    return cached_json(url, cache, fetcher, "semantic_scholar", no_retrieve=no_retrieve, log=log)


def _first(values, default=""):
    if isinstance(values, list) and values:
        return values[0]
    return values if values is not None else default


def _date_from_parts(obj) -> str | None:
    if not isinstance(obj, dict):
        return None
    parts = obj.get("date-parts")
    if not (isinstance(parts, list) and parts and isinstance(parts[0], list)):
        return None
    vals = [str(v).zfill(2) for v in parts[0]]
    if not vals:
        return None
    while len(vals) < 3:
        vals.append("01")
    return "-".join(vals[:3])


def _crossref_message(data) -> dict:
    if not isinstance(data, dict):
        return {}
    msg = data.get("message")
    return msg if isinstance(msg, dict) else data


def _relation_items(msg: dict, key: str) -> list:
    rel = msg.get("relation") if isinstance(msg.get("relation"), dict) else {}
    items = rel.get(key) or []
    return items if isinstance(items, list) else []


def _relation_id(msg: dict, *keys: str) -> str | None:
    for key in keys:
        for item in _relation_items(msg, key):
            if isinstance(item, dict) and item.get("id"):
                return normalize_doi(item["id"]) or str(item["id"])
    return None


def _parse_crossref(data) -> dict:
    msg = _crossref_message(data)
    if not msg:
        return {}
    doi = normalize_doi(msg.get("DOI"))
    pub_date = (
        _date_from_parts(msg.get("published-print"))
        or _date_from_parts(msg.get("published-online"))
        or _date_from_parts(msg.get("published"))
    )
    title = _first(msg.get("title")) or None
    authors = []
    for a in msg.get("author") or []:
        if isinstance(a, dict):
            name = ", ".join(x for x in (a.get("family"), a.get("given")) if x)
            if name:
                authors.append(name)
    venue = _first(msg.get("container-title")) or None
    retracted_by = _relation_id(msg, "is-retracted-by", "retracted-by")
    corrected_by = _relation_id(msg, "is-corrected-by", "has-correction", "corrected-by")
    superseded_by = _relation_id(msg, "is-preprint-of", "is-version-of", "is-superseded-by")
    return {
        "doi": doi,
        "title": title,
        "authors": authors,
        "venue": venue,
        "publisher": msg.get("publisher"),
        "publication_date": pub_date,
        "url": msg.get("URL"),
        "type": msg.get("type"),
        "retracted": bool(retracted_by),
        "corrected": bool(corrected_by),
        "superseded": bool(superseded_by),
        "superseded_by": superseded_by,
    }


def _parse_openalex(data) -> dict:
    if not isinstance(data, dict) or "id" not in data:
        return {}
    host = data.get("host_venue") if isinstance(data.get("host_venue"), dict) else {}
    return {
        "doi": normalize_doi(data.get("doi")),
        "title": data.get("title"),
        "openalex_id": data.get("id"),
        "venue": host.get("display_name"),
        "publisher": host.get("publisher"),
        "publication_year": data.get("publication_year"),
        "retracted": bool(data.get("is_retracted")),
    }


def _parse_semantic_scholar(data) -> dict:
    if not isinstance(data, dict):
        return {}
    ext = data.get("externalIds") if isinstance(data.get("externalIds"), dict) else {}
    return {
        "semantic_scholar_id": data.get("paperId"),
        "doi": normalize_doi(ext.get("DOI")),
        "arxiv_id": ext.get("ArXiv") or ext.get("ARXIV"),
        "pmid": ext.get("PubMed") or ext.get("PMID"),
        "title": data.get("title"),
        "citation_count": data.get("citationCount"),
        "reference_count": data.get("referenceCount"),
    }


def _empty_record(source: dict) -> dict:
    sid = source.get("source_id")
    return {
        "source_id": sid,
        "canonical_source_id": sid,
        "duplicate_of": None,
        "title": source.get("title") or None,
        "identifiers": {
            "doi_raw": source.get("doi") or None,
            "doi_normalized": normalize_doi(source.get("doi")) or _doi_from_url(source.get("url")),
            "arxiv_id": None,
            "pmid": None,
            "pmcid": None,
            "openalex_id": None,
            "semantic_scholar_id": None,
            "crossref_work_id": None,
            "publisher_landing_page": None,
        },
        "publication_identity": {
            "status": "UNRESOLVED",
            "version": "unknown",
            "metadata_sources_checked": [],
            "metadata_consistency_score": 0.0,
            "metadata_mismatches": [],
            "duplicate_of": None,
            "related_versions": [],
            "retraction_status": "unknown",
            "correction_status": "unknown",
            "superseded_by": None,
        },
        "flags": {
            "retracted": False,
            "corrected": False,
            "superseded": False,
            "duplicate_version": False,
        },
    }


def _merge_identifier(record: dict, key: str, value) -> None:
    if value and not record["identifiers"].get(key):
        record["identifiers"][key] = value


def _semantic_id_from_url(url: str) -> str | None:
    if not url:
        return None
    m = re.search(r"semanticscholar\.org/(?:paper/)?(?:paper/)?([^/?#]+)$", url)
    if m:
        return m.group(1)
    m = re.search(r"/paper/([^/?#]+)", url)
    return m.group(1) if m and "semanticscholar.org" in url else None


def _version_from_source(source: dict, crossref: dict, ss: dict) -> str:
    text = " ".join(str(source.get(k) or "") for k in ("url", "source_type", "publisher")).lower()
    if "arxiv" in text or crossref.get("type") == "posted-content":
        return "preprint"
    if crossref:
        return "publisher_version"
    if ss.get("arxiv_id"):
        return "preprint"
    return "unknown"


def _finalize_status(record: dict, *, verified: bool, partial: bool) -> None:
    flags = record["flags"]
    pi = record["publication_identity"]
    if flags["retracted"]:
        pi["status"] = "RETRACTED"
        pi["retraction_status"] = "retracted"
    elif flags["superseded"]:
        pi["status"] = "SUPERSEDED"
        pi["retraction_status"] = "not_retracted"
    elif flags["corrected"]:
        pi["status"] = "CORRECTED"
        pi["retraction_status"] = "not_retracted"
        pi["correction_status"] = "corrected"
    elif verified:
        pi["status"] = "PUBLISHED_VERIFIED" if pi["version"] != "preprint" else "PREPRINT_VERIFIED"
        pi["retraction_status"] = "not_retracted"
        if pi["correction_status"] == "unknown":
            pi["correction_status"] = "none"
    elif partial:
        pi["status"] = "METADATA_PARTIAL"


def _canonical_key(record: dict) -> str | None:
    doi = record["identifiers"].get("doi_normalized")
    if doi:
        return "doi:" + doi
    title = (record.get("title") or "").strip().lower()
    if title:
        return "title:" + re.sub(r"\s+", " ", title)
    return None


def _canonicalize(records: list[dict]) -> None:
    seen: dict[str, str] = {}
    for record in sorted(records, key=lambda r: r["source_id"] or ""):
        key = _canonical_key(record)
        if not key:
            continue
        canonical = seen.get(key)
        if not canonical:
            seen[key] = record["source_id"]
            continue
        record["canonical_source_id"] = canonical
        record["duplicate_of"] = canonical
        record["flags"]["duplicate_version"] = True
        record["publication_identity"]["status"] = "DUPLICATE_VERSION"
        record["publication_identity"]["duplicate_of"] = canonical
        record["publication_identity"]["retraction_status"] = (
            record["publication_identity"].get("retraction_status") or "unknown"
        )


def _load_sources(run_dir: Path) -> list[dict]:
    path = run_dir / "03_source_registry.csv"
    if not path.exists():
        return []
    return list(csv.DictReader(io.StringIO(path.read_text(encoding="utf-8"))))


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows),
                    encoding="utf-8")


def _resolve_source(source: dict, cache: MetadataCache, fetcher=None,
                    no_retrieve: bool = False, log: list | None = None) -> tuple[dict, dict]:
    record = _empty_record(source)
    checked = []
    doi = record["identifiers"].get("doi_normalized")
    verified = False
    partial = False
    crossref = {}
    openalex = {}
    ss = {}

    if doi:
        pub = resolve_doi(doi, cache, fetcher, no_retrieve, log)
        checked.append({"adapter": "publisher", "cache_hit": pub["cache_hit"], "offline": pub["offline"]})
        if pub.get("data"):
            record["identifiers"]["publisher_landing_page"] = "https://doi.org/" + doi

        cr = crossref_lookup(doi, cache, fetcher, no_retrieve, log)
        checked.append({"adapter": "crossref", "cache_hit": cr["cache_hit"], "offline": cr["offline"]})
        crossref = _parse_crossref(cr.get("data"))
        if crossref:
            verified = True
            record["identifiers"]["doi_normalized"] = crossref.get("doi") or doi
            record["identifiers"]["crossref_work_id"] = crossref.get("doi") or doi
            record["title"] = crossref.get("title") or record["title"]

        oa = openalex_lookup(doi, cache, fetcher, no_retrieve, log)
        checked.append({"adapter": "openalex", "cache_hit": oa["cache_hit"], "offline": oa["offline"]})
        openalex = _parse_openalex(oa.get("data"))
        if openalex:
            verified = True
            _merge_identifier(record, "openalex_id", openalex.get("openalex_id"))

        sem = semantic_scholar_discovery("DOI:" + doi, cache, fetcher, no_retrieve, log)
        checked.append({"adapter": "semantic_scholar", "cache_hit": sem["cache_hit"], "offline": sem["offline"]})
        ss = _parse_semantic_scholar(sem.get("data"))
    else:
        ssid = _semantic_id_from_url(source.get("url") or "")
        if ssid:
            sem = semantic_scholar_discovery(ssid, cache, fetcher, no_retrieve, log)
            checked.append({"adapter": "semantic_scholar", "cache_hit": sem["cache_hit"], "offline": sem["offline"]})
            ss = _parse_semantic_scholar(sem.get("data"))

    if ss:
        partial = True
        _merge_identifier(record, "semantic_scholar_id", ss.get("semantic_scholar_id"))
        _merge_identifier(record, "arxiv_id", ss.get("arxiv_id"))
        _merge_identifier(record, "pmid", ss.get("pmid"))
        if ss.get("doi") and not record["identifiers"].get("doi_normalized"):
            record["identifiers"]["doi_normalized"] = ss["doi"]
        record["title"] = record["title"] or ss.get("title")

    retracted = bool(crossref.get("retracted") or openalex.get("retracted"))
    corrected = bool(crossref.get("corrected"))
    superseded = bool(crossref.get("superseded"))
    record["flags"]["retracted"] = retracted
    record["flags"]["corrected"] = corrected
    record["flags"]["superseded"] = superseded
    pi = record["publication_identity"]
    pi["version"] = _version_from_source(source, crossref, ss)
    pi["metadata_sources_checked"] = [item["adapter"] for item in checked]
    pi["metadata_consistency_score"] = 1.0 if verified else (0.4 if partial else 0.0)
    if corrected:
        pi["correction_status"] = "corrected"
    if superseded:
        pi["superseded_by"] = crossref.get("superseded_by")

    _finalize_status(record, verified=verified, partial=partial)
    verification = {
        "source_id": source.get("source_id"),
        "checked": checked,
        "result": record["publication_identity"]["status"],
        "identifiers": record["identifiers"],
        "warnings": [k for k, v in record["flags"].items() if v],
    }
    return record, verification


def verify_publication_identity(run_dir, fetcher=None, *, no_retrieve: bool = False,
                                cache_dir=None) -> dict:
    run = Path(run_dir)
    cache = MetadataCache(Path(cache_dir) if cache_dir else run / ".metadata_cache")
    log: list[dict] = []
    sources = _load_sources(run)
    versions = []
    verification = []
    for source in sources:
        record, meta = _resolve_source(source, cache, fetcher, no_retrieve, log)
        versions.append(record)
        verification.append(meta)
    _canonicalize(versions)

    # Keep metadata_verification duplicate warnings aligned after canonicalization.
    duplicate_by_id = {row["source_id"]: row for row in versions if row["flags"]["duplicate_version"]}
    for row in verification:
        if row["source_id"] in duplicate_by_id and "duplicate_version" not in row["warnings"]:
            row["warnings"].append("duplicate_version")
        row["duplicate_of"] = duplicate_by_id.get(row["source_id"], {}).get("duplicate_of")

    _write_jsonl(run / "metadata_verification.jsonl", verification)
    _write_jsonl(run / "source_versions.jsonl", versions)
    _write_jsonl(run / "retrieval_log.jsonl", log)
    return {"metadata_verification": verification, "source_versions": versions, "retrieval_log": log}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Verify publication identity for a Storm Council output dir.")
    ap.add_argument("output_dir")
    ap.add_argument("--no-retrieve", action="store_true",
                    help="use only cached responses; unresolved sources remain explicit")
    args = ap.parse_args(argv)
    out = Path(args.output_dir)
    if not out.is_dir():
        print(f"error: {out} is not a directory", file=sys.stderr)
        return 1
    result = verify_publication_identity(out, no_retrieve=args.no_retrieve)
    print(f"wrote metadata artifacts for {len(result['source_versions'])} sources")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
