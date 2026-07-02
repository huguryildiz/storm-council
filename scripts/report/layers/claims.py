"""Claims ledger table."""

from __future__ import annotations


from report.components.badges import _EVIDENCE_TAG, _locator_text
from report.components.base import _field_details, e, refs, text_refs
from report.layers.deliberation import _round_label


def _claims_table_html(claims, effects_by_claim=None, full=True) -> str:
    """Render the claims ledger. ``full`` (appendix / --layer all) shows the raw
    per-claim confidence decimal and the adversarial-check stamp; the reader path
    (``full=False``) keeps the status label and the qualitative evidence-basis but
    drops the uncalibrated decimal and the per-claim "passed" stamp (A4)."""
    if not isinstance(claims, list) or not claims:
        return ""
    effects_by_claim = effects_by_claim or {}
    rows = ""
    for c in claims:
        if not isinstance(c, dict):
            continue
        cid = c.get("claim_id") or c.get("id") or ""
        ctype = c.get("claim_type", "")
        status = str(c.get("evidence_status", "")).lower()
        scls, slbl = _EVIDENCE_TAG.get(status, ("kind", status or "—"))
        persp = str(c.get("perspective", "")).replace("_", " ")
        text = text_refs(c.get("claim_text") or c.get("text", ""))
        cev = c.get("counterevidence_ids")
        cev_html = f'<span class="cev">counters{refs(cev)}</span>' if cev else ""
        meta_chips = []
        if c.get("confidence") is not None:
            basis = c.get("confidence_basis")
            band = c.get("confidence_band")
            btitle = f' title="{e(str(basis))}"' if basis else ""
            if full:
                conf_title = f' title="{e(str(basis))}"' if basis else ""
                meta_chips.append(f'<span class="claim-chip"{conf_title}>⚡ {e(str(c.get("confidence")))}</span>')
                # Confidence provenance (Phase 4): a bare float must carry a basis or
                # band so it never reads as calibrated. Missing on old artifacts is a
                # visible soft-warn, never blocking.
                if band or basis:
                    label = e(str(band)) if band else "basis noted"
                    meta_chips.append(f'<span class="claim-chip claim-basis"{btitle}>{label}</span>')
                else:
                    meta_chips.append(
                        '<span class="claim-chip claim-basis-missing" title="No confidence '
                        'basis recorded (evidence tier × verdict × full-text status).">'
                        'basis not recorded</span>')
            elif band or basis:
                # Reader path (A4): keep the qualitative evidence-basis, drop the
                # uncalibrated decimal. A claim with no recorded basis shows nothing
                # here — the "basis not recorded" soft-warn stays in the appendix.
                label = e(str(band)) if band else "basis noted"
                meta_chips.append(f'<span class="claim-chip claim-basis"{btitle}>{label}</span>')
        # 07c: decision-criticality chip (pivotal / contributing / peripheral),
        # copied from the claim's own mirror field — ordinal-only, never a number.
        dc = c.get("decision_criticality")
        if isinstance(dc, dict):
            crit = str(dc.get("criticality") or "").lower()
            if crit in ("pivotal", "contributing", "peripheral"):
                meta_chips.append(
                    f'<span class="claim-chip claim-crit-{crit}">{e(crit)}</span>')
        eff = effects_by_claim.get(cid)
        if isinstance(eff, dict) and eff.get("before") not in (None, ""):
            rnd = eff.get("round")
            when = f' after R{e(_round_label(rnd))} {e(str(eff.get("move_type") or "challenge"))}' if rnd else ""
            meta_chips.append(
                '<span class="claim-chip claim-delta">%s %s &rarr; %s%s</span>' % (
                    e(str(eff.get("field") or "confidence")),
                    e(str(eff.get("before"))), e(str(eff.get("after"))), when))
        if c.get("created_at"):
            try:
                from datetime import datetime, timezone
                dt = datetime.fromisoformat(c["created_at"])
                local_date = dt.astimezone().strftime("%Y-%m-%d %H:%M")
            except Exception:
                local_date = c["created_at"]
            meta_chips.append(f'<span class="claim-chip">🕐 {e(local_date)}</span>')
        meta_html = f'<span class="claim-meta">{"".join(meta_chips)}</span>' if meta_chips else ""
        src_html = refs(c.get("source_ids")) or "—"
        verification = c.get("content_verification")
        if isinstance(verification, dict):
            locator = verification.get("evidence_locator")
            verification = {
                "status": verification.get("status"),
                "full_text_status": verification.get("full_text_status"),
                "entailment_rationale": verification.get("entailment_rationale"),
                "evidence_locator": _locator_text(locator) if isinstance(locator, dict) else locator,
                # A4: the per-claim adversarial-check stamp implies scrutiny that the
                # real (5-bullet) review did not perform per claim — appendix only.
                "adversarial_check": verification.get("adversarial_check") if full else None,
            }
        atom = c.get("atomicity")
        if isinstance(atom, dict):
            atom = {
                "is_atomic": atom.get("is_atomic"),
                "split_from": atom.get("split_from"),
                "bundled_risk": atom.get("bundled_risk"),
            }
        detail_html = _field_details((
            ("strength", c.get("claim_strength")),
            ("evidence", c.get("evidence_ids")),
            ("support_scope", c.get("support_scope")),
            ("scope_risk_flags", c.get("scope_risk_flags")),
            ("limitations", c.get("limitations")),
            ("atomicity", atom),
            ("content_verification", verification),
        ), "Claim details")
        rows += ('<tr id="ref-%s"><td class="mono">%s</td><td style="text-transform:capitalize">%s</td>'
                 '<td><span class="tag kind">%s</span></td>'
                 '<td><span class="tag %s">%s</span></td>'
                 '<td>%s%s%s%s</td><td>%s</td><td>%s</td></tr>') % (
                     e(cid), e(cid), e(persp), e(ctype), scls, e(slbl),
                     text, cev_html, meta_html, "", src_html, detail_html)
    return ('<table class="claims-table"><thead><tr><th>ID</th><th>Lens</th><th>Type</th>'
            '<th>Status</th><th>Claim</th><th>Sources</th><th>Details</th></tr></thead><tbody>'
            + rows + "</tbody></table>")
