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
import math
import re
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
  .mono{ font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace; white-space:nowrap; }
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
  .verdict-panel{ margin-top:14px; padding:12px 14px; border-radius:9px; background:rgba(255,255,255,.55); border:1px solid rgba(0,0,0,.07); display:flex; flex-wrap:wrap; align-items:center; gap:10px 16px; }
  .verdict-panel-label{ font-family:ui-monospace,Menlo,monospace; font-size:10px; letter-spacing:.12em; text-transform:uppercase; color:var(--faint); white-space:nowrap; }
  .verdict-status-badge{ font-family:ui-monospace,Menlo,monospace; font-size:12px; font-weight:700; padding:4px 12px; border-radius:999px; letter-spacing:.03em; white-space:nowrap; }
  .verdict-status-badge.vb-pass{ background:var(--green); color:#fff; }
  .verdict-status-badge.vb-caveats{ background:var(--amber); color:#fff; }
  .verdict-status-badge.vb-fail{ background:var(--red); color:#fff; }
  .verdict-status-badge.vb-unknown{ background:var(--faint); color:#fff; }
  .verdict-divider{ width:1px; height:28px; background:rgba(0,0,0,.1); flex-shrink:0; }
  .verdict-scores{ display:flex; flex-wrap:wrap; gap:6px; }
  .vscore{ display:flex; flex-direction:column; align-items:center; background:rgba(255,255,255,.7); border:1px solid rgba(0,0,0,.08); border-radius:8px; padding:6px 10px; min-width:68px; }
  .vscore-val{ font-family:ui-monospace,Menlo,monospace; font-size:17px; font-weight:800; line-height:1; color:var(--ink); }
  .vscore-key{ font-size:9.5px; color:var(--faint); letter-spacing:.04em; text-transform:uppercase; margin-top:3px; text-align:center; line-height:1.2; }
  .vscore.ok .vscore-val{ color:var(--green); }
  .vscore.warn .vscore-val{ color:var(--amber); }
  .vscore.bad .vscore-val{ color:var(--red); }
  .status .checks{ display:flex; flex-wrap:wrap; gap:8px; margin:12px 0 0; }
  .status .chk{ font-family:ui-monospace,Menlo,monospace; font-size:11.5px; padding:5px 13px; border-radius:999px; background:rgba(255,255,255,.65); border:1px solid rgba(0,0,0,.09); color:var(--muted); display:inline-flex; align-items:baseline; gap:4px; box-shadow:0 1px 2px rgba(0,0,0,.04); }
  .status .chk b{ color:var(--ink); font-size:14px; font-weight:800; letter-spacing:-.015em; }
  .status .chk.green{ border-color:var(--green-line); } .status .chk.green b{ color:var(--green); }
  .status .chk.amber{ border-color:var(--amber-line); } .status .chk.amber b{ color:var(--amber); }
  .status .chk.red{ border-color:var(--red-line); } .status .chk.red b{ color:var(--red); }
  .howto{ background:var(--card); border:1px solid var(--line); border-radius:10px; padding:16px 20px; margin:0 0 34px; }
  .howto h3{ margin:0 0 10px; font-size:12px; letter-spacing:.12em; text-transform:uppercase; color:var(--faint); font-weight:700; }
  .howto ul{ margin:0; padding-left:18px; } .howto li{ font-size:14px; color:var(--muted); margin:6px 0; } .howto b{ color:var(--ink); }
  .kpi-card{ display:flex; gap:14px; align-items:flex-start; background:var(--card); border:1px solid var(--line);
    border-radius:10px; padding:16px 20px; margin:0 0 16px; }
  .kpi-icon{ font-size:20px; line-height:1; flex:none; }
  .kpi-title{ display:block; font-size:13px; color:var(--ink); margin:0 0 4px; }
  .kpi-desc{ margin:0; font-size:13.5px; line-height:1.55; color:var(--muted); }
  .kpi-desc code{ font-family:ui-monospace,Menlo,monospace; font-size:.92em; background:#eef0f3; color:var(--ink);
    padding:1px 5px; border-radius:4px; }
  section{ margin:0 0 30px; }
  h2{ font-size:20px; font-weight:750; letter-spacing:-.01em; margin:0 0 12px; padding-top:10px; }
  h2 .num{ font-family:ui-monospace,Menlo,monospace; font-size:13px; color:var(--brand); margin-right:10px; }
  p.lead{ margin:0 0 12px; }
  .bottom-line-card{ background:var(--brand-soft); border-radius:14px; padding:24px 28px 24px 32px; box-shadow:inset 4px 0 0 var(--brand); }
  .bottom-line-card p{ font-size:18px; line-height:1.68; font-weight:500; color:var(--ink); margin:0; letter-spacing:-.012em; }
  ul.clean{ margin:0; padding-left:20px; } ul.clean li{ margin:7px 0; }
  ul.sub{ margin:4px 0 4px 20px; padding-left:16px; } ul.sub li{ margin:4px 0; font-size:13px; color:var(--muted); }
  .cid{ font-family:ui-monospace,Menlo,monospace; font-size:12px; color:var(--brand); background:var(--brand-soft); padding:1px 6px; border-radius:5px; white-space:nowrap; }
  table{ width:100%; border-collapse:collapse; font-size:14px; }
  th,td{ text-align:left; padding:10px 8px; border-bottom:1px solid var(--line); vertical-align:top; }
  th{ font-size:11px; letter-spacing:.07em; text-transform:uppercase; color:var(--faint); font-weight:700; }
  .tag{ display:inline-block; font-family:ui-monospace,Menlo,monospace; font-size:11px; padding:2px 7px; border-radius:5px; }
  .tag.open{ background:#fdecea; color:var(--red); } .tag.part{ background:#fdf6e3; color:var(--amber); } .tag.done{ background:#e7f6ee; color:var(--green); } .tag.kind{ background:#eef0f3; color:var(--muted); }
  .lens-radar{ display:grid; grid-template-columns:minmax(210px,250px) 1fr; gap:20px; align-items:center; margin:0 0 18px;
    padding:17px 18px; border:1px solid var(--line); border-radius:10px; background:var(--card); }
  .lens-radar-plot{ min-width:0; }
  .lens-radar-chart{ display:block; width:100%; max-width:250px; height:auto; margin:0 auto; }
  .lens-radar-grid{ fill:none; stroke:#dde0e6; stroke-width:1; }
  .lens-radar-axis{ stroke:#e5e7ec; stroke-width:1; }
  .lens-radar-area{ fill:rgba(91,70,200,.16); stroke:var(--brand); stroke-width:2; }
  .lens-radar-dot{ fill:var(--brand); stroke:#fff; stroke-width:1.5; }
  .lens-radar-label{ font-family:ui-monospace,Menlo,monospace; font-size:9.5px; fill:var(--muted); }
  .lens-radar-scale{ margin:8px 0 0; text-align:center; font-family:ui-monospace,Menlo,monospace; font-size:11px; color:var(--faint); }
  .lens-radar-kicker{ margin:0 0 6px; font-family:ui-monospace,Menlo,monospace; font-size:11px; letter-spacing:.1em; text-transform:uppercase; color:var(--brand); font-weight:700; }
  .lens-radar-summary{ margin:0 0 8px; font-size:14.5px; color:var(--ink); line-height:1.55; }
  .lens-radar-note{ margin:0 0 12px; font-size:12.5px; color:var(--faint); }
  .lens-list{ display:grid; gap:6px; }
  .lens-row{ display:grid; grid-template-columns:minmax(88px,.7fr) 1fr auto; gap:8px; align-items:center; font-size:12.5px; }
  .lens-name{ font-family:ui-monospace,Menlo,monospace; color:var(--ink); }
  .lens-stance{ color:var(--muted); min-width:0; overflow-wrap:anywhere; }
  .lens-score{ font-family:ui-monospace,Menlo,monospace; color:var(--faint); }
  .lens-tone{ display:inline-block; width:8px; height:8px; border-radius:50%; margin-right:6px; vertical-align:1px; background:var(--brand); }
  .lens-tone.challenge{ background:var(--red); } .lens-tone.caution{ background:var(--amber); } .lens-tone.mixed{ background:var(--faint); } .lens-tone.support{ background:var(--green); }
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
  .src .source-meta{ display:flex; flex-wrap:wrap; gap:4px 12px; margin-top:4px; color:var(--faint); font-size:12px; }
  .src .source-meta b{ color:var(--muted); font-weight:600; }
  .bibtex-detail{ margin-top:14px; border:1px solid var(--line); border-radius:10px; background:var(--card); padding:10px 12px; }
  .bibtex-detail summary{ cursor:pointer; font-family:ui-monospace,Menlo,monospace; font-size:12px; color:var(--brand); }
  .bibtex-detail pre{ margin:10px 0 0; overflow:auto; white-space:pre; font:12px/1.45 ui-monospace,SFMono-Regular,Menlo,Consolas,monospace; color:var(--muted); }
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
  .charters{ display:grid; gap:18px; }
  .charter{ border:1px solid var(--ca-border,var(--line)); border-top:3px solid var(--ca,var(--brand)); border-radius:14px; padding:20px 22px 22px; background:var(--ca-bg,var(--card)); position:relative; overflow:hidden; }
  .charter::after{ content:""; position:absolute; top:0; right:0; width:180px; height:180px; border-radius:50%; background:var(--ca,var(--brand)); opacity:.04; transform:translate(38%,-46%); pointer-events:none; }
  .charter--academic    { --ca:#3b5bdb; --ca-bg:#f8f9ff; --ca-border:rgba(59,91,219,.18); }
  .charter--economist   { --ca:#087f5b; --ca-bg:#f3fbf7; --ca-border:rgba(8,127,91,.18); }
  .charter--historian   { --ca:#c47c08; --ca-bg:#fdf9ef; --ca-border:rgba(196,124,8,.18); }
  .charter--practitioner{ --ca:#6741d9; --ca-bg:#faf8ff; --ca-border:rgba(103,65,217,.18); }
  .charter--skeptic     { --ca:#c92a2a; --ca-bg:#fff5f5; --ca-border:rgba(201,42,42,.18); }
  .charter h4{ margin:0 0 6px; font-size:17px; font-weight:700; letter-spacing:-.015em; text-transform:capitalize; color:var(--ca,var(--ink)); display:flex; align-items:center; gap:9px; }
  .ca-icon-svg{ width:18px; height:18px; flex-shrink:0; color:var(--ca,var(--brand)); }
  .charter .role{ margin:0 0 16px; font-size:14.5px; color:var(--ink); line-height:1.5; padding-bottom:14px; border-bottom:1px solid var(--ca-border,var(--line)); }
  .charter .ch-grid{ display:grid; grid-template-columns:1fr 1fr; gap:13px 26px; }
  .charter .ch-block h5{ margin:0 0 5px; font-size:10px; letter-spacing:.1em; text-transform:uppercase; color:var(--ca,var(--faint)); font-weight:700; opacity:.75; }
  .charter .ch-block ul{ margin:0; padding-left:16px; } .charter .ch-block li{ font-size:13px; color:var(--muted); margin:4px 0; }
  .charter .ch-block p{ margin:0; font-size:13px; color:var(--muted); line-height:1.55; }
  .claims-table td .lim{ display:block; color:var(--faint); font-size:12px; margin-top:4px; }
  .claims-table td .cev{ display:block; font-size:12px; color:var(--muted); margin-top:4px; }
  .claims-table td .claim-meta{ display:block; margin-top:6px; }
  .claim-chip{ display:inline-flex; align-items:center; gap:4px; font:11px ui-monospace,Menlo,monospace; padding:2px 8px; border-radius:999px; background:#eef0f3; color:var(--muted); margin-right:4px; }
  .evidence-table .excerpt{ color:var(--muted); font-size:12.5px; line-height:1.45; }
  .verdict-list{ display:flex; flex-direction:column; gap:4px; min-width:130px; }
  .verdict-row{ display:flex; flex-wrap:wrap; align-items:center; gap:4px; }
  .verdict-rationale{ display:block; color:var(--faint); font-size:11.5px; line-height:1.35; margin-top:1px; }
  .verdict-bad{ background:#fdecea; color:var(--red); }
  .verdict-warn{ background:#fef3e2; color:#9a6a1e; }
  .verdict-ok{ background:#e7f6ee; color:var(--green); }
  .artifact{ border:1px solid var(--line); border-radius:10px; background:var(--card); padding:16px 18px; }
  .artifact h4{ margin:14px 0 7px; font-size:14.5px; }
  .artifact h4:first-child{ margin-top:0; }
  .artifact p.lead{ font-size:14px; color:var(--ink); }
  .artifact ul.clean,.artifact ol{ margin:0 0 12px; padding-left:20px; }
  .artifact li{ margin:5px 0; font-size:14px; color:var(--muted); }
  .qcard-grid{ display:grid; gap:8px; margin:10px 0 16px; }
  .qcard{ border:1px solid var(--line); border-radius:8px; padding:11px 14px; background:#fff; }
  .qhead{ display:flex; align-items:center; gap:10px; margin-bottom:0; }
  .qterm{ font-size:12.5px; color:var(--ink); flex:1; background:var(--brand-soft); padding:3px 8px; border-radius:5px; font-family:ui-monospace,Menlo,monospace; }
  .qbadge{ font-size:10.5px; font-family:ui-monospace,Menlo,monospace; padding:2px 8px; border-radius:999px; white-space:nowrap; font-weight:600; }
  .qbadge.hits{ background:#d1fae5; color:#065f46; }
  .qbadge.zero{ background:#f3f4f6; color:#9ca3af; }
  .qresults{ margin-top:8px; border-top:1px solid var(--line); padding-top:6px; display:flex; flex-direction:column; gap:5px; }
  .qresult{ font-size:12.5px; display:flex; justify-content:space-between; align-items:flex-start; gap:12px; line-height:1.4; }
  .qtitle{ flex:1; }
  .qtitle a{ color:var(--ink); text-decoration:none; font-weight:500; } .qtitle a:hover{ text-decoration:underline; color:var(--brand); }
  .qauthors{ color:var(--muted); font-size:12px; }
  .qvenue{ font-style:italic; color:var(--muted); font-size:12px; }
  .qyear{ font-size:12px; color:var(--muted); margin-left:4px; }
  .qcite{ display:inline-flex; align-items:center; font:10.5px ui-monospace,Menlo,monospace; padding:1px 7px; border-radius:999px; background:#eef0f3; color:var(--muted); white-space:nowrap; margin-top:2px; }
  .qnull{ color:var(--muted); font-style:italic; font-size:12px; }
  .lplan-kicker{ font-family:ui-monospace,Menlo,monospace; font-size:11px; letter-spacing:.1em; text-transform:uppercase; color:var(--faint); margin:18px 0 2px; }
  .lplan-intro{ font-size:13px; color:var(--muted); margin:0 0 12px; max-width:64ch; }
  .lplan-grid{ display:grid; grid-template-columns:repeat(auto-fit,minmax(290px,1fr)); gap:12px; margin:0 0 16px; }
  .lplan{ border:1px solid var(--line); border-radius:10px; padding:14px 16px; background:#fff; }
  .lplan-head{ display:flex; align-items:center; gap:8px; margin:0 0 12px; padding:0 0 10px; border-bottom:1px solid var(--line); }
  .lplan-ic{ flex:0 0 auto; display:inline-flex; line-height:0; }
  .lplan-ic svg{ width:18px; height:18px; display:block; }
  .lplan-name{ font-family:ui-monospace,Menlo,monospace; font-size:13px; font-weight:700; text-transform:capitalize; color:var(--ink); letter-spacing:.01em; }
  .lplan-label{ display:block; font-family:ui-monospace,Menlo,monospace; font-size:10px; letter-spacing:.11em; text-transform:uppercase; color:var(--faint); margin:0 0 4px; }
  .lplan-val{ font-size:13px; line-height:1.55; color:var(--muted); }
  .lplan-falsify{ background:var(--amber-bg); border:1px solid var(--amber-line); border-radius:8px; padding:9px 11px; margin-top:12px; }
  .lplan-falsify .lplan-label{ color:var(--amber); }
  .lplan-falsify .lplan-val{ color:#6b5d2e; }
  .artifact table{ margin:6px 0 14px; background:#fff; }
  .artifact code{ font-family:ui-monospace,Menlo,monospace; font-size:.92em; color:var(--brand); }
  .cx-detail{ margin-top:9px; }
  .cx-detail summary{ cursor:pointer; font-family:ui-monospace,Menlo,monospace; font-size:12px; color:var(--brand); }
  .cx-detail p{ margin:8px 0 0; font-size:13px; color:var(--muted); line-height:1.5; }
  .cx-detail .cx-why{ color:var(--ink); }
  .cx-detail .cx-meta{ font-family:ui-monospace,Menlo,monospace; font-size:12px; color:var(--faint); }
  .field-detail{ margin-top:8px; }
  .field-detail summary{ cursor:pointer; font-family:ui-monospace,Menlo,monospace; font-size:12px; color:var(--brand); }
  .field-detail dl{ margin:8px 0 0; display:grid; grid-template-columns:minmax(92px,max-content) 1fr; gap:5px 10px; }
  .field-detail dt{ font-family:ui-monospace,Menlo,monospace; font-size:11px; color:var(--faint); }
  .field-detail dd{ margin:0; font-size:12.5px; color:var(--muted); line-height:1.45; min-width:0; }
  .moves{ display:flex; flex-direction:column; gap:11px; margin:0 0 6px; }
  .round-h{ font-family:ui-monospace,Menlo,monospace; font-size:11px; letter-spacing:.1em; text-transform:uppercase; color:var(--faint); font-weight:700; margin:16px 0 8px; }
  .round-h:first-child{ margin-top:0; }
  .move{ display:grid; grid-template-columns:minmax(108px,auto) 1fr; gap:14px; padding:12px 15px; border:1px solid var(--line); border-radius:10px; background:var(--card); }
  .move .mv-side{ display:flex; flex-direction:column; gap:6px; align-items:flex-start; }
  .move .mv-lens{ font-family:ui-monospace,Menlo,monospace; font-size:12.5px; color:var(--ink); text-transform:capitalize; }
  .move .mv-target{ font-size:11px; }
  .move .mv-text{ font-size:13.5px; color:var(--ink); line-height:1.55; }
  .argmap-wrap{ overflow-x:auto; border:1px solid var(--line); border-radius:10px; background:var(--card); padding:12px; }
  .argmap{ display:block; }
  .am-node{ fill:#fff; stroke:#cfd3da; stroke-width:1.2; }
  .am-node.am-src{ fill:#eef6f1; stroke:var(--green-line); }
  .am-node.am-x{ fill:#fdf6e3; stroke:var(--amber-line); }
  .am-node.am-q{ fill:var(--brand-soft); stroke:var(--brand); }
  .am-desc{ font:11px -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif; fill:var(--ink); }
  .am-edge{ stroke:#b9bdc7; stroke-width:1.4; fill:none; }
  .am-edge.am-dotted{ stroke-dasharray:4 3; stroke:#cdb47a; }
  .am-ref{ font:10px ui-monospace,Menlo,monospace; fill:var(--brand); }
  .am-ref-plain{ fill:var(--faint); }
  .am-cap{ margin:9px 2px 0; font-size:12px; color:var(--faint); line-height:1.5; }
  .argmap-interactive{ margin:0; }
  .am-toolbar{ display:flex; flex-wrap:wrap; align-items:center; justify-content:space-between; gap:8px 14px; margin:0 0 10px; }
  .am-filter{ display:flex; flex-wrap:wrap; gap:6px; }
  .am-toggle{ display:inline-flex; align-items:center; gap:5px; font-family:ui-monospace,Menlo,monospace; font-size:11.5px;
    color:var(--muted); background:var(--card); border:1px solid var(--line); border-radius:999px; padding:3px 10px; cursor:pointer; user-select:none; }
  .am-toggle input{ accent-color:var(--brand); margin:0; }
  .am-hint{ font-size:11.5px; color:var(--faint); }
  .am-layout{ display:inline-flex; border:1px solid var(--line); border-radius:999px; overflow:hidden; background:var(--card); }
  .am-lybtn{ font-family:ui-monospace,Menlo,monospace; font-size:11.5px; color:var(--muted); background:transparent;
    border:0; padding:4px 13px; cursor:pointer; }
  .am-lybtn + .am-lybtn{ border-left:1px solid var(--line); }
  .am-lybtn.is-active{ background:var(--brand); color:#fff; }
  .am-cy{ display:none; width:100%; height:520px; border:1px solid var(--line); border-radius:10px; background:var(--card); }
  .am-details{ margin:10px 0 0; border:1px solid var(--line); border-left:3px solid var(--brand); border-radius:8px;
    background:#fff; padding:11px 14px; font-size:13.5px; line-height:1.55; }
  .am-details .am-d-head{ display:flex; align-items:baseline; gap:8px; flex-wrap:wrap; }
  .am-details .am-d-ref{ font-family:ui-monospace,Menlo,monospace; font-size:11px; color:var(--brand); background:var(--brand-soft); padding:1px 7px; border-radius:5px; }
  .am-details .am-d-note{ margin:6px 0 0; color:var(--muted); }
  .am-details .am-jump{ display:inline-block; margin-top:8px; font-family:ui-monospace,Menlo,monospace; font-size:12px; color:var(--brand); text-decoration:none; }
  .am-details .am-jump:hover{ text-decoration:underline; }
  @media print{ .am-toolbar,.am-cy,.am-details{ display:none !important; } .am-static{ display:block !important; } }
  .toc{ position:fixed; top:40px; left:calc(50% - 614px); width:190px; max-height:calc(100vh - 80px);
    overflow-y:auto; padding-right:6px; }
  .toc h4{ margin:0 0 10px 10px; font-family:ui-monospace,Menlo,monospace; font-size:10px; letter-spacing:.14em;
    text-transform:uppercase; color:var(--faint); font-weight:700; }
  .toc ol{ list-style:none; margin:0; padding:0; }
  .toc a{ display:flex; gap:9px; padding:5px 10px; border-left:2px solid var(--line); color:var(--muted);
    text-decoration:none; font-size:12.5px; line-height:1.35; }
  .toc a:hover{ color:var(--ink); background:var(--card); }
  .toc a.active{ color:var(--brand); border-left-color:var(--brand); background:var(--brand-soft); font-weight:600; }
  .toc a .tn{ font-family:ui-monospace,Menlo,monospace; font-size:11px; color:var(--faint); flex:0 0 auto; }
  .toc a.active .tn{ color:var(--brand); }
  @media (max-width:1280px){ .toc{ display:none; } }
  @media print{ .toc{ display:none; } }
  @media (max-width:640px){ .page{padding:30px 22px} .report-header{display:block} .brand-logo{margin:0 0 20px} h1{font-size:27px}
    .lens-radar{ grid-template-columns:1fr; } .lens-radar-chart{ max-width:230px; } .lens-row{ grid-template-columns:1fr auto; }
    .lens-stance{ grid-column:1 / -1; padding-left:14px; } .charter .ch-grid{ grid-template-columns:1fr; } }
"""

_STATUS_CLASS = {"pass": "green", "verified": "green", "source_checked": "green",
                 "pass_with_caveats": "", "caveats": "", "illustrative": "",
                 "revise": "red", "blocked": "red"}
_STRENGTH = {"strong": ("s-strong", "evidence: strong"), "moderate": ("s-mod", "evidence: moderate"),
             "weak": ("s-weak", "evidence: weak"), "unsupported": ("s-none", "unsupported")}
_CONFLICT = {"unresolved": ("open", "unresolved"), "partly": ("part", "partly"),
             "partially_resolved": ("part", "partly"), "resolved": ("done", "resolved")}
_REF_RE = re.compile(r"\b[CSXE]-\d{3}\b")
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
# Lens icons are defined once in LENS_ICONS (single global source of truth, below).
# Charters render them via _lens_icon_ca(); see that helper near the LENS_ICONS block.
# Minimal Mermaid subset: a node is an id followed by a bracketed quoted label
# (any of [..], (..), {..}, [[..]], {{..}}, ([..])); an edge is `a --> b` or the
# dotted `a -.-> b`, optionally carrying a |label|.
_MMD_NODE_RE = re.compile(
    r'([A-Za-z0-9_]+)\s*(?:\[\[|\{\{|\(\[|\[|\(|\{)\s*"(.*?)"\s*(?:\]\]|\}\}|\]\)|\]|\)|\})'
)
_MMD_EDGE_RE = re.compile(
    r'([A-Za-z0-9_]+)\s*(-\.->|-->)\s*(?:\|[^|]*\|\s*)?([A-Za-z0-9_]+)'
)
# Matches BibTeX field assignments; handles up to two levels of nested braces in values.
_BIB_FIELD_RE = re.compile(
    r'(\w+)\s*=\s*(?:\{((?:[^{}]|\{(?:[^{}]|\{[^{}]*\})*\})*)\}|"([^"]*)")',
    re.DOTALL,
)


def _bib_normalize_id(key: str) -> str:
    """Convert BibTeX key like S001 -> S-001 to match JSON source IDs."""
    m = re.match(r'^([A-Za-z]+)(\d+)$', key.strip())
    if m:
        return f"{m.group(1).upper()}-{int(m.group(2)):03d}"
    return key.strip().upper()


def _parse_bibtex(bibtex: str) -> dict:
    """Parse BibTeX string to {normalized_id: {_type, field: value, ...}}."""
    entries: dict = {}
    text = str(bibtex)
    i = 0
    while i < len(text):
        at = text.find('@', i)
        if at == -1:
            break
        brace = text.find('{', at)
        if brace == -1:
            break
        etype = text[at + 1:brace].strip().lower()
        if etype in ('comment', 'string', 'preamble'):
            i = brace + 1
            continue
        depth, j = 1, brace + 1
        while j < len(text) and depth > 0:
            if text[j] == '{':
                depth += 1
            elif text[j] == '}':
                depth -= 1
            j += 1
        body = text[brace + 1:j - 1]
        i = j
        comma = body.find(',')
        if comma == -1:
            continue
        key = body[:comma].strip()
        rest = body[comma + 1:]
        fields: dict = {'_type': etype}
        for fm in _BIB_FIELD_RE.finditer(rest):
            fname = fm.group(1).lower()
            fval = fm.group(2) if fm.group(2) is not None else (fm.group(3) or '')
            if fname == 'author':
                # Keep inner braces intact — {Name} marks a corporate/literal author.
                fval = re.sub(r'\s+', ' ', fval).strip()
            else:
                fval = re.sub(r'\{\{([^{}]*)\}\}', r'\1', fval)
                fval = re.sub(r'\{([^{}]*)\}', r'\1', fval)
                fval = re.sub(r'\s+', ' ', fval).strip()
            fields[fname] = fval
        entries[_bib_normalize_id(key)] = fields
    return entries


def _bib_initials(name: str) -> str:
    return ' '.join(p[0].upper() + '.' for p in name.split() if p)


def _bib_author_apa(author_str: str) -> str:
    """Convert BibTeX author string to APA 7 author list."""
    if not author_str:
        return ''
    raw = re.split(r'\s+and\s+', author_str, flags=re.IGNORECASE)
    formatted: list = []
    has_et_al = False
    for a in raw:
        a = a.strip()
        if not a:
            continue
        if a.lower() in ('others', 'et al.', 'et al'):
            has_et_al = True
            continue
        # Braced name {Organization} = corporate/literal — don't reformat.
        if re.match(r'^\{[^{}]+\}$', a):
            formatted.append(a[1:-1])
        elif ',' in a:
            last, _, first = a.partition(',')
            initials = _bib_initials(first.strip())
            formatted.append(f"{last.strip()}, {initials}" if initials else last.strip())
        else:
            parts = a.split()
            if len(parts) == 1:
                formatted.append(parts[0])
            else:
                initials = _bib_initials(' '.join(parts[:-1]))
                formatted.append(f"{parts[-1]}, {initials}" if initials else parts[-1])
    if not formatted:
        return ''
    if has_et_al:
        return formatted[0] + ', et al.'
    if len(formatted) == 1:
        return formatted[0]
    if len(formatted) == 2:
        return f"{formatted[0]}, & {formatted[1]}"
    return ', '.join(formatted[:-1]) + ', & ' + formatted[-1]


def _format_apa_html(fields: dict, url: str = '') -> str:
    """Render BibTeX entry fields as an APA 7 HTML citation fragment."""
    etype = fields.get('_type', 'misc')
    author = _bib_author_apa(fields.get('author', ''))
    year = fields.get('year', 'n.d.')
    title = fields.get('title', '')
    use_url = url or fields.get('url', '')
    parts: list = []
    if author:
        author_esc = html.escape(author)
        # Initials already end with "."; corporate names don't — add period only when needed.
        parts.append(author_esc if author.endswith('.') else author_esc + '.')
    parts.append(f'({html.escape(year)}).')
    if etype == 'article':
        parts.append(html.escape(title) + '.')
        j = fields.get('journal', '')
        vol = fields.get('volume', '')
        num = fields.get('number', '')
        pages = fields.get('pages', '')
        if j:
            jstr = f'<em>{html.escape(j)}</em>'
            if vol:
                jstr += f', <em>{html.escape(vol)}</em>'
                if num:
                    jstr += f'({html.escape(num)})'
            if pages:
                jstr += f', {html.escape(pages)}'
            parts.append(jstr + '.')
    elif etype in ('inproceedings', 'conference', 'incollection'):
        parts.append(html.escape(title) + '.')
        bt = fields.get('booktitle', '')
        if bt:
            parts.append(f'In <em>{html.escape(bt)}</em>.')
    elif etype == 'book':
        parts.append(f'<em>{html.escape(title)}</em>.')
        pub = fields.get('publisher', '')
        if pub:
            parts.append(html.escape(pub) + '.')
    elif etype == 'techreport':
        parts.append(f'<em>{html.escape(title)}</em>.')
        inst = fields.get('institution', '')
        num = fields.get('number', '')
        detail = inst
        if num:
            detail = f'{detail} (No. {num})' if detail else f'(No. {num})'
        if detail:
            parts.append(html.escape(detail) + '.')
    else:
        parts.append(html.escape(title) + '.')
        pub = fields.get('publisher', '') or fields.get('organization', '')
        if pub:
            parts.append(html.escape(pub) + '.')
    result = ' '.join(p for p in parts if p)
    if use_url:
        result += (
            f' <a class="slink" href="{html.escape(use_url)}"'
            f' target="_blank" rel="noopener">{html.escape(use_url)}</a>'
        )
    return result


def _fmt_datetime_html(val: str) -> str:
    """Wrap ISO datetime strings in a <time> element for JS local-time conversion."""
    s = str(val).strip()
    if re.search(r'[T ]\d{2}:\d{2}', s):
        return f'<time class="ts-local" data-ts="{html.escape(s)}">{html.escape(s)}</time>'
    return html.escape(s)


def e(x) -> str:
    return html.escape(str(x if x is not None else ""))


_ANCHORS: set = set()
_EMITTED_CLAIM_TARGETS: set = set()


def _ref_chip(ref_id: str) -> str:
    if ref_id.startswith("C-"):
        target = ""
        if ref_id not in _EMITTED_CLAIM_TARGETS:
            _EMITTED_CLAIM_TARGETS.add(ref_id)
            target = f' id="ref-{e(ref_id)}"'
        return f'<a{target} class="cid clink" href="#ref-{e(ref_id)}">{e(ref_id)}</a>'
    if ref_id in _ANCHORS:
        return f'<a class="cid clink" href="#ref-{e(ref_id)}">{e(ref_id)}</a>'
    return f'<span class="cid">{e(ref_id)}</span>'


def text_refs(value) -> str:
    text = str(value if value is not None else "")
    parts = []
    last = 0
    for match in _REF_RE.finditer(text):
        parts.append(e(text[last:match.start()]))
        parts.append(_ref_chip(match.group(0)))
        last = match.end()
    parts.append(e(text[last:]))
    return "".join(parts)


def refs(ids) -> str:
    out = []
    if isinstance(ids, str):
        ids = [ids]
    for i in (ids or []):
        out.append(f" {_ref_chip(str(i))}")
    return "".join(out)


def _detail_value(value) -> str:
    if value is None or value == "" or value == [] or value == {}:
        return ""
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, (int, float)):
        return e(value)
    if isinstance(value, str):
        return text_refs(value)
    if isinstance(value, list):
        vals = [v for v in value if v is not None and v != ""]
        if not vals:
            return ""
        if all(isinstance(v, str) and re.fullmatch(r"[CSXE]-\d{3}", v) for v in vals):
            return refs(vals).strip()
        return "; ".join(_detail_value(v) for v in vals)
    if isinstance(value, dict):
        parts = []
        for k, v in value.items():
            rendered = _detail_value(v)
            if rendered:
                parts.append(f"{e(k)}: {rendered}")
        return "; ".join(parts)
    return text_refs(value)


def _field_details(rows, summary: str = "Details") -> str:
    rendered = []
    for label, value in rows:
        val = _detail_value(value)
        if val:
            rendered.append(f"<dt>{e(label)}</dt><dd>{val}</dd>")
    if not rendered:
        return ""
    return (
        f'<details class="field-detail"><summary>{e(summary)}</summary>'
        f'<dl>{"".join(rendered)}</dl></details>'
    )


def _rich_text(value) -> str:
    out = text_refs(value)
    out = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", out)
    out = re.sub(r"`([^`]+)`", r"<code>\1</code>", out)
    return out


def _is_table_row(s: str) -> bool:
    return s.startswith("|") and s.endswith("|") and s.count("|") >= 2


def _is_table_separator(s: str) -> bool:
    if not _is_table_row(s):
        return False
    cells = [c.strip() for c in s.strip("|").split("|")]
    return bool(cells) and all(re.fullmatch(r":?-{3,}:?", c or "") for c in cells)


def _table_cells(s: str) -> list[str]:
    return [c.strip() for c in s.strip().strip("|").split("|")]


def _table_html(lines: list[str]) -> str:
    if len(lines) < 2 or not _is_table_separator(lines[1]):
        return ""
    headers = _table_cells(lines[0])
    rows = [_table_cells(line) for line in lines[2:]]
    head = "".join(f"<th>{_rich_text(h)}</th>" for h in headers)
    body = ""
    for row in rows:
        cells = row + [""] * max(0, len(headers) - len(row))
        body += "<tr>" + "".join(f"<td>{_rich_text(c)}</td>" for c in cells[:len(headers)]) + "</tr>"
    return f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"


def _logo_svg() -> str:
    icon = Path(__file__).resolve().parents[1] / "assets" / "icon.svg"
    try:
        return icon.read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def _cytoscape_js() -> str:
    """Read the vendored Cytoscape.js library for inline embedding (no network).

    Returns '' if the asset is absent, so the report degrades to the static SVG.
    """
    lib = Path(__file__).resolve().parents[1] / "assets" / "vendor" / "cytoscape.min.js"
    try:
        return lib.read_text(encoding="utf-8")
    except OSError:
        return ""


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
    if not isinstance(snapshot, dict):
        return ""
    lenses = [x for x in snapshot.get("lenses", []) if isinstance(x, dict)]
    if len(lenses) < 3:
        return ""

    cx = 140.0
    cy = 115.0
    radius = 64.0
    step = 360.0 / len(lenses)
    angles = [-90.0 + i * step for i in range(len(lenses))]
    outer = [_radar_point(cx, cy, radius, a) for a in angles]
    grid = "".join(
        f'<polygon class="lens-radar-grid" points="{_fmt_points([_radar_point(cx, cy, radius * level, a) for a in angles])}" />'
        for level in (1 / 3, 2 / 3, 1)
    )
    axes = "".join(
        f'<line class="lens-radar-axis" x1="{cx:.1f}" y1="{cy:.1f}" x2="{x:.1f}" y2="{y:.1f}" />'
        for x, y in outer
    )
    area_points = [
        _radar_point(cx, cy, radius * _clamped_score(lens.get("score")), angle)
        for lens, angle in zip(lenses, angles)
    ]
    dots = "".join(
        f'<circle class="lens-radar-dot" cx="{x:.1f}" cy="{y:.1f}" r="3.5" />'
        for x, y in area_points
    )

    labels = ""
    for lens, angle in zip(lenses, angles):
        x, y = _radar_point(cx, cy, radius + 20, angle)
        anchor = "middle"
        if x < cx - 12:
            anchor = "end"
        elif x > cx + 12:
            anchor = "start"
        labels += (
            f'<text class="lens-radar-label" x="{x:.1f}" y="{y:.1f}" '
            f'text-anchor="{anchor}" dominant-baseline="middle">'
            f'{e(str(lens.get("name", "")).replace("_", " ").title())}</text>'
        )

    rows = ""
    tone_classes = {"support", "challenge", "caution", "mixed"}
    for lens in lenses:
        name = str(lens.get("name", "")).replace("_", " ").title()
        tone = str(lens.get("tone", "")).lower()
        tone_class = tone if tone in tone_classes else ""
        score = _clamped_score(lens.get("score"))
        stance = lens.get("stance") or lens.get("note") or ""
        rows += (
            '<div class="lens-row">'
            f'<span class="lens-name"><span class="lens-tone {e(tone_class)}"></span>{e(name)}</span>'
            f'<span class="lens-stance">{e(stance)}</span>'
            f'<span class="lens-score">{score:.2f}</span>'
            '</div>'
        )

    summary = snapshot.get("summary") or "A compact view of how strongly each council lens presses on the decision."
    scale = snapshot.get("scale_label") or "0 low emphasis · 1 high emphasis"
    title = snapshot.get("title") or "Lens posture snapshot"
    return (
        '<div class="lens-radar">'
        '<div class="lens-radar-plot">'
        '<svg class="lens-radar-chart" viewBox="0 0 280 230" role="img" aria-label="Five-lens council posture radar">'
        '<title>Five-lens council posture radar</title>'
        f"{grid}{axes}"
        f'<polygon class="lens-radar-area" points="{_fmt_points(area_points)}" />'
        f"{dots}{labels}"
        '</svg>'
        f'<p class="lens-radar-scale">{e(scale)}</p>'
        '</div>'
        '<div class="lens-radar-copy">'
        f'<p class="lens-radar-kicker">{e(title)}</p>'
        f'<p class="lens-radar-summary">{text_refs(summary)}</p>'
        '<p class="lens-radar-note">This is a council posture map, not a quality score.</p>'
        f'<div class="lens-list">{rows}</div>'
        '</div>'
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


# Stable accent per lens, echoing the council-posture tone semantics.
_LENS_DOT = {
    "practitioner": "var(--green)",
    "academic": "var(--brand)",
    "skeptic": "var(--red)",
    "economist": "var(--amber)",
    "historian": "var(--faint)",
}

# ── Lens icons: single global source of truth ─────────────────────────────────
# One canonical icon per research lens, as Lucide line-icon geometry on a 24×24
# viewBox, drawn in the lens accent via currentColor. EVERY place the report shows
# a lens icon (charters, lens plans, anywhere new) MUST read from this mapping —
# never define a second, divergent lens-icon set. See CLAUDE.md "Lens icons".
LENS_ICONS = {
    "practitioner": '<path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/>',
    "academic": '<path d="M21.42 10.92a1 1 0 0 0-.02-1.84L12.83 5.18a2 2 0 0 0-1.66 0L2.6 9.08a1 1 0 0 0 0 1.84l8.57 3.9a2 2 0 0 0 1.66 0z"/><path d="M22 10v6"/><path d="M6 12.5V16a6 3 0 0 0 12 0v-3.5"/>',
    "skeptic": '<circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/>',
    "economist": '<polyline points="22 7 13.5 15.5 8.5 10.5 2 17"/><polyline points="16 7 22 7 22 13"/>',
    "historian": '<path d="M19 17V5a2 2 0 0 0-2-2H4"/><path d="M8 21h12a2 2 0 0 0 2-2v-1a1 1 0 0 0-1-1H11a1 1 0 0 0-1 1v1a2 2 0 1 1-4 0V5a2 2 0 1 0-4 0v2a1 1 0 0 0 1 1h3"/>',
}
LENS_ICON_FALLBACK = '<circle cx="12" cy="12" r="9"/>'


def _lens_icon_inner(name: str) -> str:
    """Canonical inner SVG geometry for a lens, from the global LENS_ICONS map."""
    return LENS_ICONS.get(name.lower(), LENS_ICON_FALLBACK)


def _lens_icon_svg(name: str, accent: str) -> str:
    return (
        f'<span class="lplan-ic" style="color:{accent}" aria-hidden="true">'
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" '
        f'stroke-linecap="round" stroke-linejoin="round">{_lens_icon_inner(name)}</svg></span>'
    )


def _lens_icon_ca(name: str) -> str:
    """Charter-header form of the canonical lens icon (uses .ca-icon-svg sizing)."""
    return (
        '<svg class="ca-icon-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        'stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
        f'{_lens_icon_inner(name)}</svg>'
    )


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


def _md_block(text: str) -> str:
    """Render a tiny markdown subset to HTML, linkifying S-/C-/X- references."""
    out: list[str] = []
    list_mode = ""
    sub_open = False

    def close_sub():
        nonlocal sub_open
        if sub_open:
            out.append("</ul>")
            sub_open = False

    def close_list():
        nonlocal list_mode
        close_sub()
        if list_mode:
            out.append(f"</{list_mode}>")
            list_mode = ""

    def open_list(mode: str):
        nonlocal list_mode
        if list_mode != mode:
            close_list()
            cls = ' class="clean"' if mode == "ul" else ""
            out.append(f"<{mode}{cls}>")
            list_mode = mode

    lines = str(text).splitlines()
    i = 0
    while i < len(lines):
        raw = lines[i]
        s = raw.strip()
        if not s:
            close_list()
            i += 1
            continue
        if _is_table_row(s):
            table_lines = []
            j = i
            while j < len(lines) and _is_table_row(lines[j].strip()):
                table_lines.append(lines[j].strip())
                j += 1
            table = _table_html(table_lines)
            if table:
                close_list()
                out.append(table)
                i = j
                continue
        if s.startswith("# "):
            close_list()
            # The report section already carries the top-level artifact title.
            i += 1
            continue
        if s.startswith("#"):
            close_list()
            out.append(f"<h4>{_rich_text(s.lstrip('# '))}</h4>")
        elif s.startswith("- ") or s.startswith("* "):
            indent = len(raw) - len(raw.lstrip(" "))
            if indent >= 2:
                if list_mode != "ul":
                    open_list("ul")
                if not sub_open:
                    out.append('<ul class="sub">')
                    sub_open = True
                out.append(f"<li>{_rich_text(s[2:])}</li>")
            else:
                close_sub()
                open_list("ul")
                out.append(f"<li>{_rich_text(s[2:])}</li>")
        elif re.match(r"^\d+\.\s+", s):
            open_list("ol")
            item = re.sub(r"^\d+\.\s+", "", s)
            out.append(f"<li>{_rich_text(item)}</li>")
        else:
            close_list()
            out.append(f'<p class="lead">{_rich_text(s)}</p>')
        i += 1
    close_list()
    return "".join(out)


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


def _claims_table_html(claims, effects_by_claim=None) -> str:
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
            meta_chips.append(f'<span class="claim-chip">⚡ {e(str(c.get("confidence")))}</span>')
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
                "adversarial_check": verification.get("adversarial_check"),
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
        method = ev.get("extraction_method") or ""
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


def _wrap(text: str, width: int, max_lines: int) -> list:
    words = str(text).split()
    if not words:
        return [""]
    lines: list = []
    cur = ""
    for w in words:
        if not cur:
            cur = w
        elif len(cur) + 1 + len(w) <= width:
            cur += " " + w
        else:
            lines.append(cur)
            cur = w
            if len(lines) == max_lines:
                break
    if cur and len(lines) < max_lines:
        lines.append(cur)
    rendered = " ".join(lines)
    if len(rendered) < len(text.strip()):
        lines[-1] = lines[-1][: max(0, width - 1)].rstrip() + "…"
    return lines


def _node_parts(label: str) -> tuple:
    """Split a Mermaid node label into a display description and its ref ids."""
    raw = str(label).replace("<br/>", " ").replace("<br>", " ")
    seen: list = []
    for m in _REF_RE.finditer(raw):
        if m.group(0) not in seen:
            seen.append(m.group(0))
    desc = re.sub(r"\s+", " ", _REF_RE.sub("", raw)).strip(" :,-")
    return desc, seen


def _parse_mmd(mmd: str) -> tuple:
    nodes: dict = {}
    solid: list = []
    dotted: list = []
    for line in str(mmd).splitlines():
        line = line.strip()
        if not line or line.startswith("%%"):
            continue
        for nid, label in _MMD_NODE_RE.findall(line):
            nodes.setdefault(nid, label)
        cleaned = _MMD_NODE_RE.sub(lambda m: m.group(1), line)
        for em in _MMD_EDGE_RE.finditer(cleaned):
            src, arrow, dst = em.group(1), em.group(2), em.group(3)
            nodes.setdefault(src, src)
            nodes.setdefault(dst, dst)
            (dotted if arrow == "-.->" else solid).append((src, dst))
    return nodes, solid, dotted


def _am_node_class(nid: str) -> str:
    head, tail = nid[:1], nid[1:]
    if head == "S" and tail.isdigit():
        return "am-src"
    if head == "X" and tail.isdigit():
        return "am-x"
    if head == "C" and tail.isdigit():
        return "am-claim"
    if nid == "Q":
        return "am-q"
    return ""


_AM_TYPE_CLASS = {
    "source": "am-src", "contradiction": "am-x", "claim": "am-claim",
    "question": "am-q", "option": "am-opt", "action": "am-act", "other": "am-other",
}


def _am_node_type(nid: str) -> str:
    """Semantic node type for filtering/coloring the interactive map."""
    head, tail = nid[:1], nid[1:]
    if head == "S" and tail.isdigit():
        return "source"
    if head == "X" and tail.isdigit():
        return "contradiction"
    if head == "C" and tail.isdigit():
        return "claim"
    if head == "N" and tail.isdigit():
        return "action"
    if nid == "Q":
        return "question"
    if len(nid) == 1 and nid.isalpha():
        return "option"
    return "other"


def _cyto_node_note(ntype: str, ref: str, desc: str,
                    sources_by_id: dict, contra_by_id: dict) -> str:
    """Tooltip text for a node, enriched from report_data.json where available.

    Falls back to the Mermaid label description. Never fabricates content.
    """
    if ntype == "source":
        src = sources_by_id.get(ref)
        if src:
            bits = [str(src.get("title") or "").strip(), str(src.get("note") or "").strip()]
            joined = " — ".join(b for b in bits if b)
            if joined:
                return joined
    elif ntype == "contradiction":
        x = contra_by_id.get(ref)
        if x:
            meta = " · ".join(b for b in (str(x.get("kind") or "").strip(),
                                          str(x.get("status") or "").strip()) if b)
            bits = [str(x.get("stake") or "").strip()]
            if meta:
                bits.append(meta)
            joined = " — ".join(b for b in bits if b)
            if joined:
                return joined
    return desc


def _argument_map_cyto(mmd, data) -> dict:
    """Build Cytoscape.js elements (nodes + edges) from the Mermaid argument map.

    Topology comes from the same `_parse_mmd` used by the static SVG; node tooltips
    are enriched by joining ids against the sources/contradictions already loaded in
    `data`. Returns {"nodes": [], "edges": []} when nothing parses.
    """
    nodes, solid, dotted = _parse_mmd(mmd)
    if not nodes:
        return {"nodes": [], "edges": []}
    sources_by_id = {s.get("id"): s for s in (data or {}).get("sources", []) if isinstance(s, dict)}
    contra_by_id = {x.get("id"): x for x in (data or {}).get("contradictions", []) if isinstance(x, dict)}

    cyto_nodes = []
    for nid, label in nodes.items():
        desc, node_refs = _node_parts(label)
        ref = node_refs[0] if node_refs else ""
        ntype = _am_node_type(nid)
        cyto_nodes.append({
            "data": {
                "id": nid,
                "label": desc or nid,
                "ref": ref,
                "ntype": ntype,
                "note": _cyto_node_note(ntype, ref, desc, sources_by_id, contra_by_id),
            },
            "classes": _AM_TYPE_CLASS.get(ntype, "am-other"),
        })

    cyto_edges = []
    for i, (s, d) in enumerate(solid):
        cyto_edges.append({"data": {"id": f"e{i}", "source": s, "target": d}})
    for j, (s, d) in enumerate(dotted):
        cyto_edges.append({"data": {"id": f"d{j}", "source": s, "target": d}, "classes": "dotted"})

    return {"nodes": cyto_nodes, "edges": cyto_edges}


def _svg_ref(ref: str, x: float, y: float) -> str:
    label = f'<text class="am-ref" x="{x:.1f}" y="{y:.1f}">{e(ref)}</text>'
    if ref.startswith("C-") or ref in _ANCHORS:
        return f'<a href="#ref-{e(ref)}">{label}</a>'
    return f'<text class="am-ref am-ref-plain" x="{x:.1f}" y="{y:.1f}">{e(ref)}</text>'


def _am_edge_path(pos, src, dst, layer, w, h, vgap, dotted) -> str:
    sx, sy = pos[src]
    dx, dy = pos[dst]
    x1, x2 = sx + w / 2, dx + w / 2
    cls = "am-edge am-dotted" if dotted else "am-edge"
    if layer.get(src) == layer.get(dst):
        y1, y2 = sy + h, dy + h
        mid = max(sy, dy) + h + vgap * 0.45
        d = f"M{x1:.1f},{y1:.1f} C{x1:.1f},{mid:.1f} {x2:.1f},{mid:.1f} {x2:.1f},{y2:.1f}"
    elif layer.get(dst, 0) < layer.get(src, 0):
        d = f"M{x1:.1f},{sy:.1f} L{x2:.1f},{dy + h:.1f}"
    else:
        d = f"M{x1:.1f},{sy + h:.1f} L{x2:.1f},{dy:.1f}"
    return f'<path class="{cls}" d="{d}" marker-end="url(#am-arrow)" />'


def _argument_map_svg(mmd) -> str:
    """Parse the minimal Mermaid argument map and render it as an inline,
    self-contained SVG (no mermaid.js, no network). Degrades to '' on no nodes."""
    if not mmd or not str(mmd).strip():
        return ""
    nodes, solid, dotted = _parse_mmd(mmd)
    if not nodes:
        return ""
    # Longest-path layering over solid edges only (dotted = secondary links).
    layer = {nid: 0 for nid in nodes}
    for _ in range(len(nodes)):
        changed = False
        for src, dst in solid:
            if layer.get(dst, 0) < layer.get(src, 0) + 1:
                layer[dst] = layer.get(src, 0) + 1
                changed = True
        if not changed:
            break
    order = list(nodes.keys())
    max_layer = max(layer.values()) if layer else 0
    layers = [[nid for nid in order if layer[nid] == lvl] for lvl in range(max_layer + 1)]
    layers = [lst for lst in layers if lst]

    parts = {nid: _node_parts(nodes[nid]) for nid in nodes}
    wrapped = {nid: _wrap(parts[nid][0], 24, 3) for nid in nodes}
    max_lines = max((len(wrapped[nid]) for nid in nodes), default=1)
    any_refs = any(parts[nid][1] for nid in nodes)

    w, pad, lh = 184.0, 11.0, 14.0
    h = pad + max_lines * lh + (16.0 if any_refs else 0.0) + 9.0
    hgap, vgap, mtop, mside = 26.0, 50.0, 18.0, 18.0
    widths = [len(lst) * w + max(0, len(lst) - 1) * hgap for lst in layers]
    svg_w = (max(widths) if widths else w) + 2 * mside
    svg_h = 2 * mtop + len(layers) * h + max(0, len(layers) - 1) * vgap

    pos: dict = {}
    for li, lst in enumerate(layers):
        startx = (svg_w - widths[li]) / 2.0
        y = mtop + li * (h + vgap)
        for i, nid in enumerate(lst):
            pos[nid] = (startx + i * (w + hgap), y)

    edges = "".join(
        _am_edge_path(pos, s, d, layer, w, h, vgap, dot)
        for grp, dot in ((solid, False), (dotted, True))
        for s, d in grp if s in pos and d in pos
    )

    # Per-node clip paths so text is always contained within the box.
    clip_defs = ""
    for nid in nodes:
        if nid not in pos:
            continue
        nx, ny = pos[nid]
        safe = re.sub(r"[^a-zA-Z0-9]", "_", nid)
        clip_defs += (f'<clipPath id="amc-{safe}">'
                      f'<rect x="{nx + 2:.1f}" y="{ny + 2:.1f}" '
                      f'width="{w - 4:.1f}" height="{h - 4:.1f}" /></clipPath>')

    node_svg = ""
    for nid in nodes:
        if nid not in pos:
            continue
        x, y = pos[nid]
        safe = re.sub(r"[^a-zA-Z0-9]", "_", nid)
        tspans = ""
        ty = y + pad + 10
        for ln in wrapped[nid]:
            tspans += f'<tspan x="{x + 12:.1f}" y="{ty:.1f}">{e(ln)}</tspan>'
            ty += lh
        ref_svg = ""
        rx = x + 12
        for r in parts[nid][1][:5]:
            ref_svg += _svg_ref(r, rx, y + h - 11)
            rx += (len(r) + 1) * 7.0
            if rx > x + w - 20:
                break
        node_svg += (f'<g><rect class="am-node {_am_node_class(nid)}" x="{x:.1f}" y="{y:.1f}" '
                     f'width="{w:.1f}" height="{h:.1f}" rx="9" ry="9" />'
                     f'<g clip-path="url(#amc-{safe})">'
                     f'<text class="am-desc">{tspans}</text>{ref_svg}</g></g>')

    legend = "Solid arrows flow toward conclusions"
    if dotted:
        legend += "; dashed arrows mark counter-claims"
    legend += ". Reference chips link to the matching claim, source, and contradiction entries."
    return (
        '<div class="argmap-wrap">'
        f'<svg class="argmap" viewBox="0 0 {svg_w:.0f} {svg_h:.0f}" width="{svg_w:.0f}" '
        f'height="{svg_h:.0f}" role="img" aria-label="Argument map of the council decision">'
        '<defs><marker id="am-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" '
        'markerHeight="7" orient="auto-start-reverse">'
        f'<path d="M0,0 L10,5 L0,10 z" fill="#9aa0ab" /></marker>{clip_defs}</defs>'
        f"{edges}{node_svg}</svg></div>"
        f'<p class="am-cap">{e(legend)}</p>'
    )


_AM_FILTER_LABELS = [
    ("question", "Question"), ("option", "Options"), ("claim", "Claims"),
    ("source", "Sources"), ("contradiction", "Contradictions"),
    ("action", "Next actions"), ("other", "Other"),
]

# Vanilla init for the inline Cytoscape graph. No Python interpolation here — the
# graph data is read from the sibling <script type="application/json"> block, so
# every {..} below is literal JS.
_AM_CY_INIT_JS = """
(function () {
  if (typeof cytoscape === 'undefined') return;
  var dataEl = document.getElementById('am-cy-data');
  var container = document.getElementById('am-cy');
  if (!dataEl || !container) return;
  var elements;
  try { elements = JSON.parse(dataEl.textContent); } catch (e) { return; }
  if (!elements || !elements.nodes || !elements.nodes.length) return;

  var staticEl = document.querySelector('.am-static');
  if (staticEl) staticEl.style.display = 'none';
  container.style.display = 'block';

  var layouts = {
    flow: { name: 'breadthfirst', directed: true, padding: 14, spacingFactor: 1.05, avoidOverlap: true },
    network: { name: 'cose', padding: 14, animate: false, randomize: true, nodeRepulsion: 9000,
               idealEdgeLength: 75, nodeOverlap: 14, gravity: 0.35, componentSpacing: 70 }
  };
  var activeLayout = 'flow';
  function runLayout() { cy.layout(layouts[activeLayout]).run(); }
  var cy = cytoscape({
    container: container,
    elements: elements,
    wheelSensitivity: 0.2,
    style: [
      { selector: 'node', style: {
          'label': 'data(label)', 'text-wrap': 'wrap', 'text-max-width': '120px',
          'font-size': '9px', 'font-family': '-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,sans-serif',
          'text-valign': 'center', 'text-halign': 'center', 'color': '#15161a',
          'background-color': '#ffffff', 'border-color': '#cfd3da', 'border-width': 1.2,
          'shape': 'round-rectangle', 'width': 'label', 'height': 'label',
          'padding': '8px' } },
      { selector: 'node.am-q', style: { 'background-color': '#efecfb', 'border-color': '#5b46c8', 'font-weight': 'bold' } },
      { selector: 'node.am-opt', style: { 'background-color': '#efecfb', 'border-color': '#5b46c8', 'font-weight': 'bold' } },
      { selector: 'node.am-src', style: { 'background-color': '#eef6f1', 'border-color': '#9bd9b8' } },
      { selector: 'node.am-x', style: { 'background-color': '#fdf6e3', 'border-color': '#eccb74' } },
      { selector: 'node.am-act', style: { 'background-color': '#e7f6ee', 'border-color': '#9bd9b8' } },
      { selector: 'node.am-other', style: { 'background-color': '#f4f5f7', 'border-color': '#e7e8ec' } },
      { selector: 'edge', style: {
          'width': 1.4, 'line-color': '#b9bdc7', 'target-arrow-color': '#9aa0ab',
          'target-arrow-shape': 'triangle', 'arrow-scale': 0.9, 'curve-style': 'bezier' } },
      { selector: 'edge.dotted', style: { 'line-style': 'dashed', 'line-color': '#cdb47a', 'target-arrow-color': '#cdb47a' } },
      { selector: '.am-dim', style: { 'opacity': 0.12 } },
      { selector: 'node.am-focus', style: { 'border-width': 3, 'border-color': '#5b46c8' } }
    ],
    layout: layouts.flow
  });

  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"]/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c];
    });
  }
  var box = document.getElementById('am-details');
  function showDetails(d) {
    if (!box) return;
    var ref = d.ref ? ' <span class="am-d-ref">' + esc(d.ref) + '</span>' : '';
    var jump = d.ref ? '<a class="am-jump" href="#ref-' + esc(d.ref) + '">Open in report \\u2193</a>' : '';
    box.innerHTML = '<div class="am-d-head"><b>' + esc(d.label) + '</b>' + ref + '</div>' +
      (d.note ? '<p class="am-d-note">' + esc(d.note) + '</p>' : '') + jump;
    box.style.display = 'block';
  }
  function hideDetails() { if (box) box.style.display = 'none'; }

  cy.on('tap', 'node', function (evt) {
    var n = evt.target;
    cy.elements().addClass('am-dim').removeClass('am-focus');
    n.closedNeighborhood().removeClass('am-dim');
    n.addClass('am-focus');
    showDetails(n.data());
  });
  cy.on('tap', function (evt) {
    if (evt.target === cy) { cy.elements().removeClass('am-dim am-focus'); hideDetails(); }
  });

  var toggles = document.querySelectorAll('.am-filter input[data-type]');
  Array.prototype.forEach.call(toggles, function (cb) {
    cb.addEventListener('change', function () {
      var t = cb.getAttribute('data-type');
      cy.nodes('[ntype = "' + t + '"]').style('display', cb.checked ? 'element' : 'none');
      runLayout();
    });
  });

  var lybtns = document.querySelectorAll('.am-layout button[data-layout]');
  Array.prototype.forEach.call(lybtns, function (btn) {
    btn.addEventListener('click', function () {
      activeLayout = btn.getAttribute('data-layout');
      Array.prototype.forEach.call(lybtns, function (b) { b.classList.toggle('is-active', b === btn); });
      runLayout();
      cy.fit(undefined, 20);
    });
  });
})();
"""


def _argument_map_interactive_html(mmd, data) -> str:
    """Interactive Cytoscape argument map with a static-SVG print/no-JS fallback.

    Returns '' when nothing parses. When the vendored library is absent, returns
    just the static SVG so the report still shows the map.
    """
    static_svg = _argument_map_svg(mmd)
    if not static_svg:
        return ""
    lib = _cytoscape_js()
    if not lib:
        return static_svg

    elements = _argument_map_cyto(mmd, data)
    present = {n["data"]["ntype"] for n in elements["nodes"]}
    toggles = "".join(
        f'<label class="am-toggle"><input type="checkbox" data-type="{e(t)}" checked> {e(lbl)}</label>'
        for t, lbl in _AM_FILTER_LABELS if t in present
    )
    # JSON sits inside a <script> block — neutralise any "</script>" in the data.
    elements_json = json.dumps(elements, ensure_ascii=False).replace("</", "<\\/")

    return (
        '<div class="argmap-interactive">'
        '<div class="am-toolbar">'
        f'<div class="am-filter">{toggles}</div>'
        '<div class="am-layout" role="group" aria-label="Map layout">'
        '<button type="button" class="am-lybtn is-active" data-layout="flow">Flow</button>'
        '<button type="button" class="am-lybtn" data-layout="network">Network</button>'
        '</div>'
        '<span class="am-hint">Tap a node to focus · drag to pan · scroll to zoom</span>'
        '</div>'
        '<div class="am-cy" id="am-cy"></div>'
        '<div class="am-details" id="am-details" style="display:none"></div>'
        f'<div class="am-static">{static_svg}</div>'
        f'<script type="application/json" id="am-cy-data">{elements_json}</script>'
        f'<script>{lib}</script>'
        f'<script>{_AM_CY_INIT_JS}</script>'
        '</div>'
    )


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
            'strength of belief in that claim &mdash; e.g. <code>0.88</code> means the lens is fairly but not '
            'fully certain. It is intentionally <b>separate from the Status column</b>: a high-confidence forecast '
            'is still a forecast, not evidence. As a rule of thumb, the Stage 6 adversarial review flags '
            'confidence ≥ 0.8 on any claim whose status is not <code>supported</code> as possible '
            'overconfidence &mdash; worth a second look.</p></div></div>'
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
            identity = _source_identity_badges(s)
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
            "full_text_status", "publisher", "publication_date", "accessed_at",
            "credibility_notes", "relevance_notes",
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


if __name__ == "__main__":
    raise SystemExit(main())
