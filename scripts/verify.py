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

# Decision-criticality ordinal enum (schema §7.9 / S10). Ordinal-only — there is
# no numeric importance/weight/probability anywhere in this feature, by design.
_CRITICALITY_VALUES = {"pivotal", "contributing", "peripheral"}

# Contradiction-resolution planner ordinal enums (07d, schema §7.10 / S11). Both
# ordinal-only — no hours/currency/probability, and no value-of-information numbers.
_EFFORT_VALUES = {"low", "medium", "high"}
_DECISION_IMPACT_VALUES = {"would_flip", "might_flip", "unlikely_to_change"}
_OPEN_STATUSES = {"unresolved", "open", "leaning"}
# 07d rejects "VOI theater": any key matching these (case-insensitive, at any nesting
# depth inside resolution_plan) is a fabricated expected-value-of-information field.
_VOI_BANNED_KEYS = {"evsi", "evpi", "evppi", "enbs", "expected_value",
                    "probability", "prior", "utility", "payoff"}

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


def _decision_criticality_minor_issues(dc, claim_ids: set, contra_ids: set) -> list:
    """Structural + internal-consistency checks for decision_criticality.json (07c,
    schema §7.9). ALL issues are MINOR advisories — never blocking/major, and the
    whole block is skipped when the file is absent.

    verify.py does NOT re-derive the ranking (that needs the argument-map graph the
    renderer parses); it validates shape, ID resolution, the ordinal-only rule, and
    the pivotal<->flips_recommendation pairing that makes a wrong `pivotal` catchable.
    A wrong `pivotal` is the single most dangerous failure this feature can produce,
    so that pairing (check 4) and `most_load_bearing` (check 3) get dedicated checks."""
    issues: list = []
    if not isinstance(dc, dict):
        return issues
    rankings = dc.get("rankings")
    if not isinstance(rankings, list):
        rankings = []
    ranked_crit: dict = {}
    for r in rankings:
        if not isinstance(r, dict):
            issues.append("decision_criticality ranking entry is not an object")
            continue
        cid, xid = r.get("claim_id"), r.get("contradiction_id")
        rid = cid or xid or "?"
        # exactly one of claim_id / contradiction_id
        if bool(cid) == bool(xid):
            issues.append(
                f"decision_criticality ranking {rid} must name exactly one of "
                "claim_id / contradiction_id")
        crit = str(r.get("criticality") or "").lower()
        # check 1: enum membership
        if crit not in _CRITICALITY_VALUES:
            issues.append(
                f"decision_criticality ranking {rid} has unknown criticality "
                f"'{r.get('criticality')}' (expected pivotal|contributing|peripheral)")
        # check 2: ID resolution (stale ranking is advisory, never retroactive penalty)
        if cid and cid not in claim_ids:
            issues.append(
                f"decision_criticality ranking references unknown claim {cid} "
                "(stale ranking — claims ledger edited after it was authored?)")
        if xid and xid not in contra_ids:
            issues.append(
                f"decision_criticality ranking references unknown contradiction {xid} "
                "(stale ranking — contradiction ledger edited after it was authored?)")
        # check 4: pivotal <-> flips_recommendation:true pairing
        flips = r.get("flips_recommendation")
        if crit == "pivotal":
            if flips is not True:
                issues.append(
                    f"decision_criticality {rid} is pivotal but flips_recommendation is not "
                    "true (self-contradictory: a pivotal entry changes the recommendation)")
            if not (isinstance(r.get("rule_trace"), str) and r.get("rule_trace").strip()):
                issues.append(
                    f"decision_criticality pivotal ranking {rid} cites no rule_trace — "
                    "cannot be audited")
        elif crit in {"contributing", "peripheral"} and flips is True:
            issues.append(
                f"decision_criticality {rid} is {crit} but flips_recommendation is true "
                "(only a pivotal entry may flip the recommendation)")
        # check 5: no numeric score fields — this feature is ordinal-only
        for k, v in r.items():
            if isinstance(v, bool):
                continue
            if isinstance(v, (int, float)):
                issues.append(
                    f"decision_criticality ranking {rid} carries a numeric field "
                    f"'{k}' — this feature is ordinal-only, remove '{k}'")
        if rid != "?":
            ranked_crit[rid] = crit
    # check 3: most_load_bearing must point at a pivotal entry
    mlb = dc.get("most_load_bearing")
    if mlb and ranked_crit.get(mlb) != "pivotal":
        issues.append(
            "decision_criticality most_load_bearing references a non-pivotal or unranked "
            "entry — this actively misleads the brief reader")
    # check 6: options snapshot + rule required to audit a non-empty ranking
    if rankings:
        if not dc.get("options_considered"):
            issues.append(
                "decision_criticality has rankings but no options_considered snapshot — "
                "the ranking cannot be audited against the recommendation state")
        if not (isinstance(dc.get("recommendation_rule"), str)
                and dc.get("recommendation_rule").strip()):
            issues.append(
                "decision_criticality has rankings but no recommendation_rule — "
                "the ranking cannot be audited")
    return issues


