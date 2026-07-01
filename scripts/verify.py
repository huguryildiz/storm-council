#!/usr/bin/env python3
"""Verify a Storm Council output directory and compute the quality gate.

Pure standard library. No network, no LLM, no API key. This is the deterministic
half of the workflow's honesty guarantee: the *reasoning* is the model's, but the
*verification and scoring* are computed here from the artifacts the skill wrote.

Reads (from the output directory):
  - 03_claims.jsonl          one claim record per line
  - 03_evidence.jsonl        (optional) one evidence record per line (schema v2)
  - 03_evidence_verdicts.jsonl (optional) LLM-assisted entailment/scope verdicts
  - 04_contradictions.json   array of contradiction records
  - 03_source_registry.csv   the source registry (source_id, source_type, ...)
  - report_data.json         (optional) for option/action recommendation scoring

Checks (structural + deterministic publication/content guards):
  - reference integrity (claim/source/evidence/contradiction IDs resolve)
  - supported facts/inferences cite a source
  - DOI normalization + duplicate-DOI (same paper under two source IDs)
  - retracted / superseded / corrected source handling
  - placeholder / unverifiable source URLs
  - schema v2 direct_support requires an evidence locator
  - direct / strong / comparative located evidence requires a well-formed verdict
  - abstract-only sources cannot directly support strong claims
  - comparative claims require scope fields (metric / baseline / dataset)
  - unsupported absolute / overclaiming language

Deterministic code cannot decide semantic entailment; it enforces the structural
and identity preconditions that make a real entailment judgement possible, and
surfaces the rest as issues for the model/human reviewer.

Usage:
  python3 verify.py <output_dir>            # print the report, exit 0
  python3 verify.py <output_dir> --write    # write 06_quality_gate.json + patch report_data.json
  python3 verify.py <output_dir> --strict   # exit 2 on REVISE / BLOCKED
  python3 verify.py <output_dir> --seal     # hash artifacts -> provenance_manifest.json
  python3 verify.py <output_dir> --check-seal  # re-hash and report PASS / ALTERED

Sealing is INTEGRITY, not AUTHENTICITY: content hashes prove a bundle is unchanged
since it was sealed; an unsigned manifest cannot prove *who* sealed it, and anyone
with write access can alter a file and regenerate the manifest to match. See §10 of
the 07a plan and the manifest's own _schema_notes.
"""

from __future__ import annotations

import argparse
import csv
import difflib
import hashlib
import io
import json
import re
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Loaded standalone (spec_from_file_location) or run as a script: make the sibling
# ``report`` package importable so status/score thresholds stay shared with the
# renderer (report/thresholds.py) and can't drift.
_PKG_DIR = os.path.dirname(os.path.abspath(__file__))
if _PKG_DIR not in sys.path:
    sys.path.insert(0, _PKG_DIR)
from report.thresholds import POSITIVE_LEVELS as _POSITIVE_LEVELS, SCORE_WARN_MIN

_ID = re.compile(r"\b[CSXE]-\d{3,}\b")
_LOW_QUALITY = {"blog", "other", "news"}
_EVIDENCE_BEARING = {"supported", "partially_supported", "contested"}
_STRONG_TYPES = {"fact", "inference", "recommendation"}
_SUPPORTED = {"supported", "partially_supported"}

# Publication identity / version status enums (schema v2).
_RETRACTED = {"retracted"}
_DOWNGRADED_STATUS = {"superseded", "corrected", "duplicate_version"}

# Source provenance classes (schema §7.3). A run's own search/retrieval log is
# `run_log` — provenance for what was queried, never external support for a claim.
_SOURCE_CLASSES = {"peer_reviewed", "preprint", "official", "gray", "run_log"}

# Content verification statuses (schema v2).
_DIRECT = "direct_support"
_VERDICT_VALUES = {"entails", "partial", "does_not_entail", "uncertain"}
_SCOPE_VERDICT_VALUES = {"yes", "narrowed", "overclaimed", "uncertain"}

# A locator is satisfied by any one of these (evidence record or inline).
_LOCATOR_KEYS = ("page", "section", "subsection", "table", "figure",
                 "equation", "paragraph_hint", "clause")

# Overclaiming lexicon. "hard" terms assert proof/causation/superlatives;
# "absolute" terms assert universal scope. Both are heuristics, never proof of
# error — they are surfaced so the reviewer checks them against the evidence.
_OVERCLAIM_HARD = {"proves", "proven", "disproves", "causes", "causal",
                   "guarantees", "guaranteed", "best", "superior", "optimal"}
_OVERCLAIM_ABSOLUTE = {"all", "always", "never", "none", "every", "everything"}
_OVERCLAIM = _OVERCLAIM_HARD | _OVERCLAIM_ABSOLUTE

# Comparative phrasing that demands scope fields.
_COMPARATIVE_HINT = re.compile(
    r"\b(outperform\w*|better than|faster than|superior|exceeds?|beats?|"
    r"more accurate|higher than|lower than|state[- ]of[- ]the[- ]art)\b", re.I)

_CAUSAL_HINT = re.compile(r"\b(causes?|causal|because of|leads? to|results? in)\b", re.I)

_PLACEHOLDER_URL = re.compile(
    r"(example\.(com|org|net|edu|invalid|test)|\.invalid\b|\.test\b|\.example\b|"
    r"localhost|127\.0\.0\.1|placeholder|your-domain|todo|xxxx|tbd)", re.I)

