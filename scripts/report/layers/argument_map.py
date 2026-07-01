"""Argument map: Mermaid parse, static SVG, and interactive Cytoscape view."""

from __future__ import annotations

import re
import json

from report.components.base import _ANCHORS, _REF_RE, e
from report.components.icons import _cytoscape_js


_MMD_NODE_RE = re.compile(
    r'([A-Za-z0-9_]+)\s*(?:\[\[|\{\{|\(\[|\[|\(|\{)\s*"(.*?)"\s*(?:\]\]|\}\}|\]\)|\]|\)|\})'
)


_MMD_EDGE_RE = re.compile(
    r'([A-Za-z0-9_]+)\s*(-\.->|-->)\s*(?:\|[^|]*\|\s*)?([A-Za-z0-9_]+)'
)


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


def _pivotal_refs(data) -> set:
    """The set of C-###/X-### refs that 07c ranked `pivotal`, read from
    data["decision_criticality"]["rankings"]. Empty when the artifact is absent —
    so an un-adopting bundle gets an identical argument map (no am-pivotal class)."""
    dc = (data or {}).get("decision_criticality")
    if not isinstance(dc, dict):
        return set()
    out = set()
    for r in dc.get("rankings") or []:
        if isinstance(r, dict) and str(r.get("criticality") or "").lower() == "pivotal":
            rid = r.get("claim_id") or r.get("contradiction_id")
            if rid:
                out.add(rid)
    return out


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
    pivotal = _pivotal_refs(data)

    cyto_nodes = []
    for nid, label in nodes.items():
        desc, node_refs = _node_parts(label)
        ref = node_refs[0] if node_refs else ""
        ntype = _am_node_type(nid)
        # 07c: a pivotal node gets an orthogonal visual channel (thicker, distinctly
        # coloured border in the stylesheet) — space-joined onto its type class.
        classes = _AM_TYPE_CLASS.get(ntype, "am-other")
        if any(r in pivotal for r in node_refs):
            classes += " am-pivotal"
        cyto_nodes.append({
            "data": {
                "id": nid,
                "label": desc or nid,
                "ref": ref,
                "ntype": ntype,
                "note": _cyto_node_note(ntype, ref, desc, sources_by_id, contra_by_id),
            },
            "classes": classes,
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


def _argument_map_svg(mmd, pivotal_refs=None) -> str:
    """Parse the minimal Mermaid argument map and render it as an inline,
    self-contained SVG (no mermaid.js, no network). Degrades to '' on no nodes.

    ``pivotal_refs`` (07c) is the set of C-###/X-### refs to mark with an extra
    ``am-pivotal`` class in the print/no-JS fallback; empty/None ⇒ no marking, so
    a bundle without decision_criticality.json renders an identical SVG."""
    if not mmd or not str(mmd).strip():
        return ""
    pivotal_refs = pivotal_refs or set()
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
        node_cls = _am_node_class(nid)
        if any(r in pivotal_refs for r in parts[nid][1]):
            node_cls = (node_cls + " am-pivotal").strip()
        node_svg += (f'<g><rect class="am-node {node_cls}" x="{x:.1f}" y="{y:.1f}" '
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
      { selector: 'node.am-focus', style: { 'border-width': 3, 'border-color': '#5b46c8' } },
      { selector: 'node.am-pivotal', style: { 'border-width': 3, 'border-color': '#c0392b' } }
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


def _argument_map_interactive_html(mmd, data, cytoscape_js=None) -> str:
    """Interactive Cytoscape argument map with a static-SVG print/no-JS fallback.

    Returns '' when nothing parses. When the vendored library is absent, returns
    just the static SVG so the report still shows the map. ``cytoscape_js`` lets
    the render_report facade inject its own (test-monkeypatchable) library getter;
    it defaults to the vendored reader.
    """
    static_svg = _argument_map_svg(mmd, _pivotal_refs(data))
    if not static_svg:
        return ""
    lib = (cytoscape_js or _cytoscape_js)()
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