def _pivotal_ids_from_dc(dc) -> set:
    """Set of claim/contradiction ids that decision_criticality.json ranks pivotal.
    Empty when the doc is missing/malformed — never raises."""
    out: set = set()
    if not isinstance(dc, dict):
        return out
    rankings = dc.get("rankings")
    if isinstance(rankings, list):
        for r in rankings:
            if isinstance(r, dict) and str(r.get("criticality") or "").lower() == "pivotal":
                rid = r.get("claim_id") or r.get("contradiction_id")
                if rid:
                    out.add(rid)
    return out


def _voi_offenders(plan) -> list:
    """Every VOI-theater key found (case-insensitive) at any nesting depth inside a
    resolution_plan — the fabricated expected-value-of-information vocabulary 07d bans."""
    hits = []

    def walk(node):
        if isinstance(node, dict):
            for k, v in node.items():
                if isinstance(k, str) and k.lower() in _VOI_BANNED_KEYS:
                    hits.append(k)
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)

    walk(plan)
    return hits


def _resolution_plan_minor_issues(contradictions, claim_ids: set, pivotal_ids: set,
                                  tripwire_ids, dc_present: bool) -> list:
    """07d contradiction-resolution planner validation (schema §7.10 / S11). ALL
    issues are MINOR advisories — this feature never gates the score and never
    touches blocking/major. Each rule fires only when its data is present:

    1. enum membership (approx_effort, decision_impact, evidence_type_needed,
       at-least-one-experiment-or-source);
    2. reference integrity (linked_claims -> real C-###; linked_tripwires -> a real
       tripwire ONLY when decision_tripwires.json exists; linked_options shape only);
    3. 07c consistency (would_flip => at least one linked/own claim is pivotal), one-
       directional and only when decision_criticality.json exists;
    4. gap advisory (an unresolved/open/leaning contradiction with no plan at all);
    5. VOI-theater rejection (fabricated EVSI/EVPI/probability/… fields, or a numeric
       decision_impact/approx_effort).

    ``tripwire_ids`` is None when decision_tripwires.json is absent (skip check 2's
    tripwire arm entirely); ``dc_present`` gates check 3."""
    issues: list = []
    for x in contradictions:
        xid = _contradiction_id(x)
        plan = x.get("resolution_plan")
        status = str(x.get("resolution_status") or "").lower()

        if not isinstance(plan, dict):
            # Rule 4: an open contradiction that gives no guidance at all.
            if status in _OPEN_STATUSES:
                issues.append(
                    f"{xid} is unresolved but has no resolution_plan "
                    "(how to resolve it is not specified)")
            continue

        # Rule 1: enum membership + required content.
        effort = plan.get("approx_effort")
        if not (isinstance(effort, str) and effort in _EFFORT_VALUES):
            issues.append(
                f"{xid} resolution_plan.approx_effort is missing or invalid "
                "(expected low|medium|high)")
        impact = plan.get("decision_impact")
        if not (isinstance(impact, str) and impact in _DECISION_IMPACT_VALUES):
            issues.append(
                f"{xid} resolution_plan.decision_impact is missing or invalid "
                "(expected would_flip|might_flip|unlikely_to_change)")
        ev_type = plan.get("evidence_type_needed")
        if not (isinstance(ev_type, str) and ev_type.strip()):
            issues.append(f"{xid} resolution_plan is missing evidence_type_needed")
        exp = plan.get("proposed_experiment_or_source")
        src = plan.get("data_source")
        has_exp = isinstance(exp, str) and exp.strip()
        has_src = isinstance(src, str) and src.strip()
        if not (has_exp or has_src):
            issues.append(
                f"{xid} resolution_plan names no proposed experiment or data source")

        # Rule 2: reference integrity.
        for cid in plan.get("linked_claims") or []:
            if cid not in claim_ids:
                issues.append(
                    f"{xid} resolution_plan.linked_claims references missing claim {cid}")
        if tripwire_ids is not None:
            for tid in plan.get("linked_tripwires") or []:
                if tid not in tripwire_ids:
                    issues.append(
                        f"{xid} resolution_plan.linked_tripwires references missing "
                        f"tripwire {tid}")
        for opt in plan.get("linked_options") or []:
            if not (isinstance(opt, str) and opt.strip()):
                issues.append(
                    f"{xid} resolution_plan.linked_options contains a blank/non-text entry")

        # Rule 3: 07c consistency — one-directional, would_flip only.
        if dc_present and impact == "would_flip":
            candidates = plan.get("linked_claims") or _contradiction_claim_ids(x)
            if not any(c in pivotal_ids for c in candidates):
                issues.append(
                    f"{xid} resolution_plan.decision_impact is would_flip but none of its "
                    "linked claims are ranked pivotal in decision_criticality.json")

        # Rule 5: VOI-theater rejection.
        for key in _voi_offenders(plan):
            issues.append(
                f"{xid} resolution_plan contains a numeric/probabilistic VOI field "
                f"({key}); Storm Council does not compute expected-value-of-information — "
                "use the ordinal enums only")
        for fld in ("decision_impact", "approx_effort"):
            v = plan.get(fld)
            if v is not None and not isinstance(v, str):
                issues.append(
                    f"{xid} resolution_plan contains a numeric/probabilistic VOI field "
                    f"({fld}); Storm Council does not compute expected-value-of-information — "
                    "use the ordinal enums only")
    return issues


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

    # --- decision-criticality (07c) ----------------------------------------- #
    # Advisory-only, gated entirely on decision_criticality.json existing: an old
    # bundle (or any run that never adopts 07c) sees zero change to its verdict.
    dcf = d / "decision_criticality.json"
    dc_doc = None
    if dcf.exists():
        try:
            dc_doc = json.loads(dcf.read_text(encoding="utf-8"))
        except ValueError:
            dc_doc = None
        contra_ids = {_contradiction_id(x) for x in contradictions}
        minor += _decision_criticality_minor_issues(dc_doc, claim_ids, contra_ids)

    # --- contradiction-resolution planner (07d) ----------------------------- #
    # Advisory-only. Every check is minor and fires only when its own data is
    # present: resolution_plan on a record, decision_criticality.json for the
    # would_flip<->pivotal cross-check, decision_tripwires.json for linked_tripwires.
    # Absent siblings ⇒ those arms skip silently, never an error.
    pivotal_ids = _pivotal_ids_from_dc(dc_doc)
    twf = d / "decision_tripwires.json"
    tripwire_ids = None
    if twf.exists():
        try:
            tw_doc = json.loads(twf.read_text(encoding="utf-8"))
        except ValueError:
            tw_doc = None
        tw_list = tw_doc.get("tripwires") if isinstance(tw_doc, dict) else tw_doc
        tripwire_ids = {t.get("id") for t in tw_list
                        if isinstance(t, dict) and t.get("id")} if isinstance(tw_list, list) else set()
    minor += _resolution_plan_minor_issues(
        contradictions, claim_ids, pivotal_ids, tripwire_ids, dc_doc is not None)

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