_DOI_RE = re.compile(r"10\.\d{4,9}/\S+")


# --------------------------------------------------------------------------- #
# Helpers (unit-testable)
# --------------------------------------------------------------------------- #

def normalize_doi(value) -> str | None:
    """Return a normalized DOI (lowercased, prefix-stripped) or None if absent
    or malformed. Accepts bare DOIs, ``doi:`` prefixes, and doi.org URLs."""
    if not value:
        return None
    s = str(value).strip()
    s = re.sub(r"(?i)^https?://(dx\.)?doi\.org/", "", s)
    s = re.sub(r"(?i)^doi:\s*", "", s)
    s = s.strip().rstrip(".,;)")
    m = _DOI_RE.fullmatch(s)
    if not m:
        return None
    return s.lower()


def _doi_from_url(url) -> str | None:
    if not url:
        return None
    m = re.search(r"10\.\d{4,9}/[^\s?#]+", str(url))
    return normalize_doi(m.group(0)) if m else None


def is_placeholder_url(url) -> bool:
    if not url:
        return False
    return bool(_PLACEHOLDER_URL.search(str(url)))


def find_overclaims(text) -> list:
    """Return overclaiming terms present in ``text`` (word-boundary matched)."""
    if not text:
        return []
    low = str(text).lower()
    hits = []
    for term in sorted(_OVERCLAIM):
        if re.search(r"\b" + re.escape(term) + r"\b", low):
            hits.append(term)
    return hits


def _source_field(s: dict, *keys: str) -> str:
    for k in keys:
        v = (s.get(k) or "").strip() if isinstance(s.get(k), str) else s.get(k)
        if v and str(v).lower() != "null":
            return str(v)
    return ""


def _source_doi(s: dict) -> str | None:
    ident = s.get("identifiers") if isinstance(s.get("identifiers"), dict) else {}
    raw = (ident.get("doi_normalized") or ident.get("doi_raw")
           or s.get("doi") or s.get("doi_normalized"))
    doi = normalize_doi(raw) if raw else None
    if doi:
        return doi
    return _doi_from_url(s.get("url"))


def _doi_declared(s: dict) -> str:
    ident = s.get("identifiers") if isinstance(s.get("identifiers"), dict) else {}
    return _source_field({**s, **ident}, "doi", "doi_raw", "doi_normalized")


def _publication_status(s: dict) -> str:
    pid = s.get("publication_identity") if isinstance(s.get("publication_identity"), dict) else {}
    val = _source_field({**s, **pid}, "status", "publication_status", "retraction_status")
    return val.lower()


def _publication_flags(s: dict) -> dict:
    flags = s.get("flags") if isinstance(s.get("flags"), dict) else {}
    return flags


def _full_text_status(s: dict) -> str:
    acc = s.get("access") if isinstance(s.get("access"), dict) else {}
    val = _source_field({**s, **acc}, "full_text_status")
    return val.lower()


def _source_class(s: dict) -> str:
    """Return the source's provenance class. An unknown or missing class
    defaults to ``gray`` — never ``peer_reviewed`` — so a backfill gap can only
    ever weaken a source's standing, and an old registry that omits the field is
    read as ordinary (gray) support, not blocked."""
    val = _source_field(s, "source_class").lower()
    return val if val in _SOURCE_CLASSES else "gray"


def _claim_full_text_status(c: dict, sources_by_id: dict) -> str:
    cv = c.get("content_verification") if isinstance(c.get("content_verification"), dict) else {}
    val = (cv.get("full_text_status") or "").lower()
    if val:
        return val
    statuses = {_full_text_status(sources_by_id[sid])
                for sid in c.get("source_ids", []) if sid in sources_by_id}
    statuses.discard("")
    if statuses and statuses <= {"abstract_only"}:
        return "abstract_only"
    return ""


def _claim_is_strong(c: dict) -> bool:
    strength = (c.get("claim_strength") or "").lower()
    if strength in {"comparative", "causal", "quantitative"}:
        return True
    text = c.get("claim_text") or c.get("text") or ""
    if _COMPARATIVE_HINT.search(text) or _CAUSAL_HINT.search(text):
        return True
    return bool(find_overclaims(text))


def _claim_is_comparative(c: dict) -> bool:
    if (c.get("claim_strength") or "").lower() == "comparative":
        return True
    return bool(_COMPARATIVE_HINT.search(c.get("claim_text") or c.get("text") or ""))


def _claim_requires_entailment_verdict(c: dict) -> bool:
    cv = c.get("content_verification") if isinstance(c.get("content_verification"), dict) else {}
    if (cv.get("status") or "").lower() == _DIRECT:
        return True
    strength = (c.get("claim_strength") or "").lower()
    if strength in {"strong", "comparative"}:
        return True
    return _claim_is_comparative(c)


def _locator_present(loc) -> bool:
    if not isinstance(loc, dict):
        return False
    return any(loc.get(k) for k in _LOCATOR_KEYS)


# --------------------------------------------------------------------------- #
# Loading
# --------------------------------------------------------------------------- #

