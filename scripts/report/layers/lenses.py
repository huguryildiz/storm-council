"""Lens sections: perspective snapshot radar, evidence plan, lens plans, charters."""

from __future__ import annotations

import re
import math

from report.components.base import _md_block, _rich_text, e, text_refs
from report.components.icons import _LENS_DOT, _lens_icon_ca, _lens_icon_svg


def _clamped_score(value) -> float:
    try:
        score = float(value)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(1.0, score))


def _radar_point(cx: float, cy: float, radius: float, angle_deg: float) -> tuple[float, float]:
    angle = math.radians(angle_deg)
    return cx + radius * math.cos(angle), cy + radius * math.sin(angle)


def _fmt_points(points: list[tuple[float, float]]) -> str:
    return " ".join(f"{x:.1f},{y:.1f}" for x, y in points)


def _lens_snapshot_html(snapshot) -> str:
    """Qualitative council-posture summary (A5).

    The old version drew a radar from invented 0–1 "posture intensity" decimals
    about role-play personas — fake precision no caption could rescue. This renders
    one plain-language posture line per lens (tone dot + stance), with no numbers
    and no chart, so nothing reads as a measurement."""
    if not isinstance(snapshot, dict):
        return ""
    lenses = [x for x in snapshot.get("lenses", []) if isinstance(x, dict)]
    if len(lenses) < 3:
        return ""

    rows = ""
    tone_classes = {"support", "challenge", "caution", "mixed"}
    for lens in lenses:
        name = str(lens.get("name", "")).replace("_", " ").title()
        tone = str(lens.get("tone", "")).lower()
        tone_class = tone if tone in tone_classes else ""
        stance = lens.get("stance") or lens.get("note") or ""
        rows += (
            '<div class="lens-row">'
            f'<span class="lens-name"><span class="lens-tone {e(tone_class)}"></span>{e(name)}</span>'
            f'<span class="lens-stance">{e(stance)}</span>'
            '</div>'
        )

    summary = snapshot.get("summary") or "A compact view of where each council lens stands on the decision."
    title = snapshot.get("title") or "Lens posture snapshot"
    return (
        '<div class="lens-posture">'
        f'<p class="lens-radar-kicker">{e(title)}</p>'
        f'<p class="lens-radar-summary">{text_refs(summary)}</p>'
        '<p class="lens-radar-note">This is a qualitative council posture map, not a quality score.</p>'
        f'<div class="lens-list">{rows}</div>'
        '</div>'
    )


