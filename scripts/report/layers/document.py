"""Document assembly: build(), layer gating, artifact folding, CLI entrypoint."""

from __future__ import annotations

import json
import csv
import argparse
from pathlib import Path

from report.components.badges import _CONFLICT, _STRENGTH, _source_class_badges, _source_identity_badges
from report.components.base import _ANCHORS, _EMITTED_CLAIM_TARGETS, _fmt_datetime_html, _md_block, e, refs, text_refs
from report.components.bib import _format_apa_html, _parse_bibtex
from report.components.icons import _logo_svg
from report.layers.argument_map import _argument_map_interactive_html
from report.layers.claims import _claims_table_html
from report.layers.deliberation import _claim_effects_from_deliberation, _cx_detail_html, _deliberation_html, _run_manifest_html
from report.layers.evidence import _evidence_table_html
from report.layers.lenses import _evidence_plan_html, _lens_charters_html, _lens_snapshot_html


CSS = (Path(__file__).resolve().parent.parent / "styles.css").read_text(encoding="utf-8")


_STATUS_CLASS = {"pass": "green", "verified": "green", "source_checked": "green",
                 "pass_with_caveats": "", "caveats": "", "illustrative": "",
                 "revise": "red", "blocked": "red"}


_LAYERS = ("brief", "report", "appendix", "all")


def _layer_visible(layer: str, tier: str) -> bool:
    """Which section tiers render for a given output layer.

    ``all`` renders everything (byte-identical to the historic single file);
    ``report`` is the curated brief plus its analytical backbone; ``appendix``
    is the raw-artifact / heavy-interactive dump on its own."""
    if layer == "all":
        return True
    if layer == "brief":
        return tier == "brief"
    if layer == "report":
        return tier in ("brief", "report")
    if layer == "appendix":
        return tier == "appendix"
    return True