def _read_jsonl(path: Path) -> list:
    rows = []
    if not path.exists():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def _load(d: Path):
    claims = _read_jsonl(d / "03_claims.jsonl")
    evidence = _read_jsonl(d / "03_evidence.jsonl")
    verdicts = _read_jsonl(d / "03_evidence_verdicts.jsonl")
    contradictions = []
    xf = d / "04_contradictions.json"
    if xf.exists():
        contradictions = json.loads(xf.read_text(encoding="utf-8")) or []
    sources = []
    sf = d / "03_source_registry.csv"
    if sf.exists():
        sources = list(csv.DictReader(io.StringIO(sf.read_text(encoding="utf-8"))))
    report = {}
    rf = d / "report_data.json"
    if rf.exists():
        report = json.loads(rf.read_text(encoding="utf-8"))
    return claims, evidence, verdicts, contradictions, sources, report


def _load_source_versions(d: Path) -> dict:
    rows = {}
    for row in _read_jsonl(d / "source_versions.jsonl"):
        sid = row.get("source_id")
        if sid:
            rows[sid] = row
    return rows


def _merge_source_versions(sources_by_id: dict, versions_by_id: dict) -> None:
    for sid, version in versions_by_id.items():
        if sid not in sources_by_id:
            continue
        src = sources_by_id[sid]
        for key in ("identifiers", "publication_identity", "flags",
                    "canonical_source_id", "duplicate_of"):
            if key in version:
                src[key] = version[key]


def _pct(num: int, den: int) -> int:
    return round(100 * num / den) if den else 0


def _contradiction_claim_ids(x: dict) -> list:
    ids = []
    for k in ("claim_a_id", "claim_b_id"):
        if x.get(k):
            ids.append(x.get(k))
    cl = x.get("claim_ids")
    if isinstance(cl, list):
        ids.extend([c for c in cl if c])
    return ids


def _contradiction_id(x: dict) -> str:
    # Canonical id is `id`; `conflict_id`/`contradiction_id` are deprecated aliases.
    return x.get("id") or x.get("conflict_id") or x.get("contradiction_id") or "?"


def _resolution_is_credited(x: dict) -> bool:
    """A self-declared resolution only counts toward the contradiction score
    when it names a real basis and cites the evidence (E-###) or deliberation
    moves (M-###) that settled it. A bare ``resolution_status`` with no basis —
    or ``basis:"none"`` — is uncredited: it does not improve the score."""
    if x.get("resolution_status") not in {"resolved", "partially_resolved"}:
        return False
    res = x.get("resolution")
    if not isinstance(res, dict):
        return False
    basis = str(res.get("basis") or "").lower()
    if basis in ("", "none"):
        return False
    return bool((res.get("evidence_ids") or []) or (res.get("move_ids") or []))


# --------------------------------------------------------------------------- #
# Verification
# --------------------------------------------------------------------------- #

