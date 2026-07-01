"""Council deliberation log, move effects, run manifest, cross-examination detail."""

from __future__ import annotations


from report.components.badges import _MOVE_TAG
from report.components.base import _field_details, _fmt_datetime_html, e, refs, text_refs


def _round_label(r) -> str:
    """Normalise a round identifier to its bare ordinal ('round_1'/'R1' -> '1')."""
    s = str(r).strip()
    low = s.lower()
    if low.startswith("round_"):
        low = low[6:]
    elif low.startswith("round"):
        low = low[5:]
    elif low[:1] == "r" and low[1:2].isdigit():
        low = low[1:]
    return low.replace("_", " ").strip() or s


def _move_effect_html(effect) -> str:
    """Render a deliberation move's consequence: what a challenge changed."""
    if not isinstance(effect, dict):
        return ""
    ct = str(effect.get("change_type") or "").lower()
    if ct in ("", "none"):
        return ""
    field = effect.get("field") or "confidence"
    before, after = effect.get("before"), effect.get("after")
    if ct == "withdrawn":
        desc = "claim withdrawn"
    elif ct == "scope_narrowed":
        desc = f"{e(field)} scope narrowed" + (
            f": {text_refs(after)}" if after not in (None, "") else "")
    elif ct in ("confidence_delta", "status_change") or (before not in (None, "") or after not in (None, "")):
        arrow = f'{e(str(before))} &rarr; {e(str(after))}' if before not in (None, "") else e(str(after))
        desc = f"{e(field)} {arrow}"
    else:
        desc = e(ct.replace("_", " "))
    resolves = effect.get("resolves") or []
    res_html = f' · resolves {refs(resolves).strip()}' if resolves else ""
    return f'<div class="mv-effect"><span class="mv-effect-label">Effect</span> {desc}{res_html}</div>'


def _claim_effects_from_deliberation(moves) -> dict:
    """Map claim_id -> its last confidence/status effect, for the claims ledger.

    Lets the ledger show a before&rarr;after delta ('0.73 &rarr; 0.61 after R1
    challenge') driven by cross-examination moves."""
    out: dict = {}
    if not isinstance(moves, list):
        return out
    for m in moves:
        if not isinstance(m, dict):
            continue
        eff = m.get("effect")
        if not isinstance(eff, dict):
            continue
        ct = str(eff.get("change_type") or "").lower()
        if ct in ("", "none"):
            continue
        target = m.get("target_id") or m.get("target_claim_id")
        if not target or not str(target).startswith("C-"):
            continue
        out[target] = {
            "change_type": ct,
            "field": eff.get("field") or "confidence",
            "before": eff.get("before"),
            "after": eff.get("after"),
            "round": m.get("round"),
            "move_type": m.get("move") or m.get("move_type"),
        }
    return out


def _run_manifest_html(m) -> str:
    """Render the minimal run manifest (dispatch mode, models/lenses, retrieval
    tools, timestamp, schema/version) in the appendix. Attests the *claim* of
    independent dispatch — not proof of it; the copy says so."""
    if not isinstance(m, dict) or not m:
        return ""
    rows = ""

    def _row(label, val_html):
        return f'<tr><th scope="row">{e(label)}</th><td>{val_html}</td></tr>'

    if m.get("generated_at"):
        rows += _row("Generated", _fmt_datetime_html(str(m["generated_at"])))
    if m.get("dispatch_mode"):
        rows += _row("Dispatch mode", e(str(m["dispatch_mode"]).replace("_", " ")))
    if m.get("independent_contexts") is not None:
        rows += _row("Independent contexts", "yes" if m["independent_contexts"] else "no")
    mpl = m.get("models_per_lens")
    if isinstance(mpl, dict) and mpl:
        items = "".join(
            f'<li><b style="text-transform:capitalize">{e(str(k))}</b>: {e(str(v))}</li>'
            for k, v in mpl.items())
        rows += _row("Models per lens", f'<ul class="clean">{items}</ul>')
    tools = m.get("retrieval_tools_used")
    if isinstance(tools, list) and tools:
        chips = "".join(f'<span class="tag kind">{e(str(t))}</span> ' for t in tools)
        rows += _row("Retrieval tools used", chips)
    elif isinstance(tools, list):
        rows += _row("Retrieval tools used", '<span class="tag open">none — claims are unsupported</span>')
    if m.get("schema_version"):
        rows += _row("Schema version", e(str(m["schema_version"])))
    if m.get("generator_version"):
        rows += _row("Generator version", e(str(m["generator_version"])))
    if not rows:
        return ""
    note = ('<p class="lead">This manifest records how the run was dispatched. It attests the '
            '<b>claim</b> of independent lens contexts and the tools invoked — it is not itself '
            'proof that the lenses reasoned independently.</p>')
    return f'{note}<table class="manifest-table"><tbody>{rows}</tbody></table>'