def _evidence_plan_html(text: str) -> str:
    """Render evidence plan: query-result lines become premium cards; everything else uses _md_block."""
    import re
    query_re = re.compile(r'^- `(.+?)`: result_count=(\d+)')
    paper_re = re.compile(
        r'selected/top result: (.+?)'
        r'(?: \| authors: (.+?))?'
        r'(?: \| venue: (.+?))?'
        r' \| paperId=(\w+) \| year=(\d+) \| citationCount=(\d+)'
    )

    # Split off the "Lens Plans" subsection — it gets dedicated premium-card treatment.
    all_lines = text.splitlines()
    lp_re = re.compile(r'^#{2,}\s+lens plans\s*$', re.IGNORECASE)
    split_at = next((k for k, ln in enumerate(all_lines) if lp_re.match(ln.strip())), None)
    if split_at is not None:
        lens_html = _lens_plans_html("\n".join(all_lines[split_at + 1:]))
        lines = all_lines[:split_at]
    else:
        lens_html = ""
        lines = all_lines

    out: list[str] = []
    i = 0

    while i < len(lines):
        raw = lines[i]
        s = raw.strip()
        indent = len(raw) - len(raw.lstrip(" "))
        m = query_re.match(s) if indent < 2 else None

        if m:
            # Collect all consecutive top-level query bullets into one card grid
            cards = []
            while i < len(lines):
                raw2 = lines[i]
                s2 = raw2.strip()
                indent2 = len(raw2) - len(raw2.lstrip(" "))
                m2 = query_re.match(s2) if indent2 < 2 else None
                if m2:
                    query, count = m2.group(1), int(m2.group(2))
                    sub: list[str] = []
                    i += 1
                    while i < len(lines):
                        sub_raw = lines[i]
                        sub_s = sub_raw.strip()
                        sub_ind = len(sub_raw) - len(sub_raw.lstrip(" "))
                        if sub_ind >= 2 and (sub_s.startswith("- ") or sub_s.startswith("* ")):
                            sub.append(sub_s[2:])
                            i += 1
                        elif not sub_s:
                            i += 1
                            break
                        else:
                            break
                    cards.append((query, count, sub))
                else:
                    break

            out.append('<div class="qcard-grid">')
            for query, count, sub in cards:
                tone = "zero" if count == 0 else "hits"
                badge = f'<span class="qbadge {tone}">{count} result{"s" if count != 1 else ""}</span>'
                results_html = ""
                if sub:
                    rows = []
                    for item in sub:
                        pm = paper_re.match(item)
                        if pm:
                            title, authors, venue, paper_id, year, cites = (
                                pm.group(1), pm.group(2), pm.group(3), pm.group(4), pm.group(5), pm.group(6)
                            )
                            ss_url = f"https://www.semanticscholar.org/paper/{paper_id}"
                            authors_html = (
                                f'<span class="qauthors">{_rich_text(authors)}</span> '
                                if authors else ""
                            )
                            venue_html = (
                                f' <em class="qvenue">{_rich_text(venue)}.</em>'
                                if venue else ""
                            )
                            rows.append(
                                f'<div class="qresult">'
                                f'<span class="qtitle">'
                                f'{authors_html}'
                                f'({year}). '
                                f'<a href="{ss_url}" target="_blank" rel="noopener">{_rich_text(title)}</a>.'
                                f'{venue_html}'
                                f'</span>'
                                f'<span class="qcite">cited by {cites}</span>'
                                f'</div>'
                            )
                        else:
                            rows.append(f'<div class="qresult"><span class="qnull">{_rich_text(item)}</span></div>')
                    results_html = f'<div class="qresults">{"".join(rows)}</div>'
                out.append(
                    f'<div class="qcard">'
                    f'<div class="qhead"><code class="qterm">{_rich_text(query)}</code>{badge}</div>'
                    f'{results_html}</div>'
                )
            out.append('</div>')
        else:
            # Collect non-query lines and pass through _md_block
            buf: list[str] = []
            while i < len(lines):
                raw2 = lines[i]
                s2 = raw2.strip()
                ind2 = len(raw2) - len(raw2.lstrip(" "))
                if query_re.match(s2) and ind2 < 2:
                    break
                buf.append(raw2)
                i += 1
            if buf:
                out.append(_md_block("\n".join(buf)))

    return "".join(out) + lens_html


def _lens_plans_html(text: str) -> str:
    """Render the Lens Plans subsection as premium per-lens cards.

    Each `### lens` block carries one paragraph of the form
    "Queries and sources: …. Disconfirming evidence would be …." — split into a
    labeled retrieval field and a highlighted falsification field.
    """
    import re
    lines = text.splitlines()
    cards: list[str] = []
    i = 0
    while i < len(lines):
        s = lines[i].strip()
        h = re.match(r'^#{2,}\s+(.+?)\s*$', s)
        if not h:
            i += 1
            continue
        name = h.group(1).strip()
        i += 1
        body: list[str] = []
        while i < len(lines) and not re.match(r'^#{2,}\s+', lines[i].strip()):
            if lines[i].strip():
                body.append(lines[i].strip())
            i += 1
        para = " ".join(body).strip()
        if not para:
            continue

        idx = para.find("Disconfirming evidence")
        if idx != -1:
            queries = para[:idx].strip()
            falsify = para[idx:].strip()
        else:
            queries, falsify = para, ""
        queries = re.sub(r'^Queries and sources:\s*', '', queries).strip().rstrip('.').strip()
        falsify = re.sub(r'^Disconfirming evidence\s+(?:would be|is|=)?\s*', '', falsify).strip()

        dot = _LENS_DOT.get(name.lower(), "var(--brand)")
        parts = [
            '<div class="lplan">',
            f'<div class="lplan-head">{_lens_icon_svg(name, dot)}'
            f'<span class="lplan-name">{e(name)}</span></div>',
        ]
        if queries:
            parts.append(
                '<div class="lplan-field">'
                '<span class="lplan-label">Queries &amp; sources</span>'
                f'<div class="lplan-val">{_rich_text(queries)}</div></div>'
            )
        if falsify:
            parts.append(
                '<div class="lplan-falsify">'
                '<span class="lplan-label">Disconfirming evidence</span>'
                f'<div class="lplan-val">{_rich_text(falsify)}</div></div>'
            )
        parts.append('</div>')
        cards.append("".join(parts))

    if not cards:
        return ""
    return (
        '<p class="lplan-kicker">Lens plans</p>'
        '<p class="lplan-intro">What each lens set out to retrieve — and the evidence '
        'that would have changed its mind.</p>'
        f'<div class="lplan-grid">{"".join(cards)}</div>'
    )


