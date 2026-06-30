#!/usr/bin/env python3
"""Render a Storm Council decision-brief report (JSON -> single HTML).

Pure standard library. No network, no LLM, no API key. The reasoning is done by
the skill (Claude); this script only fixes the *format* so every report looks
identical. Honesty: the status banner reflects whatever the input says — render
a "verified" state only if verification actually happened.

Usage:
    python3 render_report.py report_data.json -o storm_council_report.html
"""

from __future__ import annotations

import argparse
import csv
import html
import json
import sys
from pathlib import Path

CSS = """
  :root{
    --ink:#15161a; --muted:#5b606b; --faint:#8a8f99; --line:#e7e8ec;
    --brand:#5b46c8; --brand-soft:#efecfb;
    --amber:#b7791f; --amber-bg:#fdf6e3; --amber-line:#eccb74;
    --green:#1a7f51; --green-bg:#e7f6ee; --green-line:#9bd9b8;
    --red:#b42318; --red-bg:#fdecea; --red-line:#f1b0a8;
    --card:#fbfbfd;
  }
  *{box-sizing:border-box}
  body{ margin:0; background:#f4f5f7; color:var(--ink);
    font:16px/1.62 -apple-system,BlinkMacSystemFont,"Segoe UI",Inter,Roboto,Helvetica,Arial,sans-serif; }
  .page{ max-width:820px; margin:32px auto; background:#fff; padding:56px 60px 44px;
    border:1px solid var(--line); border-radius:14px; box-shadow:0 1px 2px rgba(20,22,26,.04); }
  .report-header{ display:flex; align-items:flex-start; justify-content:space-between; gap:28px; margin:0 0 14px; }
  .report-title-block{ min-width:0; }
  .brand-logo{ flex:0 0 auto; margin-top:-8px; }
  .brand-logo svg{ display:block; width:50px; height:50px; max-width:100%; }
  .mono{ font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace; }
  .eyebrow{ font-family:ui-monospace,Menlo,monospace; font-size:12px; letter-spacing:.16em;
    text-transform:uppercase; color:var(--brand); margin:0 0 18px; }
  h1{ font-size:34px; line-height:1.16; font-weight:800; letter-spacing:-.015em; margin:0 0 14px; }
  .subtitle{ font-size:17px; color:var(--muted); margin:0 0 22px; max-width:62ch; }
  .meta{ display:flex; flex-wrap:wrap; gap:6px 26px; padding:14px 0; margin:0 0 22px;
    border-top:1px solid var(--line); border-bottom:1px solid var(--line);
    font-family:ui-monospace,Menlo,monospace; font-size:12.5px; color:var(--faint); }
  .meta b{ color:var(--ink); font-weight:600; }
  .status{ border-radius:10px; padding:16px 18px; margin:0 0 26px; border:1px solid var(--amber-line); background:var(--amber-bg); }
  .status.green{ border-color:var(--green-line); background:var(--green-bg); }
  .status.red{ border-color:var(--red-line); background:var(--red-bg); }
  .status .pill{ display:inline-block; font-family:ui-monospace,Menlo,monospace; font-size:11px;
    letter-spacing:.08em; font-weight:700; color:#fff; background:var(--amber); padding:3px 9px; border-radius:999px; vertical-align:2px; margin-right:8px; }
  .status.green .pill{ background:var(--green); } .status.red .pill{ background:var(--red); }
  .status p{ margin:8px 0 0; font-size:14px; color:#4a4636; }
  .status .verdict{ margin-top:10px; font-family:ui-monospace,Menlo,monospace; font-size:12px; color:#5a5642; }
  .status .checks{ display:flex; flex-wrap:wrap; gap:8px; margin:12px 0 0; }
  .status .chk{ font-family:ui-monospace,Menlo,monospace; font-size:11.5px; padding:3px 9px; border-radius:999px; background:#fff; border:1px solid var(--line); color:var(--muted); }
  .status .chk b{ color:var(--ink); }
  .status .chk.green{ background:var(--green-bg); border-color:var(--green-line); color:var(--green); } .status .chk.green b{ color:var(--green); }
  .status .chk.amber{ background:var(--amber-bg); border-color:var(--amber-line); color:var(--amber); } .status .chk.amber b{ color:var(--amber); }
  .status .chk.red{ background:var(--red-bg); border-color:var(--red-line); color:var(--red); } .status .chk.red b{ color:var(--red); }
  .howto{ background:var(--card); border:1px solid var(--line); border-radius:10px; padding:16px 20px; margin:0 0 34px; }
  .howto h3{ margin:0 0 10px; font-size:12px; letter-spacing:.12em; text-transform:uppercase; color:var(--faint); font-weight:700; }
  .howto ul{ margin:0; padding-left:18px; } .howto li{ font-size:14px; color:var(--muted); margin:6px 0; } .howto b{ color:var(--ink); }
  section{ margin:0 0 30px; }
  h2{ font-size:20px; font-weight:750; letter-spacing:-.01em; margin:0 0 12px; padding-top:10px; }
  h2 .num{ font-family:ui-monospace,Menlo,monospace; font-size:13px; color:var(--brand); margin-right:10px; }
  p.lead{ margin:0 0 12px; }
  ul.clean{ margin:0; padding-left:20px; } ul.clean li{ margin:7px 0; }
  .cid{ font-family:ui-monospace,Menlo,monospace; font-size:12px; color:var(--brand); background:var(--brand-soft); padding:1px 6px; border-radius:5px; }
  table{ width:100%; border-collapse:collapse; font-size:14px; }
  th,td{ text-align:left; padding:10px 8px; border-bottom:1px solid var(--line); vertical-align:top; }
  th{ font-size:11px; letter-spacing:.07em; text-transform:uppercase; color:var(--faint); font-weight:700; }
  .tag{ display:inline-block; font-family:ui-monospace,Menlo,monospace; font-size:11px; padding:2px 7px; border-radius:5px; }
  .tag.open{ background:#fdecea; color:var(--red); } .tag.part{ background:#fdf6e3; color:var(--amber); } .tag.done{ background:#e7f6ee; color:var(--green); } .tag.kind{ background:#eef0f3; color:var(--muted); }
  .opt{ border:1px solid var(--line); border-radius:10px; padding:16px 18px; margin:12px 0; background:var(--card); }
  .opt h4{ margin:0 0 4px; font-size:16px; }
  .opt .chip{ float:right; font-family:ui-monospace,Menlo,monospace; font-size:11px; padding:3px 9px; border-radius:999px; font-weight:700; }
  .chip.s-strong{ background:#e7f6ee; color:var(--green); } .chip.s-mod{ background:#fdf6e3; color:var(--amber); }
  .chip.s-weak{ background:#fdecea; color:var(--red); } .chip.s-none{ background:#eef0f3; color:var(--muted); }
  .opt .when{ font-size:13px; color:var(--faint); margin-top:8px; } .opt ul{ margin:8px 0 0; padding-left:18px; font-size:14px; }
  .src{ list-style:none; padding:0; margin:0; }
  .src li{ padding:9px 0; border-bottom:1px solid var(--line); font-size:13.5px; }
  .src .sid{ font-family:ui-monospace,Menlo,monospace; color:var(--brand); margin-right:8px; }
  .src .ty{ font-family:ui-monospace,Menlo,monospace; font-size:11px; color:var(--faint); }
  .src .syn{ color:var(--red); font-weight:600; }
  .src .slink{ color:var(--ink); text-decoration:none; border-bottom:1px solid var(--brand-soft); }
  .src .slink:hover{ border-bottom-color:var(--brand); }
  a.cid.clink{ text-decoration:none; }
  a.cid.clink:hover{ background:var(--brand); color:#fff; }
  :target{ scroll-margin-top:16px; }
  .src .note{ display:block; color:var(--faint); font-size:12.5px; margin-top:2px; }
  .findings{ display:flex; flex-direction:column; gap:16px; }
  .fcard{ position:relative; border:1px solid var(--line); border-radius:14px; padding:22px 26px; background:#fff; }
  .fcard.contested{ background:#fdf9f2; border-color:#efe2cf; }
  .fcard .fnum{ position:absolute; top:18px; right:18px; width:26px; height:26px; border-radius:50%; background:var(--ink); color:#fff; font-size:12.5px; font-weight:700; display:flex; align-items:center; justify-content:center; }
  .fcard .fkicker{ font-family:ui-monospace,Menlo,monospace; font-size:10.5px; letter-spacing:.09em; text-transform:uppercase; color:#9a6a1e; margin:0 38px 8px 0; }
  .fcard .ftitle{ font-size:16.5px; line-height:1.35; margin:0 38px 10px 0; }
  .fcard .fhead{ display:flex; align-items:baseline; gap:10px; margin:0 0 12px; }
  .fcard .rel-pill{ font-family:ui-monospace,Menlo,monospace; font-size:10.5px; letter-spacing:.08em; color:var(--brand); background:var(--brand-soft); padding:3px 9px; border-radius:999px; }
  .fcard .rel-score{ font-family:ui-monospace,Menlo,monospace; font-size:13px; color:var(--muted); }
  .fcard .rel-score b{ color:var(--ink); }
  .fcard .fbody{ font-size:14.5px; line-height:1.62; color:var(--ink); }
  .finding-attrs{ margin-top:14px; display:flex; flex-direction:column; gap:7px; }
  .attr{ display:block; font-size:13.5px; color:var(--ink); line-height:1.5; }
  .attr .attr-label{ display:inline-block; font-family:ui-monospace,Menlo,monospace; font-size:10px; letter-spacing:.09em; font-weight:700; padding:2px 7px; border-radius:5px; margin-right:8px; vertical-align:1px; }
  .attr.supported .attr-label{ background:#e7f6ee; color:var(--green); }
  .attr.challenged .attr-label{ background:#fdecea; color:var(--red); }
  .attr.corrected .attr-label{ background:#fef3e2; color:#9a6a1e; }
  .attr .attr-note{ color:var(--muted); }
  .scores{ display:flex; flex-wrap:wrap; gap:8px; margin:4px 0 14px; }
  .score{ font-family:ui-monospace,Menlo,monospace; font-size:12px; background:var(--card); border:1px solid var(--line); border-radius:8px; padding:7px 11px; } .score b{ color:var(--brand); }
  footer{ margin-top:38px; padding-top:18px; border-top:1px solid var(--line); font-size:12px; color:var(--faint); } footer p{ margin:6px 0; }
  footer a{ color:var(--brand); text-decoration:none; border-bottom:1px solid var(--brand-soft); }
  @media print{ body{background:#fff} .page{border:0; box-shadow:none; margin:0; max-width:none} }
  @media (max-width:640px){ .page{padding:30px 22px} .report-header{display:block} .brand-logo{margin:0 0 20px} h1{font-size:27px} }
"""

