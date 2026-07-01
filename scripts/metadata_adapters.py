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
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

_DOI_RE = re.compile(r"10\.\d{4,9}/\S+")
_ARXIV_ID_RE = re.compile(r"(?i)(\d{4}\.\d{4,5}|[a-z-]+(?:\.[A-Z]{2})?/\d{7})(v\d+)?")
_DEFAULT_ENV_PATH = Path(__file__).resolve().parents[1] / ".env"


def _load_env_file(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    values = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        text = line.strip()
        if not text or text.startswith("#"):
            continue
        if text.startswith("export "):
            text = text[len("export "):].strip()
        if "=" not in text:
            continue
        key, value = text.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key:
            continue
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        values[key] = value
    return values


def _semantic_scholar_headers() -> dict[str, str] | None:
    api_key = os.environ.get("SEMANTIC_SCHOLAR_API_KEY")
    if not api_key:
        api_key = _load_env_file(_DEFAULT_ENV_PATH).get("SEMANTIC_SCHOLAR_API_KEY")
    if not api_key:
        return None
    return {"x-api-key": api_key}


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


def cached_text(url: str, cache: MetadataCache, fetcher=None, adapter: str = "metadata",
                headers=None, timeout=20, no_retrieve: bool = False, log: list | None = None) -> dict:
    cached = cache.read(url)
    rid = _request_id(url)
    if isinstance(cached, dict) and cached.get("text") is not None:
        entry = {"request_id": rid, "adapter": adapter, "url": url, "cache_hit": True,
                 "offline": False, "timestamp": _now(), "error": None}
        if log is not None:
            log.append(entry)
        return {"data": cached.get("text"), **entry}

    if no_retrieve:
        entry = {"request_id": rid, "adapter": adapter, "url": url, "cache_hit": False,
                 "offline": True, "timestamp": _now(), "error": "retrieval disabled"}
        if log is not None:
            log.append(entry)
        return {"data": None, **entry}

    fetch = fetcher or _urllib_fetcher
    try:
        raw = fetch(url, headers=headers or {}, timeout=timeout)
        if isinstance(raw, bytes):
            text = raw.decode("utf-8")
        else:
            text = str(raw)
        cache.write(url, {"text": text})
        entry = {"request_id": rid, "adapter": adapter, "url": url, "cache_hit": False,
                 "offline": False, "timestamp": _now(), "error": None}
        if log is not None:
            log.append(entry)
        return {"data": text, **entry}
    except (OSError, urllib.error.URLError, TimeoutError, UnicodeError) as exc:
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
    return cached_json(url, cache, fetcher, "semantic_scholar", headers=_semantic_scholar_headers(),
                       no_retrieve=no_retrieve, log=log)


def _normalize_arxiv_id(value) -> str | None:
    if not value:
        return None
    text = str(value).strip()
    text = re.sub(r"(?i)^arxiv:\s*", "", text)
    text = re.sub(r"(?i)^https?://arxiv\.org/(?:abs|pdf)/", "", text)
    text = text.removesuffix(".pdf")
    m = _ARXIV_ID_RE.search(text)
    return (m.group(1) + (m.group(2) or "")).lower() if m else None


def _arxiv_base_id(value: str) -> str:
    return re.sub(r"v\d+$", "", value, flags=re.I)


def arxiv_lookup(arxiv_id: str, cache: MetadataCache, fetcher=None,
                 no_retrieve: bool = False, log: list | None = None) -> dict:
    aid = _normalize_arxiv_id(arxiv_id)
    if not aid:
        return {"data": None, "request_id": None, "adapter": "arxiv", "url": None,
                "cache_hit": False, "offline": True, "timestamp": _now(),
                "error": "missing arxiv_id"}
    query_id = urllib.parse.quote(_arxiv_base_id(aid), safe="")
    url = "https://export.arxiv.org/api/query?id_list=" + query_id
    return cached_text(url, cache, fetcher, "arxiv", no_retrieve=no_retrieve, log=log)


def pubmed_lookup(identifier: str, cache: MetadataCache, fetcher=None, *,
                  identifier_type: str = "pmid", no_retrieve: bool = False,
                  log: list | None = None) -> dict:
    kind = (identifier_type or "pmid").lower()
    ident = str(identifier or "").strip()
    if not ident:
        return {"data": None, "request_id": None, "adapter": "pubmed", "url": None,
                "cache_hit": False, "offline": True, "timestamp": _now(),
                "error": "missing pubmed identifier"}
    if kind == "pmcid":
        ident = ident.upper().removeprefix("PMC")
        db = "pmc"
    else:
        db = "pubmed"
    encoded = urllib.parse.quote(ident, safe="")
    url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db={db}&id={encoded}&retmode=xml"
    return cached_text(url, cache, fetcher, "pubmed", no_retrieve=no_retrieve, log=log)


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


def _xml_text(elem, path: str, ns: dict | None = None) -> str | None:
    if elem is None:
        return None
    found = elem.find(path, ns or {})
    if found is None:
        return None
    text = " ".join("".join(found.itertext()).split())
    return text or None


def _xml_texts(elem, path: str, ns: dict | None = None) -> list[str]:
    if elem is None:
        return []
    vals = []
    for found in elem.findall(path, ns or {}):
        text = " ".join("".join(found.itertext()).split())
        if text:
            vals.append(text)
    return vals


def _parse_arxiv(data) -> dict:
    if not data:
        return {}
    try:
        root = ET.fromstring(data)
    except ET.ParseError:
        return {}
    ns = {"atom": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}
    entry = root.find("atom:entry", ns)
    if entry is None:
        return {}
    entry_id = _xml_text(entry, "atom:id", ns)
    arxiv_id = _normalize_arxiv_id(entry_id)
    doi = normalize_doi(_xml_text(entry, "arxiv:doi", ns))
    journal_ref = _xml_text(entry, "arxiv:journal_ref", ns)
    authors = _xml_texts(entry, "atom:author/atom:name", ns)
    title = _xml_text(entry, "atom:title", ns)
    updated = _xml_text(entry, "atom:updated", ns)
    published = _xml_text(entry, "atom:published", ns)
    version_match = re.search(r"(v\d+)$", arxiv_id or "", re.I)
    superseded_by = doi or journal_ref
    return {
        "arxiv_id": arxiv_id,
        "arxiv_version": version_match.group(1).lower() if version_match else None,
        "doi": doi,
        "title": title,
        "authors": authors,
        "venue": journal_ref,
        "publication_date": (published or "")[:10] or None,
        "updated_date": (updated or "")[:10] or None,
        "url": entry_id,
        "version": "preprint",
        "retracted": False,
        "corrected": False,
        "superseded": bool(superseded_by),
        "superseded_by": superseded_by,
    }


def _pubmed_date(parent) -> str | None:
    if parent is None:
        return None
    year = _xml_text(parent, "Year")
    if not year:
        return None
    month = _xml_text(parent, "Month") or "01"
    day = _xml_text(parent, "Day") or "01"
    months = {
        "jan": "01", "feb": "02", "mar": "03", "apr": "04", "may": "05", "jun": "06",
        "jul": "07", "aug": "08", "sep": "09", "oct": "10", "nov": "11", "dec": "12",
    }
    month = months.get(month[:3].lower(), month.zfill(2) if month.isdigit() else "01")
    day = day.zfill(2) if day.isdigit() else "01"
    return f"{year}-{month}-{day}"


def _parse_pubmed_article(root) -> dict:
    article = root.find(".//PubmedArticle")
    if article is None:
        return {}
    pmid = _xml_text(article, ".//MedlineCitation/PMID")
    title = _xml_text(article, ".//Article/ArticleTitle")
    venue = _xml_text(article, ".//Article/Journal/Title")
    pub_date = _pubmed_date(article.find(".//Article/Journal/JournalIssue/PubDate"))
    doi = None
    pmcid = None
    for aid in article.findall(".//ArticleIdList/ArticleId"):
        if (aid.get("IdType") or "").lower() == "doi":
            doi = normalize_doi(aid.text)
        elif (aid.get("IdType") or "").lower() == "pmc":
            pmcid = "PMC" + (aid.text or "").upper().removeprefix("PMC")
    authors = []
    for author in article.findall(".//Article/AuthorList/Author"):
        name = ", ".join(x for x in (_xml_text(author, "LastName"), _xml_text(author, "ForeName")) if x)
        if name:
            authors.append(name)
    pub_types = [t.lower() for t in _xml_texts(article, ".//PublicationTypeList/PublicationType")]
    refs = [
        (cc.get("RefType") or "").lower()
        for cc in article.findall(".//CommentsCorrectionsList/CommentsCorrections")
    ]
    retraction_refs = {"retractionin", "retractionof", "retractedandrepublishedin", "retractedandrepublishedfrom"}
    correction_refs = {"erratumin", "erratumfor", "updatein", "updateof", "republishedin", "republishedfrom"}
    retracted = any("retracted publication" in t for t in pub_types) or any(r in retraction_refs for r in refs)
    corrected = any("corrected and republished article" in t for t in pub_types) or any(r in correction_refs for r in refs)
    return {
        "pmid": pmid,
        "pmcid": pmcid,
        "doi": doi,
        "title": title,
        "authors": authors,
        "venue": venue,
        "publication_date": pub_date,
        "version": "publisher_version",
        "retracted": retracted,
        "corrected": corrected,
        "superseded": False,
        "superseded_by": None,
    }


def _parse_pmc_article(root) -> dict:
    article = root.find(".//article") if root.tag != "article" else root
    if article is None:
        return {}
    ids = {}
    for aid in article.findall(".//article-meta/article-id"):
        key = (aid.get("pub-id-type") or "").lower()
        if key and aid.text:
            ids[key] = aid.text.strip()
    authors = []
    for contrib in article.findall(".//article-meta/contrib-group/contrib"):
        surname = _xml_text(contrib, ".//surname")
        given = _xml_text(contrib, ".//given-names")
        name = ", ".join(x for x in (surname, given) if x)
        if name:
            authors.append(name)
    pub_date = _pubmed_date(article.find(".//article-meta/pub-date"))
    return {
        "pmid": ids.get("pmid"),
        "pmcid": "PMC" + (ids.get("pmc") or "").upper().removeprefix("PMC") if ids.get("pmc") else None,
        "doi": normalize_doi(ids.get("doi")),
        "title": _xml_text(article, ".//article-meta/title-group/article-title"),
        "authors": authors,
        "venue": _xml_text(article, ".//journal-meta/journal-title-group/journal-title"),
        "publication_date": pub_date,
        "version": "publisher_version",
        "retracted": False,
        "corrected": False,
        "superseded": False,
        "superseded_by": None,
    }


def _parse_pubmed(data) -> dict:
    if not data:
        return {}
    try:
        root = ET.fromstring(data)
    except ET.ParseError:
        return {}
    parsed = _parse_pubmed_article(root)
    return parsed or _parse_pmc_article(root)


def _empty_record(source: dict) -> dict:
    sid = source.get("source_id")
    doi_raw = _source_identifier(source, "doi_raw") or source.get("doi") or None
    return {
        "source_id": sid,
        "canonical_source_id": sid,
        "duplicate_of": None,
        "title": source.get("title") or None,
        "identifiers": {
            "doi_raw": doi_raw,
            "doi_normalized": normalize_doi(_source_identifier(source, "doi_normalized") or doi_raw)
            or _doi_from_url(source.get("url")),
            "arxiv_id": _source_identifier(source, "arxiv_id") or _arxiv_id_from_url(source.get("url")),
            "pmid": _source_identifier(source, "pmid") or _pmid_from_url(source.get("url")),
            "pmcid": _source_identifier(source, "pmcid") or _pmcid_from_url(source.get("url")),
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


def _identifiers_obj(source: dict) -> dict:
    identifiers = source.get("identifiers")
    if isinstance(identifiers, dict):
        return identifiers
    if isinstance(identifiers, str) and identifiers.strip():
        try:
            parsed = json.loads(identifiers)
        except ValueError:
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


def _source_identifier(source: dict, key: str) -> str | None:
    identifiers = _identifiers_obj(source)
    val = identifiers.get(key)
    if not val and key == "doi_raw":
        val = identifiers.get("doi") or source.get("doi")
    if not val:
        val = source.get(key)
    if val is None:
        return None
    text = str(val).strip()
    if not text or text.lower() in {"null", "none"}:
        return None
    if key == "arxiv_id":
        return _normalize_arxiv_id(text)
    if key == "pmcid":
        return "PMC" + text.upper().removeprefix("PMC") if text else None
    return text


def _arxiv_id_from_url(url: str) -> str | None:
    return _normalize_arxiv_id(url)


def _pmid_from_url(url: str) -> str | None:
    if not url:
        return None
    m = re.search(r"pubmed\.ncbi\.nlm\.nih\.gov/(\d+)", str(url))
    return m.group(1) if m else None


def _pmcid_from_url(url: str) -> str | None:
    if not url:
        return None
    m = re.search(r"PMC(\d+)", str(url), re.I)
    return "PMC" + m.group(1) if m else None


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


def _stub_domain(source: dict) -> str | None:
    text = " ".join(str(source.get(k) or "") for k in ("url", "publisher", "source_type", "title")).lower()
    if "ieee" in text:
        return "ieee"
    if "acm.org" in text or "acm " in text or "association for computing machinery" in text:
        return "acm"
    if "ssrn" in text:
        return "ssrn"
    if "nber" in text:
        return "nber"
    if "repec" in text or "ideas.repec" in text:
        return "repec"
    if "ietf.org/rfc" in text or "rfc " in text:
        return "standards"
    if "iso.org" in text or source.get("source_type") == "standards":
        return "standards"
    return None


def _log_domain_gap(source: dict, adapter: str, reason: str, log: list | None = None) -> dict:
    url = source.get("url") or f"{adapter}:{source.get('source_id') or 'unknown'}"
    entry = {"request_id": _request_id(url + ":" + reason), "adapter": adapter, "url": url,
             "cache_hit": False, "offline": True, "timestamp": _now(), "error": reason}
    if log is not None:
        log.append(entry)
    return entry


def domain_lookup(source: dict, cache: MetadataCache, fetcher=None,
                  no_retrieve: bool = False, log: list | None = None) -> dict:
    arxiv_id = _source_identifier(source, "arxiv_id") or _arxiv_id_from_url(source.get("url"))
    if arxiv_id:
        lookup = arxiv_lookup(arxiv_id, cache, fetcher, no_retrieve=no_retrieve, log=log)
        return {"adapter": "arxiv", "lookup": lookup, "data": _parse_arxiv(lookup.get("data"))}

    pmid = _source_identifier(source, "pmid") or _pmid_from_url(source.get("url"))
    if pmid:
        lookup = pubmed_lookup(pmid, cache, fetcher, identifier_type="pmid",
                               no_retrieve=no_retrieve, log=log)
        return {"adapter": "pubmed", "lookup": lookup, "data": _parse_pubmed(lookup.get("data"))}

    pmcid = _source_identifier(source, "pmcid") or _pmcid_from_url(source.get("url"))
    if pmcid:
        lookup = pubmed_lookup(pmcid, cache, fetcher, identifier_type="pmcid",
                               no_retrieve=no_retrieve, log=log)
        return {"adapter": "pubmed", "lookup": lookup, "data": _parse_pubmed(lookup.get("data"))}

    stub = _stub_domain(source)
    if stub:
        entry = _log_domain_gap(source, stub, "domain adapter not yet wired", log)
        return {"adapter": stub, "lookup": entry, "data": {}}

    entry = _log_domain_gap(source, "domain", "no domain identifier", log)
    return {"adapter": "domain", "lookup": entry, "data": {}}


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
    domain = {}

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

    domain_source = {**source, "identifiers": record["identifiers"]}
    domain_result = domain_lookup(domain_source, cache, fetcher, no_retrieve=no_retrieve, log=log)
    lookup = domain_result.get("lookup") or {}
    if domain_result.get("adapter") not in {"domain"}:
        checked.append({"adapter": domain_result.get("adapter"), "cache_hit": lookup.get("cache_hit", False),
                        "offline": lookup.get("offline", False)})
    domain = domain_result.get("data") or {}
    if domain:
        verified = True
        if domain.get("arxiv_id"):
            record["identifiers"]["arxiv_id"] = domain["arxiv_id"]
        if domain.get("pmid"):
            record["identifiers"]["pmid"] = domain["pmid"]
        if domain.get("pmcid"):
            record["identifiers"]["pmcid"] = domain["pmcid"]
        if domain.get("doi") and not record["identifiers"].get("doi_normalized"):
            record["identifiers"]["doi_normalized"] = domain["doi"]
        record["title"] = domain.get("title") or record["title"]

    retracted = bool(crossref.get("retracted") or openalex.get("retracted") or domain.get("retracted"))
    corrected = bool(crossref.get("corrected") or domain.get("corrected"))
    superseded = bool(crossref.get("superseded") or domain.get("superseded"))
    record["flags"]["retracted"] = retracted
    record["flags"]["corrected"] = corrected
    record["flags"]["superseded"] = superseded
    pi = record["publication_identity"]
    pi["version"] = domain.get("version") or _version_from_source(source, crossref, ss)
    pi["metadata_sources_checked"] = [item["adapter"] for item in checked]
    pi["metadata_consistency_score"] = 1.0 if verified else (0.4 if partial else 0.0)
    if corrected:
        pi["correction_status"] = "corrected"
    if superseded:
        pi["superseded_by"] = crossref.get("superseded_by") or domain.get("superseded_by")
    if domain.get("arxiv_version"):
        pi["related_versions"].append({
            "type": "arxiv",
            "id": domain.get("arxiv_id"),
            "version": domain.get("arxiv_version"),
            "updated_date": domain.get("updated_date"),
        })

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