def _deliberation_html(moves) -> str:
    if not isinstance(moves, list) or not moves:
        return ""
    by_round: dict = {}
    order: list = []
    for m in moves:
        if not isinstance(m, dict):
            continue
        r = m.get("round", "")
        if r not in by_round:
            by_round[r] = []
            order.append(r)
        by_round[r].append(m)
    if not order:
        return ""
    out = ""
    for r in order:
        label = str(r).replace("round_", "").replace("_", " ").strip() or e(r)
        out += f'<p class="round-h">Round {e(label)}</p><div class="moves">'
        for m in by_round[r]:
            mt = str(m.get("move_type") or m.get("move") or "").lower().replace("_", "-")
            mcls, mlbl = _MOVE_TAG.get(mt, ("kind", mt.replace("-", " ") or "move"))
            lens = str(m.get("perspective") or m.get("lens") or "").replace("_", " ")
            tparts = []
            for key in ("target_claim_id", "conflict_id", "target_id"):
                if m.get(key):
                    tparts.append(refs([m[key]]).strip())
            target = " ".join(p for p in tparts if p)
            text = m.get("text") or m.get("statement") or ""
            mid = m.get("move_id")
            mid_html = f'<span class="mv-id mono">{e(mid)}</span>' if mid else ""
            effect_html = _move_effect_html(m.get("effect"))
            meta = _field_details((
                ("round", m.get("round")),
                ("move", m.get("move") or m.get("move_type")),
                ("move_id", mid),
                ("effect", m.get("effect")),
                ("created_at", m.get("created_at")),
            ), "Move metadata")
            out += ('<div class="move"><div class="mv-side">'
                    f'{mid_html}'
                    f'<span class="mv-lens">{e(lens)}</span>'
                    f'<span class="tag {mcls}">{e(mlbl)}</span>'
                    f'<span class="mv-target">{target}</span></div>'
                    f'<div class="mv-text">{text_refs(text)}{effect_html}{meta}</div></div>')
        out += "</div>"
    return out


def _cx_detail_html(detail: dict, claim_by_id: dict) -> str:
    def pos(cid):
        cl = claim_by_id.get(cid)
        chip = refs([cid]).strip() if cid else ""
        if cl:
            who = str(cl.get("perspective", "")).replace("_", " ")
            who_html = f'<b style="text-transform:capitalize">{e(who)}</b> ' if who else ""
            return f'{who_html}{chip} — {text_refs(cl.get("claim_text", ""))}'
        return chip
    inner = ""
    meta = []
    if detail.get("topic"):
        meta.append(f"Topic: {detail.get('topic')}")
    if detail.get("relationship"):
        meta.append(f"Relationship: {detail.get('relationship')}")
    if detail.get("resolution_status"):
        meta.append(f"Resolution: {detail.get('resolution_status')}")
    resolution = detail.get("resolution") if isinstance(detail.get("resolution"), dict) else None
    if detail.get("human_review_required") is not None:
        meta.append("Human review required: " + ("yes" if detail.get("human_review_required") else "no"))
    if meta:
        inner += f'<p class="cx-meta">{e(" · ".join(meta))}</p>'
    if detail.get("contradiction_id") and detail.get("contradiction_id") != detail.get("conflict_id"):
        inner += f'<p class="cx-meta">Contradiction ID: {refs([detail.get("contradiction_id")]).strip()}</p>'
    if detail.get("claim_ids"):
        inner += f'<p class="cx-pos">Claims: {refs(detail.get("claim_ids")).strip()}</p>'
    if detail.get("scope_dimension"):
        inner += f'<p class="cx-meta">Scope dimension: {text_refs(detail.get("scope_dimension"))}</p>'
    why = detail.get("why_it_matters") or detail.get("topic")
    if why:
        inner += f'<p class="cx-why">{text_refs(why)}</p>'
    if detail.get("claim_a_id"):
        inner += f'<p class="cx-pos">{pos(detail.get("claim_a_id"))}</p>'
    if detail.get("claim_b_id"):
        inner += f'<p class="cx-pos">{pos(detail.get("claim_b_id"))}</p>'
    if detail.get("evidence_balance"):
        inner += f'<p class="cx-bal">Evidence balance: <b>{e(detail["evidence_balance"])}</b></p>'
    if detail.get("next_question"):
        inner += f'<p class="cx-nq">Next question: {text_refs(detail["next_question"])}</p>'
    if detail.get("decisive_missing_evidence"):
        inner += f'<p class="cx-nq">Decisive missing evidence: {text_refs(detail["decisive_missing_evidence"])}</p>'
    if resolution:
        basis = str(resolution.get("basis") or "none").lower()
        ev_ids = resolution.get("evidence_ids") or []
        mv_ids = resolution.get("move_ids") or []
        refs_html = ""
        if ev_ids:
            refs_html += f' · evidence {refs(ev_ids).strip()}'
        if mv_ids:
            refs_html += f' · moves {refs(mv_ids).strip()}'
        credited = basis not in ("", "none") and (ev_ids or mv_ids)
        badge_cls = "done" if credited else "open"
        badge = "credited" if credited else "uncredited"
        inner += ('<div class="cx-resolution"><p class="cx-meta">'
                  f'Resolution basis: <span class="tag kind">{e(basis)}</span> '
                  f'<span class="tag {badge_cls}">{badge}</span>{refs_html}</p>')
        if resolution.get("rationale"):
            inner += f'<p class="cx-why">{text_refs(resolution["rationale"])}</p>'
        inner += "</div>"
    if not inner:
        return ""
    return f'<details class="cx-detail"><summary>Positions &amp; detail</summary>{inner}</details>'