def verify(d: Path) -> dict:
    claims, evidence, verdicts, contradictions, sources, report = _load(d)
    claim_ids = {c.get("claim_id") for c in claims}
    src_ids = {s.get("source_id") for s in sources}
    sources_by_id = {s.get("source_id"): s for s in sources}
    _merge_source_versions(sources_by_id, _load_source_versions(d))
    evidence_by_id = {e.get("evidence_id"): e for e in evidence}
    verdicts_by_pair = {
        (v.get("claim_id"), v.get("evidence_id")): v
        for v in verdicts
        if isinstance(v, dict)
    }

    blocking, major, minor = [], [], []

    # --- reference integrity ------------------------------------------------ #
    link_errors, citation_free = [], []
    for c in claims:
        cid = c.get("claim_id", "?")
        for sid in c.get("source_ids", []):
            if sid not in src_ids:
                link_errors.append(f"{cid} cites missing source {sid}")
        for xid in c.get("counterevidence_ids", []):
            if xid not in claim_ids:
                link_errors.append(f"{cid} references missing counter-claim {xid}")
        for eid in c.get("evidence_ids", []) or []:
            if eid not in evidence_by_id:
                link_errors.append(f"{cid} references missing evidence {eid}")
        if (c.get("claim_type") in {"fact", "inference"}
                and c.get("evidence_status") in _SUPPORTED
                and not c.get("source_ids")):
            citation_free.append(f"{cid} ({c.get('claim_type')}/{c.get('evidence_status')}) cites no source")
    for e in evidence:
        sid = e.get("source_id")
        if sid and sid not in src_ids:
            link_errors.append(f"{e.get('evidence_id','?')} references missing source {sid}")
    for x in contradictions:
        for ref in _contradiction_claim_ids(x):
            if ref not in claim_ids:
                link_errors.append(f"{_contradiction_id(x)} references missing claim {ref}")

    # --- LLM-assisted entailment verdict artifact ------------------------- #
    for v in verdicts:
        vid = f"{v.get('claim_id', '?')}->{v.get('evidence_id', '?')}"
        cid = v.get("claim_id")
        eid = v.get("evidence_id")
        verdict = (v.get("verdict") or "").lower()
        scope_verdict = (v.get("scope_preserved") or "").lower()
        if cid not in claim_ids:
            blocking.append(f"Evidence verdict {vid} references missing claim {cid}")
        if eid not in evidence_by_id:
            blocking.append(f"Evidence verdict {vid} references missing evidence {eid}")
        if verdict not in _VERDICT_VALUES:
            blocking.append(f"Evidence verdict {vid} has invalid verdict '{v.get('verdict')}'")
        if scope_verdict not in _SCOPE_VERDICT_VALUES:
            blocking.append(
                f"Evidence verdict {vid} has invalid scope_preserved '{v.get('scope_preserved')}'"
            )
        if not isinstance(v.get("rationale"), str) or not v.get("rationale", "").strip():
            blocking.append(f"Evidence verdict {vid} is missing a rationale")
        if not isinstance(v.get("human_review_required"), bool):
            blocking.append(f"Evidence verdict {vid} has non-boolean human_review_required")

    # --- anti-rubber-stamp: identical rationales --------------------------- #
    # A verifier that reuses one rationale string across many verdicts is not
    # reasoning each verdict individually. Threshold ≥3 identical non-empty
    # strings avoids false positives on legitimately similar short wording.
    # Minor only, never blocking — missing rationales are handled above.
    rationale_counts: dict = {}
    for v in verdicts:
        r = v.get("rationale")
        if isinstance(r, str) and r.strip():
            key = r.strip()
            rationale_counts[key] = rationale_counts.get(key, 0) + 1
    max_repeat = max(rationale_counts.values(), default=0)
    if max_repeat >= 3:
        minor.append(
            f"Verdicts not individually reasoned: {max_repeat} evidence verdicts share "
            "one identical rationale (verification may be rubber-stamping).")

    # --- lens independence: output convergence (Phase 5) ------------------- #
    # run_manifest.json can *assert* independent lens contexts; this reads the
    # actual claim text for the fact. If two lenses produced near-identical
    # claims, their independence is not evident from the output. Minor only,
    # never blocking; thresholded high (>=0.85) so merely related lenses do not
    # trip it, and skipped entirely when a lens has no claim text.
    lens_text: dict = {}
    for c in claims:
        p, t = c.get("perspective"), (c.get("claim_text") or c.get("text") or "")
        if p and t.strip():
            lens_text.setdefault(p, []).append(t.strip())
    converged = []
    lenses_sorted = sorted(lens_text)
    for i in range(len(lenses_sorted)):
        for j in range(i + 1, len(lenses_sorted)):
            a = "\n".join(lens_text[lenses_sorted[i]])
            b = "\n".join(lens_text[lenses_sorted[j]])
            ratio = difflib.SequenceMatcher(None, a, b).ratio()
            if ratio >= 0.85:
                converged.append(f"{lenses_sorted[i]}~{lenses_sorted[j]} ({ratio:.0%})")
    if converged:
        minor.append(
            "Lens outputs converged (independence not evident from claim text): "
            + ", ".join(converged))

    # --- source credibility / identity ------------------------------------- #
    def _is_low(s):
        note = (_source_field(s, "credibility_notes")).lower()
        return s.get("source_type") in _LOW_QUALITY or "synthetic" in note or "low" in note
    low_cred = [s.get("source_id") for s in sources if _is_low(s)]
    low_set = set(low_cred)
    supported_on_low = [
        f"{c.get('claim_id')}->{sid}"
        for c in claims if c.get("evidence_status") == "supported"
        for sid in c.get("source_ids", []) if sid in low_set
    ]

    # A run's own retrieval/search log (source_class == run_log) records what was
    # queried; it is not independent support. A supported claim whose *only*
    # sources are run_log therefore has no external evidence behind it — major.
    # Missing source_class defaults to gray, so pre-Phase-3 registries never trip
    # this (back-compat: absence is never turned into a blocking/major issue).
    run_log_only_support = [
        c.get("claim_id", "?")
        for c in claims
        if c.get("evidence_status") in _SUPPORTED
        for sids in [[sid for sid in c.get("source_ids", []) if sid in sources_by_id]]
        if sids and all(_source_class(sources_by_id[sid]) == "run_log" for sid in sids)
    ]

    # placeholder / unverifiable URLs
    placeholder_src = {s.get("source_id") for s in sources
                       if is_placeholder_url(s.get("url"))}
    if placeholder_src:
        minor.append("Placeholder / unverifiable source URLs: " + ", ".join(sorted(placeholder_src)))

    # malformed declared DOIs
    for s in sources:
        declared = _doi_declared(s)
        if declared and normalize_doi(declared) is None:
            major.append(f"Malformed DOI on {s.get('source_id')}: {declared}")

    # duplicate DOIs (same paper under two source IDs)
    doi_to_sources: dict = {}
    for s in sources:
        doi = _source_doi(s)
        if doi:
            doi_to_sources.setdefault(doi, []).append(s.get("source_id"))
    for doi, sids in doi_to_sources.items():
        canonical = {sources_by_id[sid].get("publication_identity", {}).get("duplicate_of")
                     if isinstance(sources_by_id[sid].get("publication_identity"), dict) else None
                     for sid in sids}
        if len(sids) > 1 and not any(canonical):
            major.append(f"Duplicate source versions share DOI {doi}: {', '.join(sorted(sids))}")

    # retraction / supersession of cited sources
    for c in claims:
        if c.get("evidence_status") not in _SUPPORTED:
            continue
        cid = c.get("claim_id", "?")
        for sid in c.get("source_ids", []):
            s = sources_by_id.get(sid)
            if not s:
                continue
            status = _publication_status(s)
            flags = _publication_flags(s)
            if flags.get("retracted") or status in _RETRACTED:
                blocking.append(f"{cid} relies on retracted source {sid}")
            elif flags.get("superseded") or status == "superseded":
                major.append(f"{cid} relies on superseded source {sid} (needs a visible warning)")
            elif flags.get("corrected") or status == "corrected":
                major.append(f"{cid} relies on corrected source {sid} (needs a visible warning)")
            elif flags.get("duplicate_version") or status == "duplicate_version":
                major.append(f"{cid} relies on duplicate_version source {sid} (needs canonical source warning)")

    # --- content verification (schema v2) ---------------------------------- #
    for c in claims:
        cid = c.get("claim_id", "?")
        cv = c.get("content_verification") if isinstance(c.get("content_verification"), dict) else None
        status = (cv.get("status") or "").lower() if cv else ""
        has_locator = _locator_present(cv.get("evidence_locator")) if cv else False
        for eid in c.get("evidence_ids", []) or []:
            ev = evidence_by_id.get(eid)
            if ev and _locator_present(ev.get("locator")):
                has_locator = True
        if cv and status == _DIRECT:
            # require a resolvable evidence locator
            if not has_locator:
                blocking.append(f"{cid} is direct_support but has no evidence locator")
            # abstract-only cannot directly support a strong claim
            if _claim_full_text_status(c, sources_by_id) == "abstract_only" and _claim_is_strong(c):
                blocking.append(f"{cid} claims direct_support from an abstract-only source for a strong claim")
        if has_locator and _claim_requires_entailment_verdict(c):
            evidence_ids = c.get("evidence_ids", []) or []
            if not evidence_ids:
                major.append(f"{cid} has located direct/strong/comparative support but no evidence_id for a verdict")
            for eid in evidence_ids:
                if eid not in evidence_by_id:
                    continue
                v = verdicts_by_pair.get((cid, eid))
                if not v:
                    major.append(f"{cid}->{eid} has located direct/strong/comparative support but no entailment verdict")
                    continue
                verdict = (v.get("verdict") or "").lower()
                scope_verdict = (v.get("scope_preserved") or "").lower()
                if verdict == "does_not_entail":
                    blocking.append(f"{cid}->{eid} verdict says does_not_entail")
                elif verdict in {"partial", "uncertain"}:
                    major.append(f"{cid}->{eid} verdict is {verdict}; claim support must be downgraded or reviewed")
                if scope_verdict == "overclaimed":
                    blocking.append(f"{cid}->{eid} scope verdict says overclaimed")
                elif scope_verdict in {"narrowed", "uncertain"}:
                    major.append(f"{cid}->{eid} scope preservation is {scope_verdict}; claim needs caveat/review")
        # comparative claims need scope fields
        if _claim_is_comparative(c):
            scope = c.get("support_scope") if isinstance(c.get("support_scope"), dict) else {}
            missing = [k for k in ("metric", "comparison_baseline", "dataset_or_benchmark")
                       if not (scope.get(k) and str(scope.get(k)).strip())]
            if missing:
                major.append(f"{cid} is comparative but missing scope fields: {', '.join(missing)}")

    # abstract-only supporting a strong claim, even without v2 content block
    for c in claims:
        if c.get("content_verification"):
            continue
        if (c.get("evidence_status") in _SUPPORTED and _claim_is_strong(c)
                and _claim_full_text_status(c, sources_by_id) == "abstract_only"):
            major.append(f"{c.get('claim_id')} is a strong claim supported only by an abstract")

    # --- overclaiming language --------------------------------------------- #
    for c in claims:
        terms = find_overclaims(c.get("claim_text") or c.get("text") or "")
        if not terms:
            continue
        cid = c.get("claim_id", "?")
        cv = c.get("content_verification") if isinstance(c.get("content_verification"), dict) else {}
        has_locator = _locator_present(cv.get("evidence_locator")) or any(
            evidence_by_id.get(eid) and _locator_present(evidence_by_id[eid].get("locator"))
            for eid in c.get("evidence_ids", []) or [])
        try:
            conf = float(c.get("confidence")) if c.get("confidence") is not None else 0.0
        except (TypeError, ValueError):
            conf = 0.0
        strong_unbacked = (c.get("evidence_status") in {"supported"}
                           and conf >= 0.85 and not has_locator)
        label = f"{cid} [{', '.join(terms)}]"
        if strong_unbacked:
            major.append(f"Overclaiming language on a high-confidence claim without a locator: {label}")
        else:
            minor.append(f"Overclaiming language to verify against evidence: {label}")

    # --- scores ------------------------------------------------------------- #
    perspectives = {c.get("perspective") for c in claims}
    expected = (report.get("counts", {}).get("lenses") or len(perspectives) or 1)
    coverage = min(100, _pct(len(perspectives), expected))
    if len({c.get("claim_type") for c in claims}) < 3:
        coverage = max(0, coverage - 10)

    evidence_bearing = [c for c in claims if c.get("evidence_status") in _EVIDENCE_BEARING]
    traceable = [c for c in evidence_bearing
                 if c.get("source_ids") and all(s in src_ids for s in c["source_ids"])]
    traceability = _pct(len(traceable), len(evidence_bearing))
    if link_errors:
        traceability = max(0, traceability - 25)

    if contradictions:
        handled = [x for x in contradictions if _resolution_is_credited(x)]
        contradiction_handling = _pct(len(handled), len(contradictions))
    else:
        contradiction_handling = 50

    # Self-declared "resolved" without an evidence/move basis must not be
    # mistaken for real handling — flag it (minor, never blocking on old runs).
    baseless_resolved = [
        _contradiction_id(x) for x in contradictions
        if x.get("resolution_status") in {"resolved", "partially_resolved"}
        and not _resolution_is_credited(x)
    ]

    # --- anti-rubber-stamp: zero rejection on a contested run --------------- #
    # On a contested topic (contradictions present) a verification pass that
    # rejected nothing — no `does_not_entail` verdict and no `unsupported`
    # claim — likely never pushed back. Minor only, never blocking.
    zero_rejection = False
    if contradictions:
        any_rejection = any((v.get("verdict") or "").lower() == "does_not_entail"
                            for v in verdicts)
        any_unsupported = any(c.get("evidence_status") == "unsupported" for c in claims)
        zero_rejection = not any_rejection and not any_unsupported

    options = report.get("options", [])
    actions = report.get("next_actions", [])
    if options or actions:
        opt_share = _pct(len([o for o in options if o.get("strength")]), len(options)) if options else 0
        act_share = _pct(len([a for a in actions
                              if _ID.findall(" ".join(a.get("refs", [])) + " " + a.get("text", ""))]),
                         len(actions)) if actions else 0
        recommendation = round((opt_share + act_share) / 2)
    else:
        recommendation = 0

    supported_share = (len([c for c in claims if c.get("evidence_status") in _SUPPORTED]) / len(claims)) if claims else 0.0
    evidence_absent = (not sources) or supported_share < 0.2

    # claims that depend on placeholder sources
    for c in claims:
        cid = c.get("claim_id", "?")
        st = c.get("evidence_status")
        for sid in c.get("source_ids", []):
            if sid in placeholder_src:
                if st == "supported":
                    blocking.append(f"{cid} is marked supported but cites placeholder source {sid}")
                elif st == "partially_supported":
                    major.append(f"{cid} cites placeholder source {sid}")

    # --- assemble issues ---------------------------------------------------- #
    blocking[:0] = [f"Citation integrity: {e}" for e in link_errors]
    blocking += [f"Citation-free conclusion: {e}" for e in citation_free]
    if evidence_absent:
        blocking.append("Insufficient evidence: no resolvable sources support the claims.")

    unsupported_strong = [
        f"{c.get('claim_id')} ({c.get('claim_type')})"
        for c in claims
        if c.get("claim_type") in _STRONG_TYPES and c.get("evidence_status") == "unsupported"
    ]
    if unsupported_strong:
        major.append("Unsupported strong claims: " + "; ".join(unsupported_strong))
    if supported_on_low:
        major.append("Supported claims depend on low-credibility sources: " + "; ".join(supported_on_low))
    if run_log_only_support:
        major.append(
            "Supported claims rest only on run-log provenance (no external source): "
            + ", ".join(run_log_only_support))
    if (options or actions) and recommendation < SCORE_WARN_MIN:
        major.append(f"Recommendations weakly justified (support score {recommendation}).")

    # --- status banner honesty ----------------------------------------------- #
    report_status_level = str((report.get("status") or {}).get("level", "")).lower()
    if report_status_level in _POSITIVE_LEVELS and not (d / "06_quality_gate.json").exists():
        major.append(
            f"Status banner claims '{report_status_level}' but no 06_quality_gate.json exists. "
            "Run verify.py --write to confirm, or set status.level to 'illustrative' or 'unverified'."
        )

    if low_cred:
        minor.append("Low-credibility sources present: " + ", ".join(sorted(low_cred)))
    open_x = [_contradiction_id(x) for x in contradictions if x.get("resolution_status") == "unresolved"]
    if open_x:
        minor.append("Open contradictions remain for human review: " + ", ".join(open_x))
    if baseless_resolved:
        minor.append(
            "Contradictions marked resolved without an evidence/move basis "
            "(not counted as handled): " + ", ".join(baseless_resolved))
    if zero_rejection:
        minor.append(
            "Verification did not push back: on a contested topic no evidence "
            "verdict is does_not_entail and no claim is unsupported.")

    # --- verdict ------------------------------------------------------------ #
    if evidence_absent:
        verdict = "BLOCKED_PENDING_EVIDENCE"
    elif blocking:
        verdict = "REVISE"
    elif len(major) >= 2:
        verdict = "REVISE"
    elif major or minor:
        verdict = "PASS_WITH_CAVEATS"
    else:
        verdict = "PASS"

    return {
        "status": verdict,
        "blocking_issues": blocking,
        "major_issues": major,
        "minor_issues": minor,
        "coverage_score": coverage,
        "traceability_score": traceability,
        "contradiction_handling_score": contradiction_handling,
        "recommendation_support_score": recommendation,
        "review_summary": f"{verdict} — {len(blocking)} blocking, {len(major)} major, {len(minor)} minor "
                          f"(computed by verify.py over {len(claims)} claims, {len(sources)} sources, "
                          f"{len(evidence)} evidence records, {len(verdicts)} evidence verdicts, "
                          f"{len(contradictions)} contradictions).",
    }