_STATUS_CLASS = {"pass": "green", "verified": "green", "source_checked": "green",
                 "pass_with_caveats": "", "caveats": "", "illustrative": "",
                 "revise": "red", "blocked": "red"}
_STRENGTH = {"strong": ("s-strong", "evidence: strong"), "moderate": ("s-mod", "evidence: moderate"),
             "weak": ("s-weak", "evidence: weak"), "unsupported": ("s-none", "unsupported")}
_CONFLICT = {"unresolved": ("open", "unresolved"), "partly": ("part", "partly"),
             "partially_resolved": ("part", "partly"), "resolved": ("done", "resolved")}


def e(x) -> str:
    return html.escape(str(x if x is not None else ""))


_ANCHORS: set = set()


def refs(ids) -> str:
    out = []
    for i in (ids or []):
        if i in _ANCHORS:
            out.append(f' <a class="cid clink" href="#ref-{e(i)}">{e(i)}</a>')
        else:
            out.append(f' <span class="cid">{e(i)}</span>')
    return "".join(out)


def _logo_svg() -> str:
    icon = Path(__file__).resolve().parents[1] / "assets" / "icon.svg"
    try:
        return icon.read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def build(data: dict) -> str:
    counts = data.get("counts", {})
    st = data.get("status", {})
    scores = st.get("scores", {})
    p: list[str] = []
    a = p.append

    _ANCHORS.clear()
    for s in data.get("sources", []) or []:
        if s.get("id"):
            _ANCHORS.add(s["id"])
    for c in data.get("contradictions", []) or []:
        if c.get("id"):
            _ANCHORS.add(c["id"])

    a("<!doctype html>\n<html lang=\"en\">\n<head>\n<meta charset=\"utf-8\" />")
    a('<meta name="viewport" content="width=device-width, initial-scale=1" />')
    a(f"<title>{e(data.get('title','Storm Council report'))}</title>")
    a("<style>" + CSS + "</style>\n</head>\n<body>\n<main class=\"page\">")

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
    if data.get("date"): meta.append(f'<span><b>Date</b> {e(data["date"])}</span>')
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
            srow = ('<p class="verdict">Review verdict: <b>%s</b> · coverage %s · traceability %s · '
                    'contradiction-handling %s · recommendation-support %s</p>' % (
                        e(verdict), e(scores.get("coverage","-")), e(scores.get("traceability","-")),
                        e(scores.get("contradiction","-")), e(scores.get("recommendation","-"))))
        crow = ""
        checks = st.get("checks")
        if checks:
            chips = "".join(
                '<span class="chk %s"><b>%s</b> %s</span>' % (
                    e(str(c.get("tone", "")).lower()), e(c.get("value", "")), e(c.get("label", "")))
                for c in checks)
            crow = f'<div class="checks">{chips}</div>'
        a('<div class="status %s"><span class="pill">%s</span><b>%s</b><p>%s</p>%s%s</div>' % (
            cls, e(st.get("pill", "STATUS")), e(st.get("headline", "")), e(st.get("detail", "")), crow, srow))

    howto = data.get("how_to_read") or [
        "<b>The panel is author-constructed.</b> Where the lenses agree, treat it as a strong hypothesis, not independent proof.",
        "<b>Confidence (0.0-1.0) is separate from evidence status.</b> A high-confidence forecast is still a forecast.",
        "<b>Fact, inference, and recommendation are labelled separately.</b>",
        "<b>Disagreements are kept on the record</b>, not resolved by force.",
    ]
    a('<div class="howto"><h3>How to read this</h3><ul>' +
      "".join(f"<li>{li}</li>" for li in howto) + "</ul></div>")

    def sec(num, title, body):
        a(f'<section><h2><span class="num">{num}</span>{e(title)}</h2>{body}</section>')

    if data.get("bottom_line"):
        sec("01", "Bottom line", f'<p class="lead">{e(data["bottom_line"])}</p>')

    def _attr(cls, label, d):
        persp = e(" + ".join(p.title() for p in d.get("perspectives", []))) if d.get("perspectives") else ""
        note = e(d.get("note", "")) if d.get("note") else ""
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
        body = f'<div class="fbody">{e(f.get("text",""))}{refs(f.get("claims"))}</div>'
        attrs = ""
        if f.get("supported_by"):
            attrs += _attr("supported", "SUPPORTED BY", f["supported_by"])
        if f.get("challenged_by"):
            attrs += _attr("challenged", "CHALLENGED BY", f["challenged_by"])
        cor = f.get("corrected")
        if cor:
            ctext = cor if isinstance(cor, str) else (cor.get("note", "") if isinstance(cor, dict) else "")
            if ctext:
                attrs += f'<span class="attr corrected"><span class="attr-label">CORRECTED</span>{e(ctext)}</span>'
        attrs_div = f'<div class="finding-attrs">{attrs}</div>' if attrs else ""
        cls = "fcard contested" if contested else "fcard"
        return f'<div class="{cls}">{num}{kicker}{title}{head}{body}{attrs_div}</div>'

    fnd = data.get("strongest_findings", [])
    if fnd:
        body = '<div class="findings">' + "".join(_finding_card(f, i) for i, f in enumerate(fnd, 1)) + "</div>"
        sec("02", "Strongest evidence-backed findings", body)

    cons = data.get("contradictions", [])
    if cons:
        rows = ""
        for c in cons:
            tcls, tlbl = _CONFLICT.get(str(c.get("status","")).lower(), ("part", c.get("status","")))
            rows += ('<tr id="ref-%s"><td class="mono">%s</td><td><span class="tag kind">%s</span></td>'
                     '<td>%s</td><td><span class="tag %s">%s</span></td></tr>' % (
                         e(c.get("id","")), e(c.get("id","")), e(c.get("kind","")), e(c.get("stake","")), tcls, e(tlbl)))
        body = ('<table><thead><tr><th>Conflict</th><th>Kind</th><th>What is at stake</th>'
                '<th>Status</th></tr></thead><tbody>' + rows + "</tbody></table>")
        sec("03", "Where the lenses disagree", body)

    opts = data.get("options", [])
    if opts:
        body = ""
        for o in opts:
            ccls, clbl = _STRENGTH.get(str(o.get("strength","")).lower(), ("s-none", o.get("strength","")))
            pts = "".join(f"<li>{e(x)}</li>" for x in o.get("points", []))
            when = f'<p class="when">When appropriate: {e(o["when"])}</p>' if o.get("when") else ""
            body += ('<div class="opt"><span class="chip %s">%s</span><h4>%s</h4><ul>%s</ul>%s</div>' % (
                ccls, e(clbl), e(o.get("name","")), pts, when))
        sec("04", "Decision options & trade-offs", body)

    acts = data.get("next_actions", [])
    if acts:
        body = '<ul class="clean">' + "".join(
            f'<li>{e(x.get("text",""))}{refs(x.get("refs"))}</li>' for x in acts) + "</ul>"
        sec("05", "Recommended next actions", body)

    gaps = data.get("gaps", [])
    if gaps:
        body = '<ul class="clean">' + "".join(
            f'<li>{e(g.get("text",""))}{refs(g.get("refs"))}</li>' for g in gaps) + "</ul>"
        sec("06", "Evidence gaps & frontier questions", body)

    srcs = data.get("sources", [])
    if srcs:
        items = ""
        for s in srcs:
            label = e(s.get("title", ""))
            url = s.get("url")
            if url and not s.get("synthetic"):
                label = f'<a class="slink" href="{e(url)}" target="_blank" rel="noopener">{label}</a>'
            title = f'<span class="syn">{label}</span>' if s.get("synthetic") else label
            note = f'<span class="note">{e(s["note"])}</span>' if s.get("note") else ""
            items += ('<li id="ref-%s"><span class="sid">%s</span> %s <span class="ty">· %s</span>%s</li>' % (
                e(s.get("id","")), e(s.get("id","")), title, e(s.get("type","")), note))
        sec("07", "Sources", '<ul class="src">' + items + "</ul>")

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
                    "".join(f"<li>{e(v)}</li>" for v in vals) + "</ul>"
        verdict = rev.get("verdict", "")
        body = (f'<div class="scores">{chips}</div>'
                f'<p class="lead">Verdict <b>{e(verdict)}</b>.</p>{issues}')
        sec("08", "Independent review", body)

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
    a("</main>\n</body>\n</html>\n")
    return "\n".join(p)


def _enrich_source_urls(data: dict, base: Path) -> None:
    """Fill missing source urls from a sibling 03_source_registry.csv so the
    report links its sources even when report_data.json omits per-source urls."""
    srcs = data.get("sources")
    if not srcs:
        return
    reg = base / "03_source_registry.csv"
    if not reg.exists():
        return
    url_by_id = {}
    with reg.open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            u = (row.get("url") or "").strip()
            if u and u.lower() != "null":
                url_by_id[(row.get("source_id") or "").strip()] = u
    for s in srcs:
        if not s.get("url"):
            u = url_by_id.get(s.get("id", ""))
            if u:
                s["url"] = u


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Render a Storm Council report (JSON -> HTML).")
    ap.add_argument("input", help="report_data.json")
    ap.add_argument("-o", "--output", default="storm_council_report.html")
    args = ap.parse_args(argv)
    data = json.loads(Path(args.input).read_text(encoding="utf-8"))
    _enrich_source_urls(data, Path(args.input).parent)
    Path(args.output).write_text(build(data), encoding="utf-8")
    print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
