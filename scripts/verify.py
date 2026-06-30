#!/usr/bin/env python3
"""Verify a Storm Council output directory and compute the quality gate.

Pure standard library. No network, no LLM, no API key. This is the deterministic
half of the workflow's honesty guarantee: the *reasoning* is the model's, but the
*verification and scoring* are computed here from the artifacts the skill wrote.

Reads (from the output directory):
  - 03_claims.jsonl          one claim record per line
  - 04_contradictions.json   array of contradiction records
  - 03_source_registry.csv   the source registry (source_id, source_type, ...)
  - report_data.json         (optional) for option/action recommendation scoring

Checks reference integrity and citation rules, then computes four scores and a
verdict (PASS / PASS_WITH_CAVEATS / REVISE / BLOCKED_PENDING_EVIDENCE).

Usage:
  python3 verify.py <output_dir>            # print the report, exit 0
  python3 verify.py <output_dir> --write    # write 06_quality_gate.json + patch report_data.json
  python3 verify.py <output_dir> --strict   # exit 2 on REVISE / BLOCKED
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import re
import sys
from pathlib import Path

_ID = re.compile(r"\b[CSX]-\d{3,}\b")
_LOW_QUALITY = {"blog", "other", "news"}
_EVIDENCE_BEARING = {"supported", "partially_supported", "contested"}
_STRONG_TYPES = {"fact", "inference", "recommendation"}


def _load(d: Path):
    claims = []
    cf = d / "03_claims.jsonl"
    if cf.exists():
        for line in cf.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                claims.append(json.loads(line))
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
    return claims, contradictions, sources, report


def _pct(num: int, den: int) -> int:
    return round(100 * num / den) if den else 0


def verify(d: Path) -> dict:
    claims, contradictions, sources, report = _load(d)
    claim_ids = {c.get("claim_id") for c in claims}
    src_ids = {s.get("source_id") for s in sources}

    link_errors, citation_free = [], []
    for c in claims:
        cid = c.get("claim_id", "?")
        for sid in c.get("source_ids", []):
            if sid not in src_ids:
                link_errors.append(f"{cid} cites missing source {sid}")
        for xid in c.get("counterevidence_ids", []):
            if xid not in claim_ids:
                link_errors.append(f"{cid} references missing counter-claim {xid}")
        if (c.get("claim_type") in {"fact", "inference"}
                and c.get("evidence_status") in {"supported", "partially_supported"}
                and not c.get("source_ids")):
            citation_free.append(f"{cid} ({c.get('claim_type')}/{c.get('evidence_status')}) cites no source")
    for x in contradictions:
        for k in ("claim_a_id", "claim_b_id"):
            if x.get(k) not in claim_ids:
                link_errors.append(f"{x.get('conflict_id','?')} references missing claim {x.get(k)}")

    def _is_low(s):
        note = (s.get("credibility_notes") or "").lower()
        return s.get("source_type") in _LOW_QUALITY or "synthetic" in note or "low" in note
    low_cred = [s.get("source_id") for s in sources if _is_low(s)]
    low_set = set(low_cred)
    supported_on_low = [
        f"{c.get('claim_id')}->{sid}"
        for c in claims if c.get("evidence_status") == "supported"
        for sid in c.get("source_ids", []) if sid in low_set
    ]
    unsupported_strong = [
        f"{c.get('claim_id')} ({c.get('claim_type')})"
        for c in claims
        if c.get("claim_type") in _STRONG_TYPES and c.get("evidence_status") == "unsupported"
    ]

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
        handled = [x for x in contradictions
                   if x.get("resolution_status") in {"resolved", "partially_resolved"}]
        contradiction_handling = _pct(len(handled), len(contradictions))
    else:
        contradiction_handling = 50

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

    supported_share = (len([c for c in claims if c.get("evidence_status") in {"supported", "partially_supported"}]) / len(claims)) if claims else 0.0
    evidence_absent = (not sources) or supported_share < 0.2

    blocking = [f"Citation integrity: {e}" for e in link_errors]
    blocking += [f"Citation-free conclusion: {e}" for e in citation_free]
    if evidence_absent:
        blocking.append("Insufficient evidence: no resolvable sources support the claims.")

    major = []
    if unsupported_strong:
        major.append("Unsupported strong claims: " + "; ".join(unsupported_strong))
    if supported_on_low:
        major.append("Supported claims depend on low-credibility sources: " + "; ".join(supported_on_low))
    if (options or actions) and recommendation < 50:
        major.append(f"Recommendations weakly justified (support score {recommendation}).")

    minor = []
    if low_cred:
        minor.append("Low-credibility sources present: " + ", ".join(sorted(low_cred)))
    open_x = [x.get("conflict_id") for x in contradictions if x.get("resolution_status") == "unresolved"]
    if open_x:
        minor.append("Open contradictions remain for human review: " + ", ".join(open_x))

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
                          f"{len(contradictions)} contradictions).",
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Verify a Storm Council output dir and compute the quality gate.")
    ap.add_argument("output_dir")
    ap.add_argument("--write", action="store_true", help="write 06_quality_gate.json and patch report_data.json")
    ap.add_argument("--strict", action="store_true", help="exit 2 on REVISE / BLOCKED_PENDING_EVIDENCE")
    args = ap.parse_args(argv)
    d = Path(args.output_dir)
    if not d.is_dir():
        print(f"error: {d} is not a directory", file=sys.stderr)
        return 1
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

    if args.strict and gate["status"] in {"REVISE", "BLOCKED_PENDING_EVIDENCE"}:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