# --------------------------------------------------------------------------- #
# Living, re-verifiable brief (07b)
#
# `--recheck` re-resolves each source's publication identity through the SAME
# deterministic adapters shipped in metadata_adapters.py, re-runs the SAME
# verify() used at authoring time, and emits a deterministic before/after diff
# (refresh_diff.json). It is a manual, point-in-time re-check — not a monitor and
# not a scheduler; nothing runs unless invoked. The honesty-critical property is
# that "we checked and it's unchanged", "we checked and it changed", and "we could
# NOT check" are three distinct, never-conflated states (§7 of the 07b plan). Rule
# ordering (§7.1) decides not_rechecked BEFORE any flag comparison, so a source
# that could not be reached can never fall through to "unchanged".
#
# recheck() invents nothing: it never hand-sets a score (verify() does the
# scoring, run twice), never rewrites a claim's evidence_status or a
# contradiction's resolution_status (it reports the conflict; a human/next full
# run decides), and never fabricates a confidence delta.
# --------------------------------------------------------------------------- #

_RECHECK_SCHEMA_VERSION = "7.8"
_RECHECK_ADAPTERS = ["publisher", "crossref", "openalex", "semantic_scholar", "arxiv", "pubmed"]
_NEGATIVE_CHANGE = {"retracted", "superseded", "corrected", "unavailable"}
_VERIFIED_STATUSES = {"PUBLISHED_VERIFIED", "PREPRINT_VERIFIED"}
_UNRESOLVED_STATUSES = {"UNRESOLVED", "METADATA_PARTIAL"}
_GATE_SUMMARY_KEYS = ("status", "coverage_score", "traceability_score",
                      "contradiction_handling_score", "recommendation_support_score")
