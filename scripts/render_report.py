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
  .src .note{ display:block; color:var(--faint); font-size:12.5px; margin-top:2px; }
  .finding-attrs{ margin-top:8px; display:flex; flex-wrap:wrap; gap:6px; }
  .attr{ display:inline-flex; align-items:baseline; gap:5px; font-size:12px; padding:3px 9px 3px 8px; border-radius:6px; line-height:1.4; }
  .attr .attr-label{ font-family:ui-monospace,Menlo,monospace; font-size:10px; letter-spacing:.1em; font-weight:700; white-space:nowrap; }
  .attr.supported{ background:#e7f6ee; color:var(--green); }
  .attr.challenged{ background:#fdecea; color:var(--red); }
  .attr .attr-note{ color:var(--muted); }
  .scores{ display:flex; flex-wrap:wrap; gap:8px; margin:4px 0 14px; }
  .score{ font-family:ui-monospace,Menlo,monospace; font-size:12px; background:var(--card); border:1px solid var(--line); border-radius:8px; padding:7px 11px; } .score b{ color:var(--brand); }
  footer{ margin-top:38px; padding-top:18px; border-top:1px solid var(--line); font-size:12px; color:var(--faint); } footer p{ margin:6px 0; }
  @media print{ body{background:#fff} .page{border:0; box-shadow:none; margin:0; max-width:none} }
  @media (max-width:640px){ .page{padding:30px 22px} h1{font-size:27px} }
"""

_STATUS_CLASS = {"pass": "green", "pass_with_caveats": "", "caveats": "", "illustrative": "",
                 "revise": "red", "blocked": "red"}
_STRENGTH = {"strong": ("s-strong", "evidence: strong"), "moderate": ("s-mod", "evidence: moderate"),
             "weak": ("s-weak", "evidence: weak"), "unsupported": ("s-none", "unsupported")}
_CONFLICT = {"unresolved": ("open", "unresolved"), "partly": ("part", "partly"),
             "partially_resolved": ("part", "partly"), "resolved": ("done", "resolved")}


def e(x) -> str:
    return html.escape(str(x if x is not None else ""))


def refs(ids) -> str:
    return "".join(f' <span class="cid">{e(i)}</span>' for i in (ids or []))


def build(data: dict) -> str:
    counts = data.get("counts", {})
    st = data.get("status", {})
    scores = st.get("scores", {})
    p: list[str] = []
    a = p.append

    a("<!doctype html>\n<html lang=\"en\">\n<head>\n<meta charset=\"utf-8\" />")
    a('<meta name="viewport" content="width=device-width, initial-scale=1" />')
    a(f"<title>{e(data.get('title','Storm Council report'))}</title>")
    a("<style>" + CSS + "</style>\n</head>\n<body>\n<main class=\"page\">")

    a(f'<p class="eyebrow">{e(data.get("eyebrow", "Storm Council · Decision Brief"))}</p>')
    a(f'<h1>{e(data.get("title",""))}</h1>')
    if data.get("subtitle"):
        a(f'<p class="subtitle">{e(data["subtitle"])}</p>')

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
        a('<div class="status %s"><span class="pill">%s</span><b>%s</b><p>%s</p>%s</div>' % (
            cls, e(st.get("pill", "STATUS")), e(st.get("headline", "")), e(st.get("detail", "")), srow))

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

    def _finding_li(f):
        txt = e(f.get("text", ""))
        claim_refs = refs(f.get("claims"))
        attrs = ""
        sup = f.get("supported_by")
        if sup:
            persp = e(" + ".join(p.title() for p in sup.get("perspectives", [])))
            note = f' <span class="attr-note">— {e(sup["note"])}</span>' if sup.get("note") else ""
            attrs += f'<span class="attr supported"><span class="attr-label">SUPPORTED BY</span>{persp}{note}</span>'
        chal = f.get("challenged_by")
        if chal:
            persp = e(" + ".join(p.title() for p in chal.get("perspectives", [])))
            note = f' <span class="attr-note">— {e(chal["note"])}</span>' if chal.get("note") else ""
            attrs += f'<span class="attr challenged"><span class="attr-label">CHALLENGED BY</span>{persp}{note}</span>'
        attrs_div = f'<div class="finding-attrs">{attrs}</div>' if attrs else ""
        return f"<li>{txt}{claim_refs}{attrs_div}</li>"

    fnd = data.get("strongest_findings", [])
    if fnd:
        body = '<ul class="clean">' + "".join(_finding_li(f) for f in fnd) + "</ul>"
        sec("02", "Strongest evidence-backed findings", body)

    cons = data.get("contradictions", [])
    if cons:
        rows = ""
        for c in cons:
            tcls, tlbl = _CONFLICT.get(str(c.get("status","")).lower(), ("part", c.get("status","")))
            rows += ('<tr><td class="mono">%s</td><td><span class="tag kind">%s</span></td>'
                     '<td>%s</td><td><span class="tag %s">%s</span></td></tr>' % (
                         e(c.get("id","")), e(c.get("kind","")), e(c.get("stake","")), tcls, e(tlbl)))
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
            title = (f'<span class="syn">{e(s.get("title",""))}</span>' if s.get("synthetic")
                     else e(s.get("title","")))
            note = f'<span class="note">{e(s["note"])}</span>' if s.get("note") else ""
            items += ('<li><span class="sid">%s</span> %s <span class="ty">· %s</span>%s</li>' % (
                e(s.get("id","")), title, e(s.get("type","")), note))
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

    a('<footer><p><b>Storm Council</b> is inspired by research-first knowledge-curation systems '
      'such as Stanford OVAL\'s STORM. It is independently developed and is <b>not</b> affiliated '
      'with, endorsed by, or derived from Stanford University, Stanford OVAL, the STORM project, '
      'Anthropic, Claude Code, or YouMind.</p>'
      '<p>This brief supports research and deliberation. It does not replace domain expertise, '
      'source verification, or accountable human decision-making.</p></footer>')
    a("</main>\n</body>\n</html>\n")
    return "\n".join(p)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Render a Storm Council report (JSON -> HTML).")
    ap.add_argument("input", help="report_data.json")
    ap.add_argument("-o", "--output", default="storm_council_report.html")
    args = ap.parse_args(argv)
    data = json.loads(Path(args.input).read_text(encoding="utf-8"))
    Path(args.output).write_text(build(data), encoding="utf-8")
    print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