# --------------------------------------------------------------------------- #
# Tamper-evident provenance seal (07a)
#
# INTEGRITY, not AUTHENTICITY. `compute_seal` hashes the artifacts already on
# disk and copies the verdict `verify.py --write` already wrote; it never grades
# or invents a score. An unsigned manifest proves "unchanged since sealing", not
# "sealed by a trusted party" — anyone with write access can re-seal a tampered
# bundle. The CLI help, the manifest `_schema_notes`, and the rendered appendix
# all say so; this is the honest ceiling of content hashing.
# --------------------------------------------------------------------------- #

_SEAL_MANIFEST_NAME = "provenance_manifest.json"
_SEAL_EXCLUDE = {_SEAL_MANIFEST_NAME}
_SEAL_HASH_ALGO = "sha256"
_SEAL_SCHEMA_VERSION = "1.0"
_SEAL_GENERATOR = "storm-council/verify.py"
# Copied verbatim from 06_quality_gate.json — never recomputed here.
_SEAL_VERDICT_FIELDS = ("status", "coverage_score", "traceability_score",
                        "contradiction_handling_score", "recommendation_support_score")
_SEAL_SCHEMA_NOTES = (
    "Content hashes prove the bundle is BYTE-IDENTICAL to what verify.py graded at "
    "sealed_at - they prove INTEGRITY, not AUTHENTICITY. Anyone with write access to "
    "this directory can alter a file and regenerate this manifest to match; an unsigned "
    "manifest cannot prove who sealed it or that it wasn't re-sealed after tampering. "
    "Use --check-seal only to confirm 'this bundle is unchanged since the last time "
    "someone (possibly untrusted) ran --seal' - not as legal proof of non-tampering. "
    "verdict_at_seal_time is copied verbatim from 06_quality_gate.json, never recomputed. "
    "artifacts[] is sorted by path; the manifest excludes itself and dotfiles; file "
    "mtimes are never read (content hash only). 'signature' is a reserved slot for a "
    "future pluggable signing interface (unimplemented in this schema version - always null)."
)