# gate_changed compares the six keys verify() returns — status + four scores +
# the three issue lists (§7.4) — so a same-tier-but-new-issue change still shows.
_GATE_COMPARE_KEYS = _GATE_SUMMARY_KEYS + ("blocking_issues", "major_issues", "minor_issues")

# Fixed per-change_class detail templates. `not_rechecked` deliberately avoids any
# "confirmed"/"still valid" wording — it is the honest-uncertainty state, not a
# clean bill of health. `unchanged` always carries the "as of this recheck"
# qualifier (asserted by a test) so a verified-negative is never read as permanent.
_CHANGE_DETAIL = {
    "not_rechecked": ("Could not be re-verified this pass (no resolvable "
                      "identifier, or every adapter was offline/uncached). The "
                      "prior status is carried forward, not re-checked."),
    "unchanged": ("Re-resolved via {via}; no retraction/correction/supersession "
                  "relation present. This holds the source is still clean as of "
                  "this recheck — it does not prove nothing will ever change."),
    "retracted": "A retraction relation is now present (via {via}) that was absent before.",
    "superseded": "A supersession/version relation is now present (via {via}) that was absent before.",
    "corrected": "A correction/erratum relation is now present (via {via}) that was absent before.",
    "unavailable": ("This source resolved to a verified identity before but its "
                    "identifier no longer resolves this pass (via {via}); it was "
                    "checkable, and is now unavailable."),
}


def _rec_status(rec) -> str | None:
    if not isinstance(rec, dict):
        return None
    pi = rec.get("publication_identity")
    return pi.get("status") if isinstance(pi, dict) else None


def _change_class(before_rec, after_rec, meta_row) -> str:
    """Per-source change_class decision, exhaustive and deterministic (§7.1).

    Rules 1 and 2 (nothing was queryable / everything was offline) are evaluated
    FIRST and UNCONDITIONALLY, so a source that could not be reached can never
    fall through to "unchanged" by omission — the load-bearing honesty property."""
    checked = meta_row.get("checked") if isinstance(meta_row, dict) else None
    checked = checked or []
    # rule 1: no adapter had a usable identifier to query
    if not checked:
        return "not_rechecked"
    # rule 2: an identifier existed but every adapter was offline/uncached
    if all(entry.get("offline") for entry in checked):
        return "not_rechecked"
    # rule 3: at least one adapter returned live or cached data this pass
    after_flags = (after_rec or {}).get("flags") or {}
    before_flags = (before_rec or {}).get("flags") or {}
    if after_flags.get("retracted") and not before_flags.get("retracted"):
        return "retracted"
    if after_flags.get("superseded") and not before_flags.get("superseded"):
        return "superseded"
    if after_flags.get("corrected") and not before_flags.get("corrected"):
        return "corrected"
    # rule 3d: was verified before, resolves to nothing now despite a live/cached hit
    if _rec_status(before_rec) in _VERIFIED_STATUSES and _rec_status(after_rec) in _UNRESOLVED_STATUSES:
        return "unavailable"
    # rule 3e: flags identical to before, or first clean resolve
    return "unchanged"


