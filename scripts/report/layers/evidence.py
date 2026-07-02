"""Evidence table."""

from __future__ import annotations


from report.components.badges import _evidence_source_badges, _evidence_verdicts_html, _locator_text, _verdicts_by_evidence
from report.components.base import _field_details, e, refs, text_refs


# A3: a "full_text" packet whose stored excerpt is shorter than this is really a
# passage/snippet — the renderer must never present it as full text. (B1 is the
# authoritative upstream fix; this keeps the renderer from upgrading the label.)
_FULL_TEXT_MIN_CHARS = 1000
_FULL_TEXT_TOKENS = {"full_text", "full text", "fulltext"}


def _honest_extraction_label(method, excerpt) -> str:
    m = str(method or "").strip()
    if m.lower() in _FULL_TEXT_TOKENS and len(str(excerpt or "")) < _FULL_TEXT_MIN_CHARS:
        return "passage"
    return m or "—"


def _evidence_table_html(evidence, sources_by_id=None, verdicts=None) -> str:
    if not isinstance(evidence, list) or not evidence:
        return ""
    verdicts_by_eid = _verdicts_by_evidence(verdicts)
    rows = ""
    for ev in evidence:
        if not isinstance(ev, dict):
            continue
        eid = ev.get("evidence_id") or ev.get("id") or ""
        sid = ev.get("source_id") or ""
        loc = _locator_text(ev.get("locator"))
        excerpt = ev.get("evidence_excerpt") or ev.get("excerpt") or ""
        method = _honest_extraction_label(ev.get("extraction_method"), excerpt)
        badges = _evidence_source_badges(ev, sources_by_id)
        verdict_html = _evidence_verdicts_html(eid, verdicts_by_eid)
        detail_html = _field_details((
            ("supports_claims", ev.get("supports_candidate_claims")),
            ("extracted_by", ev.get("extracted_by")),
            ("notes", ev.get("notes")),
        ), "Evidence details")
        rows += (
            '<tr id="ref-%s"><td class="mono">%s</td><td>%s</td><td>%s</td>'
            '<td class="excerpt">%s</td><td>%s</td><td><span class="tag kind">%s</span></td><td>%s</td><td>%s</td></tr>'
            % (e(eid), e(eid), refs([sid]) if sid else "—", text_refs(loc) if loc else "—",
               text_refs(excerpt) if excerpt else "—", verdict_html, e(method or "—"), badges, detail_html)
        )
    if not rows:
        return ""
    return (
        '<table class="evidence-table"><thead><tr><th>ID</th><th>Source</th><th>Locator</th>'
        '<th>Excerpt</th><th>Verdict</th><th>Method</th><th>Status</th><th>Details</th></tr></thead><tbody>'
        + rows + '</tbody></table>'
    )