def build(data: dict, layer: str = "all") -> str:
    if layer not in _LAYERS:
        layer = "all"
    counts = data.get("counts", {})
    st = data.get("status", {})
    scores = st.get("scores", {})
    p: list[str] = []
    a = p.append

    _ANCHORS.clear()
    _EMITTED_CLAIM_TARGETS.clear()
    for s in data.get("sources", []) or []:
        if s.get("id"):
            _ANCHORS.add(s["id"])
    for c in data.get("contradictions", []) or []:
        if c.get("id"):
            _ANCHORS.add(c["id"])
    # When a claims ledger is present it owns the C-### anchor targets, so chips
    # elsewhere link to it instead of minting a duplicate id at first mention.
    for c in data.get("claims", []) or []:
        cid = c.get("claim_id") or c.get("id")
        if cid:
            _ANCHORS.add(cid)
            _EMITTED_CLAIM_TARGETS.add(cid)
    for ev in data.get("evidence", []) or []:
        eid = ev.get("evidence_id") or ev.get("id")
        if eid:
            _ANCHORS.add(eid)

    a("<!doctype html>\n<html lang=\"en\">\n<head>\n<meta charset=\"utf-8\" />")
    a('<meta name="viewport" content="width=device-width, initial-scale=1" />')
    a(f"<title>{e(data.get('title','Storm Council report'))}</title>")
    a("<style>" + CSS + "</style>")
    if layer == "brief":
        # Print-friendly rules scoped to the standalone brief only, so the
        # default `all` output stays byte-identical to the historic report.
        a("<style>@media print{.toc{display:none!important}"
          ".page{max-width:none;padding:0}"
          "section,.fcard,.opt,.bottom-line-card{break-inside:avoid}}</style>")
    a("</head>\n<body>\n<main class=\"page\">")

    logo_svg = _logo_svg()
    a('<header class="report-header"><div class="report-title-block">')
    a(f'<p class="eyebrow">{e(data.get("eyebrow", "Storm Council · Decision Brief"))}</p>')
    a(f'<h1>{e(data.get("title",""))}</h1>')
    if data.get("subtitle"):
        a(f'<p class="subtitle">{e(data["subtitle"])}</p>')
    a("</div>")
    if logo_svg:
        a(f'<div class="brand-logo" aria-label="Storm Council icon">{logo_svg}</div>')
    a("</header>")

    meta = []
    if data.get("mode"): meta.append(f'<span><b>Mode</b> {e(data["mode"])}</span>')
    if data.get("audience"): meta.append(f'<span><b>Audience</b> {e(data["audience"])}</span>')
    if counts:
        meta.append('<span><b>Lenses</b> %s · <b>Claims</b> %s · <b>Sources</b> %s · <b>Conflicts</b> %s</span>'
                    % (e(counts.get("lenses","-")), e(counts.get("claims","-")),
                       e(counts.get("sources","-")), e(counts.get("conflicts","-"))))
    if meta:
        a('<div class="meta">' + "".join(meta) + "</div>")

    if st:
        cls = _STATUS_CLASS.get(str(st.get("level", "")).lower(), "")
        verdict = st.get("verdict", "")
        srow = ""
        if scores:
            def _score_cls(v):
                try:
                    n = int(v)
                    if n >= 80: return "ok"
                    if n >= 50: return "warn"
                    return "bad"
                except (TypeError, ValueError):
                    return ""
            def _verdict_badge_cls(v):
                vl = str(v).upper()
                if vl == "PASS": return "vb-pass"
                if "CAVEAT" in vl: return "vb-caveats"
                if "FAIL" in vl: return "vb-fail"
                return "vb-unknown"
            score_items = [
                (scores.get("coverage", "-"), "Coverage"),
                (scores.get("traceability", "-"), "Traceability"),
                (scores.get("contradiction", "-"), "Contradiction"),
                (scores.get("recommendation", "-"), "Rec. Support"),
            ]
            score_html = "".join(
                '<div class="vscore %s"><span class="vscore-val">%s</span>'
                '<span class="vscore-key">%s</span></div>'
                % (_score_cls(val), e(str(val)), e(label))
                for val, label in score_items
            )
            srow = (
                '<div class="verdict-panel">'
                '<span class="verdict-panel-label">Review verdict</span>'
                '<span class="verdict-status-badge %s">%s</span>'
                '<span class="verdict-divider"></span>'
                '<div class="verdict-scores">%s</div>'
                '</div>'
                % (_verdict_badge_cls(verdict), e(verdict), score_html)
            )
        crow = ""
        checks = st.get("checks")
        if checks:
            chips = "".join(
                '<span class="chk %s"><b>%s</b> %s</span>' % (
                    e(str(c.get("tone", "")).lower()), e(c.get("value", "")), e(c.get("label", "")))
                for c in checks)
            crow = f'<div class="checks">{chips}</div>'
        a('<div class="status %s"><span class="pill">%s</span><b>%s</b><p>%s</p>%s%s</div>' % (
            cls, e(st.get("pill", "STATUS")), e(st.get("headline", "")), text_refs(st.get("detail", "")), crow, srow))

    howto = data.get("how_to_read") or [
        "<b>The panel is author-constructed.</b> Where the lenses agree, treat it as a strong hypothesis, not independent proof.",
        "<b>Confidence (0.0-1.0) is separate from evidence status.</b> A high-confidence forecast is still a forecast.",
        "<b>Fact, inference, and recommendation are labelled separately.</b>",
        "<b>Disagreements are kept on the record</b>, not resolved by force.",
        "<b>A Contradiction score of 50 means no contradictions were logged</b> — a neutral \"no data\" reading, not a penalty. It only drops toward 0 when logged contradictions are left unresolved.",
    ]
    a('<div class="howto"><h3>How to read this</h3><ul>' +
      "".join(f"<li>{li}</li>" for li in howto) + "</ul></div>")

    section_no = [0]
    toc_items: list = []

    def sec(title, body, tier="report"):
        if not _layer_visible(layer, tier):
            return
        section_no[0] += 1
        num = f"{section_no[0]:02d}"
        toc_items.append((num, title))
        a(f'<section id="sec-{num}"><h2><span class="num">{num}</span>{e(title)}</h2>{body}</section>')

    if data.get("bottom_line"):
        sec("Bottom line", '<div class="bottom-line-card"><p>%s</p></div>' % text_refs(data["bottom_line"]), "brief")

    if data.get("decision_frame"):
        sec("Decision frame", f'<div class="artifact">{_md_block(data["decision_frame"])}</div>', "appendix")

    charters_html = _lens_charters_html(data.get("lens_charters"))
    if charters_html:
        sec("The five council lenses", charters_html, "report")

    def _attr(cls, label, d):
        persp = e(" + ".join(p.title() for p in d.get("perspectives", []))) if d.get("perspectives") else ""
        note = text_refs(d.get("note", "")) if d.get("note") else ""
        sep = " — " if persp and note else ""
        pb = f"<b>{persp}</b>" if persp else ""
        nn = f'<span class="attr-note">{note}</span>' if note else ""
        return f'<span class="attr {cls}"><span class="attr-label">{label}</span>{pb}{sep}{nn}</span>'

    def _finding_card(f, idx):
        contested = str(f.get("reliability", "")).lower() in ("low", "contested", "weak")
        num = f'<span class="fnum">{idx}</span>'
        kicker = f'<p class="fkicker">{e(f["kicker"])}</p>' if f.get("kicker") else ""
        title = f'<h4 class="ftitle">{e(f["title"])}</h4>' if f.get("title") else ""
        rel, score = f.get("reliability"), f.get("score")
        head = ""
        if rel or score is not None:
            rl = f'<span class="rel-pill">RELIABILITY: {e(str(rel).upper())}</span>' if rel else ""
            sc = f'<span class="rel-score"><b>{e(score)}</b>/10</span>' if score is not None else ""
            head = f'<div class="fhead">{rl}{sc}</div>'
        body = f'<div class="fbody">{text_refs(f.get("text",""))}{refs(f.get("claims"))}</div>'
        attrs = ""
        if f.get("supported_by"):
            attrs += _attr("supported", "SUPPORTED BY", f["supported_by"])
        if f.get("challenged_by"):
            attrs += _attr("challenged", "CHALLENGED BY", f["challenged_by"])
        cor = f.get("corrected")
        if cor:
            ctext = cor if isinstance(cor, str) else (cor.get("note", "") if isinstance(cor, dict) else "")
            if ctext:
                attrs += f'<span class="attr corrected"><span class="attr-label">CORRECTED</span>{text_refs(ctext)}</span>'
        attrs_div = f'<div class="finding-attrs">{attrs}</div>' if attrs else ""
        cls = "fcard contested" if contested else "fcard"
        return f'<div class="{cls}">{num}{kicker}{title}{head}{body}{attrs_div}</div>'

    def _finding_score(f):
        try:
            return float(f.get("score"))
        except (TypeError, ValueError):
            return float("-inf")

    fnd = data.get("strongest_findings", [])
    if fnd:
        ranked_findings = sorted(
            enumerate(fnd),
            key=lambda item: (-_finding_score(item[1]), item[0]),
        )
        body = (
            '<div class="findings">'
            + "".join(_finding_card(f, i) for i, (_, f) in enumerate(ranked_findings, 1))
            + "</div>"
        )
        sec("Strongest evidence-backed findings", body, "brief")

    effects_by_claim = _claim_effects_from_deliberation(data.get("deliberation"))
    claims_html = _claims_table_html(data.get("claims"), effects_by_claim)
    if claims_html:
        confidence_kpi = (
            '<div class="kpi-card"><span class="kpi-icon">⚡</span><div>'
            '<b class="kpi-title">Confidence score (0.0–1.0)</b>'
            '<p class="kpi-desc">The number next to the lightning-bolt icon is the lens’s own subjective '
            'strength of belief in that claim &mdash; <b>not a calibrated probability</b>. Nothing in this '
            'workflow back-tests these numbers against outcomes, so <code>0.88</code> means only that the lens '
            'is fairly but not fully certain; it does not mean the claim is right 88&nbsp;% of the time. '
            'Each score carries a <b>basis</b> (the evidence tier, verdict, and full-text status behind it) '
            'shown beside the number &mdash; read the basis, not the digits. It is intentionally '
            '<b>separate from the Status column</b>: a high-confidence forecast is still a forecast, not '
            'evidence. As a rule of thumb, the Stage 6 adversarial review flags confidence ≥ 0.8 on any claim '
            'whose status is not <code>supported</code> as possible overconfidence &mdash; worth a second '
            'look.</p></div></div>'
        )
        sec("Claims & evidence ledger", confidence_kpi + claims_html, "report")

    _sources_by_id = {
        (s.get("id") or s.get("source_id")): s
        for s in (data.get("sources") or [])
        if isinstance(s, dict) and (s.get("id") or s.get("source_id"))
    }
    evidence_html = _evidence_table_html(
        data.get("evidence"), _sources_by_id or None, data.get("evidence_verdicts")
    )
    if evidence_html:
        sec("Evidence registry", evidence_html, "report")

    # The interactive Cytoscape map (and its ~373 KB inline library) is heavy;
    # keep it in the appendix so brief/report stay lightweight and printable.
    if _layer_visible(layer, "appendix"):
        argmap_html = _argument_map_interactive_html(data.get("argument_map"), data)
        if argmap_html:
            sec("Argument map", argmap_html, "appendix")

    cons = data.get("contradictions", [])
    lens_snapshot = _lens_snapshot_html(data.get("lens_snapshot"))
    cdetail = data.get("contradiction_detail") or {}
    claim_by_id = {(c.get("claim_id") or c.get("id")): c
                   for c in (data.get("claims") or []) if isinstance(c, dict)}
    if cons:
        rows = ""
        for c in cons:
            tcls, tlbl = _CONFLICT.get(str(c.get("status","")).lower(), ("part", c.get("status","")))
            stake = text_refs(c.get("stake", ""))
            # The one-page brief shows only the summary row; the expandable
            # positions/resolution detail belongs to the fuller layers.
            det = cdetail.get(c.get("id"))
            if layer != "brief" and isinstance(det, dict):
                stake += _cx_detail_html(det, claim_by_id)
            rows += ('<tr id="ref-%s"><td class="mono">%s</td><td><span class="tag kind">%s</span></td>'
                     '<td>%s</td><td><span class="tag %s">%s</span></td></tr>' % (
                         e(c.get("id","")), e(c.get("id","")), e(c.get("kind","")), stake, tcls, e(tlbl)))
        body = (lens_snapshot + '<table><thead><tr><th>Conflict</th><th>Kind</th><th>What is at stake</th>'
                '<th>Status</th></tr></thead><tbody>' + rows + "</tbody></table>")
        sec("Where the lenses disagree", body, "brief")
    elif lens_snapshot:
        sec("Lens posture snapshot", lens_snapshot, "report")

    if data.get("contradiction_ledger"):
        sec("Contradiction ledger notes", f'<div class="artifact">{_md_block(data["contradiction_ledger"])}</div>', "appendix")

    delib_html = _deliberation_html(data.get("deliberation"))
    if delib_html:
        sec("Council deliberation", delib_html, "appendix")

    opts = data.get("options", [])
    if opts:
        body = ""
        for o in opts:
            ccls, clbl = _STRENGTH.get(str(o.get("strength","")).lower(), ("s-none", o.get("strength","")))
            pts = "".join(f"<li>{text_refs(x)}</li>" for x in o.get("points", []))
            when = f'<p class="when">When appropriate: {text_refs(o["when"])}</p>' if o.get("when") else ""
            body += ('<div class="opt"><span class="chip %s">%s</span><h4>%s</h4><ul>%s</ul>%s</div>' % (
                ccls, e(clbl), e(o.get("name","")), pts, when))
        sec("Decision options & trade-offs", body, "brief")

    acts = data.get("next_actions", [])
    if acts:
        body = '<ul class="clean">' + "".join(
            f'<li>{text_refs(x.get("text",""))}{refs(x.get("refs"))}</li>' for x in acts) + "</ul>"
        sec("Recommended next actions", body, "brief")

    gaps = data.get("gaps", [])
    if gaps:
        body = '<ul class="clean">' + "".join(
            f'<li>{text_refs(g.get("text",""))}{refs(g.get("refs"))}</li>' for g in gaps) + "</ul>"
        sec("Evidence gaps & frontier questions", body, "brief")

    if data.get("source_mapped_synthesis"):
        sec("Source-mapped synthesis notes", f'<div class="artifact">{_md_block(data["source_mapped_synthesis"])}</div>', "appendix")

    if data.get("decision_brief"):
        sec("Decision brief artifact", f'<div class="artifact">{_md_block(data["decision_brief"])}</div>', "appendix")

    if data.get("evidence_plan"):
        sec("Evidence plan", _evidence_plan_html(data["evidence_plan"]), "appendix")

    srcs = data.get("sources", [])
    if srcs:
        bib_entries = _parse_bibtex(data.get("source_bibtex") or "")
        items = ""
        for s in srcs:
            sid = s.get("id", "")
            url = s.get("url")
            bib = bib_entries.get(sid)
            if bib:
                display = _format_apa_html(bib, url or "")
                if s.get("synthetic"):
                    display = f'<span class="syn">{display}</span>'
            else:
                label = e(s.get("title", ""))
                if url and not s.get("synthetic"):
                    label = f'<a class="slink" href="{e(url)}" target="_blank" rel="noopener">{label}</a>'
                display = f'<span class="syn">{label}</span>' if s.get("synthetic") else label
            note = f'<span class="note">{text_refs(s["note"])}</span>' if s.get("note") else ""
            meta_bits = []
            for label_name, key in (
                ("Authors", "authors"),
                ("Year", "year"),
                ("Venue", "venue"),
                ("Publisher", "publisher"),
                ("Published", "publication_date"),
                ("Accessed", "accessed_at"),
                ("DOI", "doi"),
                ("arXiv", "arxiv_id"),
                ("Publication status", "publication_status"),
                ("Full text", "full_text_status"),
                ("Credibility", "credibility_notes"),
                ("Relevance", "relevance_notes"),
            ):
                val = s.get(key)
                if val and str(val).lower() != "null":
                    if key in ("publication_date", "accessed_at"):
                        val_html = _fmt_datetime_html(str(val))
                    else:
                        val_html = text_refs(val)
                    meta_bits.append(f"<span>{label_name}: {val_html}</span>")
            source_meta = f'<span class="source-meta">{"".join(meta_bits)}</span>' if meta_bits else ""
            identity = " ".join(b for b in (_source_class_badges(s), _source_identity_badges(s)) if b)
            identity_html = (" " + identity) if identity else ""
            items += ('<li id="ref-%s"><span class="sid">%s</span> %s <span class="ty">· %s</span>%s%s</li>' % (
                e(sid), e(sid), display, e(s.get("type", "")), identity_html, note + source_meta))
        source_body = '<ul class="src">' + items + "</ul>"
        if data.get("source_bibtex"):
            source_body += (
                '<details class="bibtex-detail"><summary>BibTeX records</summary>'
                f'<pre>{e(data["source_bibtex"])}</pre></details>'
            )
        sec("Sources", source_body, "report")

    manifest_html = _run_manifest_html(data.get("run_manifest"))
    if manifest_html:
        sec("Run manifest", manifest_html, "appendix")

    if data.get("adversarial_review"):
        sec("Adversarial review notes", f'<div class="artifact">{_md_block(data["adversarial_review"])}</div>', "appendix")

    rev = data.get("review", {})
    if rev:
        chips = ""
        if scores:
            for k, lbl in (("coverage","coverage"),("traceability","traceability"),
                           ("contradiction","contradiction-handling"),("recommendation","recommendation-support")):
                if k in scores:
                    chips += f'<span class="score">{lbl} <b>{e(scores[k])}</b></span>'
        issues = ""
        for label, key in (("Blocking","blocking"),("Major","major"),("Minor","minor")):
            vals = rev.get(key) or []
            if vals:
                issues += f'<p class="lead"><b>{label}:</b></p><ul class="clean">' + \
                    "".join(f"<li>{text_refs(v)}</li>" for v in vals) + "</ul>"
        verdict = rev.get("verdict", "")
        summary = (
            f'<p class="lead">{text_refs(rev["summary"])}</p>'
            if rev.get("summary") else ""
        )
        body = (f'<div class="scores">{chips}</div>'
                f'<p class="lead">Verdict <b>{e(verdict)}</b>.</p>{summary}{issues}')
        sec("Independent review", body, "brief")

    a('<footer><p><b>Storm Council</b> is inspired by research-first knowledge-curation systems, '
      'especially Stanford OVAL\'s STORM line of work. For context, see '
      '<a href="https://oval.cs.stanford.edu/">Stanford OVAL</a>, '
      '<a href="https://storm.genie.stanford.edu/">the public STORM research preview</a>, '
      '<a href="https://storm-project.stanford.edu/research/storm/">the Stanford STORM research page</a>, '
      'and the <a href="https://github.com/stanford-oval/storm">stanford-oval/storm open-source repository</a>. '
      'Storm Council is independently developed and is <b>not</b> affiliated with, endorsed by, '
      'or derived from Stanford University, Stanford OVAL, or the STORM project.</p>'
      '<p>This brief supports research and deliberation. It does not replace domain expertise, '
      'source verification, or accountable human decision-making.</p></footer>')
    a("</main>")

    if len(toc_items) > 1:
        links = "".join(
            f'<li><a href="#sec-{num}"><span class="tn">{num}</span><span>{e(title)}</span></a></li>'
            for num, title in toc_items
        )
        a(f'<nav class="toc" aria-label="Report contents"><h4>Contents</h4><ol>{links}</ol></nav>')
        # Inline, self-contained scroll-spy (no network). The anchor links work
        # without it; this only adds the active-section highlight.
        a('<script>(function(){var L=[].slice.call(document.querySelectorAll(".toc a")),'
          'S=[].slice.call(document.querySelectorAll("section[id]")),m={};'
          'L.forEach(function(a){m[a.getAttribute("href").slice(1)]=a;});'
          'function u(){var c=null;S.forEach(function(s){'
          'if(s.getBoundingClientRect().top<=120)c=s.id;});'
          'L.forEach(function(a){a.classList.remove("active");});'
          'if(c&&m[c])m[c].classList.add("active");}'
          'document.addEventListener("scroll",u,{passive:true});'
          'window.addEventListener("resize",u);u();})();</script>')

    a('<script>(function(){document.querySelectorAll("time.ts-local").forEach(function(el){'
      'var d=new Date(el.dataset.ts);if(!isNaN(d.getTime())){'
      'el.textContent=d.toLocaleString(undefined,{year:"numeric",month:"short",day:"numeric",'
      'hour:"2-digit",minute:"2-digit",timeZoneName:"short"});}});})();</script>')
    a("</body>\n</html>\n")
    return "\n".join(p)