def _gate_summary(gate: dict) -> dict:
    return {k: gate.get(k) for k in _GATE_SUMMARY_KEYS}


def _recheck_since(d: Path) -> str | None:
    """Date of the artifact being rechecked: the run manifest's generated_at if
    present, else the quality gate's mtime as a fallback, else None (rendered as
    'first check')."""
    f = d / "run_manifest.json"
    if f.exists():
        try:
            m = json.loads(f.read_text(encoding="utf-8"))
        except ValueError:
            m = None
        if isinstance(m, dict):
            for k in ("generated_at", "created_at", "timestamp"):
                if m.get(k):
                    return str(m[k])[:10]
    g = d / "06_quality_gate.json"
    if g.exists():
        return datetime.fromtimestamp(g.stat().st_mtime, timezone.utc).date().isoformat()
    return None


def _recheck_tripwires(d: Path, change_by_source: dict):
    """Evaluate 08 decision_tripwires.json if present, else return None so the key
    is omitted (never []). A tripwire whose monitoring_source was not_rechecked is
    reported condition_fired=null (unknown, not cleared)."""
    f = d / "decision_tripwires.json"
    if not f.exists():
        return None
    try:
        arr = json.loads(f.read_text(encoding="utf-8"))
    except ValueError:
        return None
    if not isinstance(arr, list):
        return None
    out = []
    for t in arr:
        if not isinstance(t, dict):
            continue
        ms = t.get("monitoring_source")
        cc = change_by_source.get(ms)
        if cc is None or cc == "not_rechecked":
            out.append({"id": t.get("id"), "monitoring_source": ms, "was_rechecked": False,
                        "condition_fired": None,
                        "note": f"monitoring_source {ms} was not_rechecked this pass; "
                                "tripwire status unknown, not cleared"})
        elif cc in _NEGATIVE_CHANGE:
            out.append({"id": t.get("id"), "monitoring_source": ms, "was_rechecked": True,
                        "condition_fired": True,
                        "note": f"monitoring_source {ms} changed to {cc}, matching this "
                                "tripwire's condition"})
        else:
            out.append({"id": t.get("id"), "monitoring_source": ms, "was_rechecked": True,
                        "condition_fired": False,
                        "note": f"monitoring_source {ms} re-resolved unchanged this pass"})
    return out


def _recheck_pivotal(d: Path, touched_claim_ids: list):
    """Cross-reference 07c decision_criticality.json if present, else return None
    so the key is omitted (never []). Reports only claims this pass touched that
    07c marked pivotal — never invents a criticality 07c did not make."""
    f = d / "decision_criticality.json"
    if not f.exists():
        return None
    try:
        data = json.loads(f.read_text(encoding="utf-8"))
    except ValueError:
        return None
    crit = {}
    if isinstance(data, dict) and isinstance(data.get("rankings"), list):
        # 07c canonical shape: rankings[] of {claim_id|contradiction_id, criticality}.
        for r in data["rankings"]:
            if isinstance(r, dict):
                rid = r.get("claim_id") or r.get("contradiction_id")
                if rid:
                    crit[rid] = str(r.get("criticality") or "").lower()
    elif isinstance(data, dict) and isinstance(data.get("claims"), list):
        for c in data["claims"]:
            if isinstance(c, dict) and c.get("claim_id"):
                crit[c["claim_id"]] = str(c.get("criticality") or "").lower()
    elif isinstance(data, dict):
        for k, v in data.items():
            if isinstance(v, str):
                crit[k] = v.lower()
    return [cid for cid in touched_claim_ids if crit.get(cid) == "pivotal"]


