"""Source-class, evidence, verdict, and move badge fragments."""

from __future__ import annotations


from report.components.base import e, refs, text_refs


_STRENGTH = {"strong": ("s-strong", "evidence: strong"), "moderate": ("s-mod", "evidence: moderate"),
             "weak": ("s-weak", "evidence: weak"), "unsupported": ("s-none", "unsupported")}


_CONFLICT = {"unresolved": ("open", "unresolved"), "partly": ("part", "partly"),
             "partially_resolved": ("part", "partly"), "resolved": ("done", "resolved")}


_EVIDENCE_TAG = {
    "supported": ("done", "supported"),
    "partially_supported": ("part", "partial"),
    "partial": ("part", "partial"),
    "unsupported": ("open", "unsupported"),
    "contested": ("open", "contested"),
    "refuted": ("open", "refuted"),
}


_MOVE_TAG = {
    "support": ("done", "support"),
    "challenge": ("open", "challenge"),
    "qualification": ("part", "qualification"),
    "request-for-evidence": ("kind", "request evidence"),
    "request-evidence": ("kind", "request evidence"),
    "reframing": ("kind", "reframing"),
}


_SOURCE_CLASS_LABELS = {
    "peer_reviewed": "peer-reviewed",
    "preprint": "preprint",
    "official": "official",
    "gray": "gray literature",
    "run_log": "run log",
}


def _locator_text(locator) -> str:
    if not isinstance(locator, dict):
        return ""
    parts = []
    labels = (("page", "page"), ("section", "section"), ("subsection", "subsection"),
              ("table", "table"), ("figure", "figure"), ("equation", "equation"),
              ("clause", "clause"), ("paragraph_hint", "paragraph"))
    for key, label in labels:
        val = locator.get(key)
        if val is not None and str(val).strip() and str(val).lower() != "null":
            parts.append(f"{label} {val}" if key in {"page", "section", "subsection", "clause"} else str(val))
    return "; ".join(parts)


def _evidence_source_badges(ev: dict, sources_by_id: dict) -> str:
    badges = []
    method = (ev.get("extraction_method") or "").lower()
    if method == "abstract":
        badges.append('<span class="tag kind">abstract-only</span>')
    elif method == "metadata":
        badges.append('<span class="tag kind">metadata-only</span>')
    src = sources_by_id.get(ev.get("source_id") or "") if sources_by_id else None
    if src:
        pi = src.get("publication_identity") or {}
        rs = (pi.get("retraction_status") or src.get("publication_status") or "").lower()
        if "retract" in rs:
            badges.append('<span class="tag open">retracted</span>')
        elif "supersed" in rs:
            badges.append('<span class="tag part">superseded</span>')
        cs = (pi.get("correction_status") or "").lower()
        if "corrected" in cs:
            badges.append('<span class="tag part">corrected</span>')
    return " ".join(badges)


def _source_identity_badges(src: dict) -> str:
    pi = src.get("publication_identity") if isinstance(src.get("publication_identity"), dict) else {}
    flags = src.get("flags") if isinstance(src.get("flags"), dict) else {}
    status = (pi.get("status") or "UNRESOLVED").upper()
    badges = []
    if flags.get("retracted") or status == "RETRACTED" or (pi.get("retraction_status") or "").lower() == "retracted":
        badges.append('<span class="tag open">retracted</span>')
    elif flags.get("superseded") or status == "SUPERSEDED":
        badges.append('<span class="tag part">superseded</span>')
    elif flags.get("corrected") or status == "CORRECTED" or (pi.get("correction_status") or "").lower() == "corrected":
        badges.append('<span class="tag part">corrected</span>')
    elif flags.get("duplicate_version") or status == "DUPLICATE_VERSION":
        badges.append('<span class="tag part">duplicate version</span>')
    elif status in {"UNRESOLVED", "METADATA_PARTIAL"}:
        badges.append(f'<span class="tag kind">{e(status)}</span>')
    elif status:
        badges.append(f'<span class="tag done">{e(status)}</span>')
    return " ".join(badges)


def _source_class_badges(src: dict) -> str:
    """Badge a source's provenance class and an abstract-only access status.
    Rendered only when the fields are present, so pre-Phase-3 reports (which omit
    them) stay unchanged. ``run_log`` and ``abstract_only`` get an amber tone to
    signal weaker standing; the other classes are neutral."""
    badges = []
    klass = (src.get("source_class") or "").strip().lower()
    if klass in _SOURCE_CLASS_LABELS:
        tone = "part" if klass == "run_log" else "kind"
        badges.append(f'<span class="tag {tone}">{e(_SOURCE_CLASS_LABELS[klass])}</span>')
    if (src.get("full_text_status") or "").strip().lower() == "abstract_only":
        badges.append('<span class="tag part">abstract-only</span>')
    return " ".join(badges)


def _verdicts_by_evidence(verdicts) -> dict:
    by_evidence: dict = {}
    if not isinstance(verdicts, list):
        return by_evidence
    for v in verdicts:
        if not isinstance(v, dict):
            continue
        eid = v.get("evidence_id")
        if eid:
            by_evidence.setdefault(eid, []).append(v)
    return by_evidence


def _verdict_badge_html(v: dict) -> str:
    verdict = str(v.get("verdict") or "").lower()
    scope = str(v.get("scope_preserved") or "").lower()
    if verdict == "does_not_entail" or scope == "overclaimed":
        cls = "verdict-bad"
    elif verdict in {"partial", "uncertain"} or scope in {"narrowed", "uncertain"}:
        cls = "verdict-warn"
    else:
        cls = "verdict-ok"
    claim = v.get("claim_id")
    rationale = v.get("rationale") or ""
    judged = v.get("judged_claim") or ""
    review = " · review" if v.get("human_review_required") else ""
    return (
        '<div class="verdict-row">%s'
        '<span class="tag %s">%s</span>'
        '<span class="tag kind">scope: %s%s</span></div>%s'
        % (
            refs([claim]) if claim else "",
            cls,
            e(verdict or "—"),
            e(scope or "—"),
            review,
            (
                (f'<span class="verdict-rationale">Judged: {text_refs(judged)}</span>' if judged else "")
                + (f'<span class="verdict-rationale">{text_refs(rationale)}</span>' if rationale else "")
            ),
        )
    )


def _evidence_verdicts_html(eid: str, verdicts_by_eid: dict) -> str:
    verdicts = verdicts_by_eid.get(eid) or []
    if not verdicts:
        return "—"
    return '<div class="verdict-list">' + "".join(_verdict_badge_html(v) for v in verdicts) + "</div>"