def _enrich_source_urls(data: dict, base: Path) -> None:
    """Fill missing source metadata from a sibling 03_source_registry.csv."""
    srcs = data.get("sources")
    if not srcs:
        return
    reg = base / "03_source_registry.csv"
    if not reg.exists():
        return
    row_by_id = {}
    with reg.open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            sid = (row.get("source_id") or "").strip()
            if sid:
                row_by_id[sid] = row
    for s in srcs:
        row = row_by_id.get(s.get("id", ""))
        if not row:
            continue
        if not s.get("url"):
            u = (row.get("url") or "").strip()
            if u:
                s["url"] = u
        if not s.get("type"):
            ty = (row.get("source_type") or "").strip()
            if ty and ty.lower() != "null":
                s["type"] = ty
        for key in (
            "authors", "year", "venue", "doi", "arxiv_id", "publication_status",
            "full_text_status", "source_class", "publisher", "publication_date",
            "accessed_at", "credibility_notes", "relevance_notes",
        ):
            val = (row.get(key) or "").strip()
            if val and val.lower() != "null" and not s.get(key):
                s[key] = val


def _read_jsonl(path: Path) -> list:
    rows: list = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except ValueError:
            continue
    return rows


def _fold_in_artifacts(data: dict, base: Path, layer: str = "all") -> None:
    """Read sibling stage artifacts from the report's directory and fold them
    into ``data`` so the report stays complete even when report_data.json is a
    summary. Anything the summary already carries wins; anything absent degrades
    to nothing rendered. Pure local file reads — no network.

    Structured data (claims, evidence, deliberation, manifest, …) is always
    folded because it can feed report/brief sections. The bulky raw-markdown
    stage dumps and the Mermaid/evidence-plan payloads only render in the
    appendix, so they are folded solely for ``appendix``/``all`` — this is what
    keeps the brief and standard report free of duplicated raw artifacts."""
    want_appendix = layer in ("appendix", "all")
    if not data.get("lens_charters"):
        f = base / "02_perspective_scan.json"
        if f.exists():
            try:
                parsed = json.loads(f.read_text(encoding="utf-8"))
            except ValueError:
                parsed = None
            if isinstance(parsed, list):
                data["lens_charters"] = parsed
            elif isinstance(parsed, dict) and isinstance(parsed.get("lenses"), list):
                data["lens_charters"] = parsed["lenses"]

    # BibTeX feeds the report-tier Sources section (APA formatting), so it is
    # folded for every layer; the raw stage-markdown dumps are appendix-only.
    if not data.get("source_bibtex"):
        f = base / "03_sources.bib"
        if f.exists():
            data["source_bibtex"] = f.read_text(encoding="utf-8")

    if want_appendix:
        for key, filename in (
            ("decision_frame", "01_decision_frame.md"),
            ("contradiction_ledger", "04_contradiction_ledger.md"),
            ("source_mapped_synthesis", "05_synthesis.md"),
            ("decision_brief", "05_decision_brief.md"),
            ("adversarial_review", "06_adversarial_review.md"),
        ):
            if not data.get(key):
                f = base / filename
                if f.exists():
                    data[key] = f.read_text(encoding="utf-8")

    if not data.get("claims"):
        f = base / "03_claims.jsonl"
        if f.exists():
            claims = _read_jsonl(f)
            if claims:
                data["claims"] = claims

    if not data.get("evidence"):
        f = base / "03_evidence.jsonl"
        if f.exists():
            evidence = _read_jsonl(f)
            if evidence:
                data["evidence"] = evidence

    if not data.get("evidence_verdicts"):
        f = base / "03_evidence_verdicts.jsonl"
        if f.exists():
            verdicts = _read_jsonl(f)
            if verdicts:
                data["evidence_verdicts"] = verdicts

    if want_appendix and not data.get("argument_map"):
        f = base / "05_argument_map.mmd"
        if f.exists():
            data["argument_map"] = f.read_text(encoding="utf-8")

    if not data.get("deliberation"):
        f = base / "04_council_deliberation.jsonl"
        if f.exists():
            moves = _read_jsonl(f)
            if moves:
                data["deliberation"] = moves

    if not data.get("contradiction_detail"):
        f = base / "04_contradictions.json"
        if f.exists():
            try:
                arr = json.loads(f.read_text(encoding="utf-8"))
            except ValueError:
                arr = None
            if isinstance(arr, list):
                # Canonical id is `id`; `conflict_id`/`contradiction_id` remain
                # as one-release deprecated aliases.
                data["contradiction_detail"] = {
                    (x.get("id") or x.get("conflict_id") or x.get("contradiction_id")): x
                    for x in arr
                    if isinstance(x, dict) and (x.get("id") or x.get("conflict_id") or x.get("contradiction_id"))
                }

    if not data.get("run_manifest"):
        f = base / "run_manifest.json"
        if f.exists():
            try:
                manifest = json.loads(f.read_text(encoding="utf-8"))
            except ValueError:
                manifest = None
            if isinstance(manifest, dict):
                data["run_manifest"] = manifest

    if want_appendix and not data.get("evidence_plan"):
        f = base / "03_evidence_plan.md"
        if f.exists():
            data["evidence_plan"] = f.read_text(encoding="utf-8")

    if not data.get("quality_gate"):
        f = base / "06_quality_gate.json"
        if f.exists():
            try:
                qgate = json.loads(f.read_text(encoding="utf-8"))
            except ValueError:
                qgate = None
            if isinstance(qgate, dict):
                data["quality_gate"] = qgate
                if qgate.get("review_summary"):
                    review = data.setdefault("review", {})
                    review.setdefault("summary", qgate["review_summary"])

    f = base / "source_versions.jsonl"
    if f.exists():
        versions = {
            row.get("source_id"): row
            for row in _read_jsonl(f)
            if isinstance(row, dict) and row.get("source_id")
        }
        if versions and data.get("sources"):
            for src in data.get("sources") or []:
                sid = src.get("id") or src.get("source_id")
                version = versions.get(sid)
                if not version:
                    continue
                for key in ("identifiers", "publication_identity", "flags",
                            "canonical_source_id", "duplicate_of"):
                    if key in version and not src.get(key):
                        src[key] = version[key]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Render a Storm Council report (JSON -> HTML).")
    ap.add_argument("input", help="report_data.json")
    ap.add_argument("-o", "--output", default="storm_council_report.html")
    ap.add_argument("--layer", choices=_LAYERS, default="all",
                    help="which layer to render: brief (1-page decision), report "
                         "(brief + analysis), appendix (raw artifacts + interactive "
                         "map + manifest), or all (default; single combined file)")
    args = ap.parse_args(argv)
    data = json.loads(Path(args.input).read_text(encoding="utf-8"))
    base = Path(args.input).parent
    _enrich_source_urls(data, base)
    _fold_in_artifacts(data, base, args.layer)
    Path(args.output).write_text(build(data, args.layer), encoding="utf-8")
    print(f"wrote {args.output} (layer={args.layer})")
    return 0