def recheck(d, *, as_of=None, fetcher=None, no_retrieve=False, cache_dir=None) -> dict:
    """Re-resolve every source's publication identity and diff the quality gate
    before vs after. Returns the refresh_diff document (§4). Writes source_versions.jsonl
    / metadata_verification.jsonl / retrieval_log.jsonl (via the unchanged
    metadata_adapters seam); writing refresh_diff.json is the caller's job (--write)."""
    import metadata_adapters
    d = Path(d)

    # 1. before gate: the on-disk gate verbatim if present (so the diff reflects
    #    what the reader was actually told), else computed fresh — the same
    #    deterministic verify() run once before the metadata refresh, never faked.
    gate_path = d / "06_quality_gate.json"
    gate_before = None
    if gate_path.exists():
        try:
            gate_before = json.loads(gate_path.read_text(encoding="utf-8"))
        except ValueError:
            gate_before = None
    if not isinstance(gate_before, dict):
        gate_before = verify(d)

    # 2. prior per-source publication-identity records (the flags to diff against).
    before_versions = _load_source_versions(d)

    # 3. metadata refresh through the existing, unmodified seam.
    cache = Path(cache_dir) if cache_dir else (d / ".metadata_cache")
    md = metadata_adapters.verify_publication_identity(
        d, fetcher=fetcher, no_retrieve=no_retrieve, cache_dir=cache)
    after_versions = {r.get("source_id"): r for r in md["source_versions"]}
    meta_by_id = {r.get("source_id"): r for r in md["metadata_verification"]}

    # 4. after gate: the same verify(), re-run now that source_versions.jsonl is refreshed.
    gate_after = verify(d)

    # 5. deterministic diff.
    claims, _, _, contradictions, sources, _ = _load(d)
    source_changes = []
    change_by_source: dict = {}
    for s in sources:
        sid = s.get("source_id")
        if not sid:
            continue
        before_rec = before_versions.get(sid)
        after_rec = after_versions.get(sid)
        meta_row = meta_by_id.get(sid) or {}
        cc = _change_class(before_rec, after_rec, meta_row)
        change_by_source[sid] = cc
        checked = meta_row.get("checked") or []
        via = [entry.get("adapter") for entry in checked
               if entry.get("adapter") and not entry.get("offline")]
        if cc == "not_rechecked":
            # carried forward unchanged, NEVER inferred as confirmed.
            before_status = after_status = _rec_status(before_rec)
        else:
            before_status = _rec_status(before_rec)
            after_status = _rec_status(after_rec)
        source_changes.append({
            "source_id": sid,
            "change_class": cc,
            "before_status": before_status,
            "after_status": after_status,
            "detected_via": via,
            "detail": _CHANGE_DETAIL[cc].format(via=", ".join(via) or "cache"),
        })

    claim_changes = []
    for c in claims:
        cid = c.get("claim_id")
        if not cid:
            continue
        status = c.get("evidence_status")
        sids = list(c.get("source_ids") or [])
        weak_sources = [sid for sid in sids if change_by_source.get(sid) in _NEGATIVE_CHANGE]
        if status in _SUPPORTED and weak_sources:
            cls = change_by_source.get(weak_sources[0])
            claim_changes.append({
                "claim_id": cid,
                "direction": "weakened",
                "rule": f"supported_claim_cites_now_{cls}_source",
                "source_ids": weak_sources,
                "before_evidence_status": status,
                "after_evidence_status": status,   # verify.py never auto-rewrites evidence_status
                "note": (f"Cites now-{cls} source(s) {', '.join(weak_sources)}; verify.py raises "
                         "this as a new blocking/major issue on recheck (see gate_after). The "
                         "claim's evidence_status is not auto-edited — a human decides."),
            })
            continue
        # strengthened (narrow, §7.3): a source this claim cites was flagged
        # before and now resolves clean this pass. Never "strengthened" merely
        # because nothing changed.
        strengthened_sources = []
        for sid in sids:
            bf = ((before_versions.get(sid) or {}).get("flags") or {})
            af = ((after_versions.get(sid) or {}).get("flags") or {})
            was_flagged = bf.get("superseded") or bf.get("corrected") or bf.get("retracted")
            now_clean = not (af.get("superseded") or af.get("corrected") or af.get("retracted"))
            if was_flagged and now_clean and change_by_source.get(sid) == "unchanged":
                strengthened_sources.append(sid)
        if status in _SUPPORTED and strengthened_sources:
            claim_changes.append({
                "claim_id": cid,
                "direction": "strengthened",
                "rule": "previously_flagged_source_now_resolves_clean",
                "source_ids": strengthened_sources,
                "before_evidence_status": status,
                "after_evidence_status": status,
                "note": (f"A source this claim cites ({', '.join(strengthened_sources)}) was "
                         "flagged (superseded/corrected/retracted) before and now resolves clean."),
            })

    contradiction_changes = []
    for x in contradictions:
        xid = _contradiction_id(x)
        if xid == "?":
            continue
        st = x.get("resolution_status") or "unresolved"
        ref_claim_ids = set(_contradiction_claim_ids(x))
        touched = sorted({
            sid for c in claims if c.get("claim_id") in ref_claim_ids
            for sid in (c.get("source_ids") or [])
            if change_by_source.get(sid) in _NEGATIVE_CHANGE
        })
        if touched:
            reason = (f"referenced source(s) {', '.join(touched)} changed class this pass; "
                      "resolution_status is unchanged (recheck does not re-adjudicate contradictions)")
        else:
            reason = "no source referenced by this contradiction's claims changed class"
        contradiction_changes.append({
            "id": xid, "status_before": st, "status_after": st, "reason": reason,
        })

    performed = _seal_now()
    n_not = sum(1 for r in source_changes if r["change_class"] == "not_rechecked")
    diff = {
        "schema_version": _RECHECK_SCHEMA_VERSION,
        "recheck": {
            "performed_at": performed,
            "as_of": as_of or performed[:10],
            "since": _recheck_since(d),
            "offline": bool(no_retrieve),
            "cache_dir": str(cache),
            "adapters_available": list(_RECHECK_ADAPTERS),
            "sources_considered": len(source_changes),
            "sources_rechecked": len(source_changes) - n_not,
            "sources_not_rechecked": n_not,
        },
        "source_changes": source_changes,
        "claim_changes": claim_changes,
        "contradiction_changes": contradiction_changes,
        "gate_before": _gate_summary(gate_before),
        "gate_after": _gate_summary(gate_after),
        "gate_changed": any(gate_before.get(k) != gate_after.get(k) for k in _GATE_COMPARE_KEYS),
    }
    tripwires = _recheck_tripwires(d, change_by_source)
    if tripwires is not None:
        diff["tripwires_evaluated"] = tripwires
    pivotal = _recheck_pivotal(d, [cc["claim_id"] for cc in claim_changes])
    if pivotal is not None:
        diff["pivotal_claims_touched"] = pivotal
    return diff