def _sha256_file(path: Path) -> str:
    """SHA-256 over the raw bytes on disk. No line-ending or whitespace
    normalization — 'byte-identical' is the entire claim being sealed."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _seal_artifact_names(d: Path) -> list:
    """Filenames to hash: every regular file directly in ``d`` (non-recursive;
    bundles are flat), excluding the manifest itself and dotfiles. Returned
    sorted by path string — never filesystem iteration order, so two seals of
    an identical directory produce identical ordering (07b re-seal stability)."""
    names = []
    for entry in d.iterdir():
        if not entry.is_file():
            continue
        name = entry.name
        if name in _SEAL_EXCLUDE or name.startswith("."):
            continue
        names.append(name)
    return sorted(names)


def _seal_now() -> str:
    """Local, unwitnessed ISO-8601-with-offset timestamp, matching
    run_manifest.json's generated_at format (no microseconds)."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def compute_seal(d: Path, sealed_at: str | None = None) -> dict:
    """Build a provenance manifest for ``d``: SHA-256 + byte count for every
    artifact, plus the verdict copied verbatim from 06_quality_gate.json.

    Does NOT call verify() and does NOT recompute any score — it reads the
    already-written quality gate and copies its fields, honoring the repo rule
    "never hand-set quality-gate scores". Raises FileNotFoundError if the gate
    is absent (the caller refuses to seal an ungraded bundle)."""
    gate_path = d / "06_quality_gate.json"
    if not gate_path.exists():
        raise FileNotFoundError("06_quality_gate.json")
    gate = json.loads(gate_path.read_text(encoding="utf-8"))
    verdict = {k: gate.get(k) for k in _SEAL_VERDICT_FIELDS}
    artifacts = []
    for name in _seal_artifact_names(d):
        p = d / name
        artifacts.append({"path": name, "sha256": _sha256_file(p),
                          "bytes": p.stat().st_size})
    return {
        "schema_version": _SEAL_SCHEMA_VERSION,
        "generator_version": _SEAL_GENERATOR,
        "sealed_at": sealed_at or _seal_now(),
        "tool": {"name": "verify.py", "invocation": "seal"},
        "verdict_at_seal_time": verdict,
        "hash_algorithm": _SEAL_HASH_ALGO,
        "artifacts": artifacts,
        "signature": None,
        "_schema_notes": _SEAL_SCHEMA_NOTES,
    }