def _lens_charter_table_html(charters) -> str:
    """Compact one-row-per-lens charter table for the reader path (A7): lens ·
    charter · main pressure. The five full charter cards (priority questions,
    blind spots, escalation triggers) predict conflicts the ledger then records —
    that scaffolding moves to the appendix; this table is what the reader needs."""
    if not isinstance(charters, list):
        return ""
    rows = ""
    for ch in charters:
        if not isinstance(ch, dict):
            continue
        name = str(ch.get("name") or ch.get("lens") or "").replace("_", " ")
        role = (ch.get("role_charter") or ch.get("focus")
                or ch.get("charter") or ch.get("role_focus") or "")
        pressure = (ch.get("potential_conflicts") or ch.get("conflicts_with_other_lenses")
                    or ch.get("escalation_triggers") or ch.get("likely_blind_spots")
                    or ch.get("likely_blind_spot") or "")
        if isinstance(pressure, str):
            pressure = [pressure]
        pressure = "; ".join(str(v) for v in pressure if v) if isinstance(pressure, list) else str(pressure)
        slug = re.sub(r'[^a-z0-9]+', '-', name.lower().strip('-'))
        icon = _lens_icon_ca(slug)
        rows += (
            f'<tr><td class="charter-lens">{icon}<span style="text-transform:capitalize">{e(name)}</span></td>'
            f'<td>{text_refs(role)}</td>'
            f'<td>{text_refs(pressure) if pressure else "—"}</td></tr>'
        )
    if not rows:
        return ""
    return (
        '<table class="charter-table"><thead><tr><th>Lens</th><th>Charter</th>'
        f'<th>Main pressure it applies</th></tr></thead><tbody>{rows}</tbody></table>'
    )


def _lens_charters_html(charters) -> str:
    if not isinstance(charters, list):
        return ""
    cards = ""
    for ch in charters:
        if not isinstance(ch, dict):
            continue
        # Normalise alternate field-name conventions produced by different run sessions
        _blind = ch.get("likely_blind_spots") or (
            [ch["likely_blind_spot"]] if ch.get("likely_blind_spot") else [])
        _conflicts = ch.get("potential_conflicts") or ch.get("conflicts_with_other_lenses") or []
        ch = dict(ch,
                  name=ch.get("name") or ch.get("lens", ""),
                  role_charter=(ch.get("role_charter") or ch.get("focus")
                                or ch.get("charter") or ch.get("role_focus", "")),
                  likely_blind_spots=_blind,
                  potential_conflicts=_conflicts)
        name = str(ch.get("name", "")).replace("_", " ")
        role = ch.get("role_charter", "")

        def block(key, head, as_list, _ch=ch):
            vals = _ch.get(key) or []
            if isinstance(vals, str):
                vals = [vals]
            vals = [v for v in vals if v]
            if not vals:
                return ""
            if as_list:
                items = "".join(f"<li>{text_refs(v)}</li>" for v in vals)
                inner = f"<ul>{items}</ul>"
            else:
                inner = f"<p>{text_refs('; '.join(str(v) for v in vals))}</p>"
            return f'<div class="ch-block"><h5>{head}</h5>{inner}</div>'

        grid = (block("priority_questions", "Priority questions", True)
                + block("expected_evidence_types", "Expected evidence", False)
                + block("likely_blind_spots", "Likely blind spots", False)
                + block("potential_conflicts", "Potential conflicts", False)
                + block("escalation_triggers", "Escalation triggers", False))
        role_html = f'<p class="role">{text_refs(role)}</p>' if role else ""
        slug = re.sub(r'[^a-z0-9]+', '-', name.lower().strip('-'))
        icon = _lens_icon_ca(slug)
        cards += (f'<div class="charter charter--{e(slug)}"><h4>{icon}{e(name)}</h4>{role_html}'
                  f'<div class="ch-grid">{grid}</div></div>')
    return f'<div class="charters">{cards}</div>' if cards else ""