def _refresh_report_md(diff: dict) -> str:
    """Plain-Markdown mirror of refresh_diff.json — a derived convenience, never a
    second source of truth."""
    r = diff.get("recheck") or {}
    since = r.get("since") or "first check"
    lines = [f"# What changed since {since}", ""]
    lines.append(f"- Re-checked {r.get('sources_rechecked', 0)} of "
                 f"{r.get('sources_considered', 0)} sources"
                 + (" (offline)" if r.get("offline") else "")
                 + f", as of {r.get('as_of', '?')}.")
    gb = (diff.get("gate_before") or {}).get("status")
    ga = (diff.get("gate_after") or {}).get("status")
    if diff.get("gate_changed"):
        lines.append(f"- Quality gate moved: **{gb} → {ga}**.")
    else:
        lines.append(f"- Quality gate did not move ({ga}).")
    lines += ["", "## Sources", ""]
    for row in diff.get("source_changes") or []:
        lines.append(f"- `{row['source_id']}` — **{row['change_class']}**: {row['detail']}")
    if diff.get("claim_changes"):
        lines += ["", "## Claims", ""]
        for cc in diff["claim_changes"]:
            lines.append(f"- `{cc['claim_id']}` — {cc['direction']} ({cc['rule']}): "
                         f"{', '.join(cc.get('source_ids') or [])}")
    return "\n".join(lines) + "\n"