def check_seal(d: Path) -> dict:
    """Re-hash the files named in provenance_manifest.json and compare to the
    recorded digests. Returns {ok, sealed_at, altered[], missing[], added[],
    checked}. Cannot detect a rewritten manifest (the manifest is excluded from
    its own hashed list) — that gap needs a signature, out of scope for the MVP.

    Raises FileNotFoundError if no manifest exists, ValueError if the manifest
    names a hash algorithm this verify.py cannot compute."""
    manifest_path = d / _SEAL_MANIFEST_NAME
    if not manifest_path.exists():
        raise FileNotFoundError(_SEAL_MANIFEST_NAME)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    algo = str(manifest.get("hash_algorithm") or "").lower()
    if algo != _SEAL_HASH_ALGO:
        raise ValueError(f"unsupported hash_algorithm {algo!r}")
    recorded = manifest.get("artifacts") or []
    sealed_names = set()
    altered, missing = [], []
    for entry in recorded:
        name = entry.get("path")
        if not name:
            continue
        sealed_names.add(name)
        p = d / name
        if not p.exists():
            missing.append(name)
            continue
        if _sha256_file(p) != entry.get("sha256"):
            size_mismatch = None
            if p.stat().st_size != entry.get("bytes"):
                size_mismatch = (entry.get("bytes"), p.stat().st_size)
            altered.append({"path": name, "size_mismatch": size_mismatch})
    added = [name for name in _seal_artifact_names(d) if name not in sealed_names]
    return {
        "ok": not altered and not missing,
        "sealed_at": manifest.get("sealed_at"),
        "altered": altered,
        "missing": missing,
        "added": added,
        "checked": len(sealed_names),
    }


def _run_seal(d: Path) -> int:
    if not (d / "06_quality_gate.json").exists():
        print("error: 06_quality_gate.json missing - run verify.py --write first "
              "(refusing to seal an ungraded bundle)", file=sys.stderr)
        return 3
    manifest = compute_seal(d)
    (d / _SEAL_MANIFEST_NAME).write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"sealed: {_SEAL_MANIFEST_NAME} ({len(manifest['artifacts'])} artifacts, "
          f"verdict {manifest['verdict_at_seal_time'].get('status')})")
    print("  note: this is INTEGRITY, not AUTHENTICITY - hashes prove the bundle is "
          "unchanged since sealing, not who sealed it; an unsigned manifest can be "
          "regenerated by anyone with write access.")
    return 0


def _run_check_seal(d: Path) -> int:
    if not (d / _SEAL_MANIFEST_NAME).exists():
        print(f"error: no {_SEAL_MANIFEST_NAME} found - run --seal first", file=sys.stderr)
        return 3
    try:
        rep = check_seal(d)
    except ValueError as ex:
        print(f"error: {ex} - upgrade verify.py", file=sys.stderr)
        return 3
    for entry in rep["altered"]:
        sm = entry.get("size_mismatch")
        extra = f" (bytes {sm[0]} -> {sm[1]})" if sm else ""
        print(f"  altered: {entry['path']}{extra}")
    for name in rep["missing"]:
        print(f"  missing: {name}")
    for name in rep["added"]:
        print(f"  added since seal: {name}")
    if rep["ok"]:
        print(f"check-seal: PASS (bundle unchanged since {rep['sealed_at']})")
        print("  note: PASS means consistent with the last seal, not verified by a "
              "trusted third party - an unsigned manifest cannot prove non-tampering.")
        return 0
    n = len(rep["altered"]) + len(rep["missing"])
    print(f"check-seal: ALTERED ({n} file(s) changed)")
    return 4


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Verify a Storm Council output dir and compute the quality gate.")
    ap.add_argument("output_dir")
    ap.add_argument("--write", action="store_true", help="write 06_quality_gate.json and patch report_data.json")
    ap.add_argument("--strict", action="store_true", help="exit 2 on REVISE / BLOCKED_PENDING_EVIDENCE")
    seal_group = ap.add_mutually_exclusive_group()
    seal_group.add_argument(
        "--seal", action="store_true",
        help="hash every artifact + copy the verify.py verdict into "
             "provenance_manifest.json (INTEGRITY, not authenticity: an unsigned "
             "manifest can be regenerated by anyone with write access). Requires "
             "06_quality_gate.json (run --write first); composes with --write.")
    seal_group.add_argument(
        "--check-seal", action="store_true",
        help="re-hash the directory against provenance_manifest.json and report "
             "PASS / ALTERED. PASS means unchanged since the last seal, NOT verified "
             "by a trusted third party; a rewritten manifest is not detected.")
    args = ap.parse_args(argv)
    d = Path(args.output_dir)
    if not d.is_dir():
        print(f"error: {d} is not a directory", file=sys.stderr)
        return 1

    if args.check_seal:
        return _run_check_seal(d)

    gate = verify(d)

    print(f"verdict: {gate['status']}")
    print(f"  coverage {gate['coverage_score']} · traceability {gate['traceability_score']} · "
          f"contradiction-handling {gate['contradiction_handling_score']} · "
          f"recommendation-support {gate['recommendation_support_score']}")
    for sev in ("blocking_issues", "major_issues", "minor_issues"):
        for msg in gate[sev]:
            print(f"  [{sev.split('_')[0]}] {msg}")

    if args.write:
        (d / "06_quality_gate.json").write_text(json.dumps(gate, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        rf = d / "report_data.json"
        if rf.exists():
            report = json.loads(rf.read_text(encoding="utf-8"))
            scores = {"coverage": gate["coverage_score"], "traceability": gate["traceability_score"],
                      "contradiction": gate["contradiction_handling_score"], "recommendation": gate["recommendation_support_score"]}
            report.setdefault("status", {})["verdict"] = gate["status"]
            report["status"]["scores"] = scores
            report["review"] = {"verdict": gate["status"], "scores": scores,
                                "blocking": gate["blocking_issues"], "major": gate["major_issues"], "minor": gate["minor_issues"]}
            rf.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print("wrote 06_quality_gate.json and patched report_data.json")

    if args.seal:
        rc = _run_seal(d)
        if rc != 0:
            return rc

    if args.strict and gate["status"] in {"REVISE", "BLOCKED_PENDING_EVIDENCE"}:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