def _write_quality_gate(d: Path, gate: dict) -> None:
    """Write 06_quality_gate.json and patch report_data.json's status/review — the
    shared --write side-effect used by both plain verify and --recheck."""
    (d / "06_quality_gate.json").write_text(
        json.dumps(gate, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    rf = d / "report_data.json"
    if rf.exists():
        report = json.loads(rf.read_text(encoding="utf-8"))
        scores = {"coverage": gate["coverage_score"], "traceability": gate["traceability_score"],
                  "contradiction": gate["contradiction_handling_score"],
                  "recommendation": gate["recommendation_support_score"]}
        report.setdefault("status", {})["verdict"] = gate["status"]
        report["status"]["scores"] = scores
        report["review"] = {"verdict": gate["status"], "scores": scores,
                            "blocking": gate["blocking_issues"], "major": gate["major_issues"],
                            "minor": gate["minor_issues"]}
        rf.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _run_recheck(d: Path, args) -> int:
    cache = args.cache or str(d / ".metadata_cache")
    diff = recheck(d, as_of=args.as_of, no_retrieve=args.offline, cache_dir=cache)
    r = diff["recheck"]
    print(f"recheck: {r['sources_rechecked']} of {r['sources_considered']} sources re-checked "
          f"(as of {r['as_of']}, since {r['since'] or 'first check'})"
          + (" [offline]" if r["offline"] else ""))
    tally: dict = {}
    for row in diff["source_changes"]:
        tally[row["change_class"]] = tally.get(row["change_class"], 0) + 1
    for k in ("retracted", "superseded", "corrected", "unavailable", "unchanged", "not_rechecked"):
        if tally.get(k):
            print(f"  {k}: {tally[k]}")
    gb, ga = diff["gate_before"]["status"], diff["gate_after"]["status"]
    print(f"  quality gate moved: {gb} -> {ga}" if diff["gate_changed"]
          else f"  quality gate did not move ({ga})")

    if args.write:
        gate = verify(d)  # == gate_after; source_versions.jsonl already refreshed
        _write_quality_gate(d, gate)
        (d / "refresh_diff.json").write_text(
            json.dumps(diff, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        (d / "refresh_report.md").write_text(_refresh_report_md(diff), encoding="utf-8")
        print("wrote refresh_diff.json, refresh_report.md, 06_quality_gate.json (after gate)")
        # 07a re-seal so provenance_manifest.json covers the refreshed artifacts.
        _run_seal(d)

    if args.strict and diff["gate_after"]["status"] in {"REVISE", "BLOCKED_PENDING_EVIDENCE"}:
        return 2
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Verify a Storm Council output dir and compute the quality gate.")
    ap.add_argument("output_dir")
    ap.add_argument("--write", action="store_true", help="write 06_quality_gate.json and patch report_data.json")
    ap.add_argument("--strict", action="store_true", help="exit 2 on REVISE / BLOCKED_PENDING_EVIDENCE")
    ap.add_argument(
        "--recheck", action="store_true",
        help="re-resolve every source's publication identity through the shipped "
             "metadata adapters, re-run verify(), and emit a before/after diff "
             "(refresh_diff.json under --write). A manual, point-in-time re-check "
             "of 'what changed since' the brief was written — it schedules nothing "
             "and watches nothing on its own.")
    ap.add_argument(
        "--as-of", dest="as_of", metavar="DATE",
        help="ISO date (YYYY-MM-DD) recorded as the 'as of' label in refresh_diff.json. "
             "A label only: it does NOT fetch historical metadata (the adapters cannot "
             "ask an API what it said on a past date). Defaults to today.")
    ap.add_argument(
        "--offline", action="store_true",
        help="pass no_retrieve=True to the metadata adapters: use only cached "
             "responses. With an empty cache every source becomes 'not_rechecked' "
             "(an honest 'we did not check', never 'unchanged').")
    ap.add_argument(
        "--cache", dest="cache", metavar="DIR",
        help="cache dir for adapter responses (default <output_dir>/.metadata_cache). "
             "Point at a fresh directory to force fresh re-resolution — a stale cache "
             "returns the old response and would report 'unchanged'.")
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

    if args.recheck:
        return _run_recheck(d, args)

    gate = verify(d)

    print(f"verdict: {gate['status']}")
    print(f"  coverage {gate['coverage_score']} · traceability {gate['traceability_score']} · "
          f"contradiction-handling {gate['contradiction_handling_score']} · "
          f"recommendation-support {gate['recommendation_support_score']}")
    for sev in ("blocking_issues", "major_issues", "minor_issues"):
        for msg in gate[sev]:
            print(f"  [{sev.split('_')[0]}] {msg}")

    if args.write:
        _write_quality_gate(d, gate)
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
