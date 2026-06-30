# Interactive Knowledge Map — Design

**Date:** 2026-06-30
**Status:** Approved (pending user spec review)
**Touches:** `scripts/render_report.py`, `assets/vendor/cytoscape.min.js` (new), `tests/test_render_report.py`

## Problem

The HTML report already renders the council's argument map, but only as a **static, hand-laid-out SVG** (`_argument_map_svg()` in `scripts/render_report.py`). Readers cannot pan, zoom, focus a node's neighborhood, or filter by node type. For a contradiction-aware research brief whose whole value is the *structure* of claims → sources → contradictions → options, a static picture undersells the map.

Goal: make the existing argument map **interactive** in the browser, without breaking the report's self-contained / no-network / print-friendly guarantees.

## Non-goals

- No change to the upstream generator (`generate_artifacts.py`) or the skill prompts. The graph is built from artifacts that already exist.
- No new report section. We upgrade the existing "Argument map" section in place.
- No CDN, no pip, no runtime network. (Hard project rule.)
- No new graph semantics — same nodes/edges the `.mmd` already encodes.

## Approach: progressive enhancement

Keep the static SVG as the **print / no-JS fallback**; layer an interactive Cytoscape.js graph on top when JavaScript is available.

```
05_argument_map.mmd  ──_parse_mmd()──▶ nodes / solid / dotted
                                          │
report_data.json     ──join (tooltips)──┤
                                          ├──▶ _argument_map_svg()   → static SVG  (print / <noscript>)
                                          └──▶ _argument_map_cyto()  → elements JSON → inline Cytoscape.js
```

- **Browser with JS:** Cytoscape graph shown; static SVG hidden (`.am-static` set to `display:none` by the init script once Cytoscape mounts).
- **Print / PDF:** `@media print` keeps the static SVG, hides the interactive canvas.
- **JS disabled:** static SVG remains visible (it is the default; JS hides it only on success).

This guarantees no regression to the current printable report.

## Data source

Reuse `_parse_mmd()` (already returns `nodes, solid, dotted`). A new `_argument_map_cyto(mmd, data)` builds Cytoscape `elements` JSON:

- **Nodes:** `{ data: { id, label, type }, classes }` where `type`/`classes` come from the existing `_am_node_class()` prefix logic (`am-src` / `am-x` / `am-q` / `am-claim` / option / next-action).
- **Edges:** `{ data: { source, target }, classes: 'dotted'? }` from `solid` / `dotted`.
- **Tooltip enrichment:** join node ids against `report_data.json` already loaded in `build()`:
  - `S-###` → `sources[].title` + `note`
  - `X-###` → `contradictions[].stake` + `kind` + `status`
  - `C-###` → `strongest_findings` / claims text when present (best-effort; falls back to the `.mmd` label)
  - option / next-action nodes → their `.mmd` label
- Missing enrichment degrades gracefully to the `.mmd` label. Never fabricate.

The elements JSON is embedded in the page as a `<script type="application/json">` block (not interpolated into JS string literals — avoids escaping bugs).

## Vendored library

- `assets/vendor/cytoscape.min.js` (MIT, ~400 KB), committed once. Build-time vendoring; **no runtime network**.
- Inlined into the HTML the same way `_logo_svg()` reads `assets/icon.svg` — read the file, wrap in `<script>…</script>`. If the asset is missing, skip the interactive layer and keep the static SVG (graceful, logged to stderr).
- Layout: Cytoscape's **built-in `breadthfirst`** layout (DAG-friendly). No `dagre`/extra plugin — keeps it a single inlined file.

## Interactions

- Pan / zoom (built-in).
- **Tap a node** → highlight its closed neighborhood (incomers + outgoers), dim the rest; show a small details panel (id, label, enriched note).
- **Filter toggles** (claim / source / contradiction / option / next-action) → show/hide node classes, re-run layout.
- **Reference chips / details panel ids** link to the existing `#ref-…` anchors in the report (reuse current anchor scheme) so clicking a node can scroll to its claim/source/contradiction row.
- Tap empty canvas → reset highlight.

Node coloring reuses the existing CSS custom properties / `.am-*` palette so the interactive graph matches the report's visual language.

## File-by-file changes

1. **`scripts/render_report.py`**
   - Add `_argument_map_cyto(mmd, data) -> dict` (elements builder, pure data).
   - Add `_argument_map_interactive_html(mmd, data) -> str` — emits: container `<div>`, embedded elements JSON, filter UI, details panel, the static SVG wrapped in `.am-static`, and the init `<script>`.
   - Add `_cytoscape_js() -> str` reading `assets/vendor/cytoscape.min.js` (mirror of `_logo_svg()`); returns `""` if absent.
   - In `build()` (~line 1473): if the vendored lib is present, render the interactive block; else fall back to the current static `_argument_map_svg()` call. Keep the section title "Argument map".
   - Add CSS (`.am-static`, `.am-cy`, filter chips, details panel, `@media print` rules) to the `CSS` string.

2. **`assets/vendor/cytoscape.min.js`** — new vendored file (download once, commit).

3. **`tests/test_render_report.py`**
   - `_argument_map_cyto()` produces well-formed elements (node count = parsed nodes, edge count = solid+dotted, classes match `_am_node_class`).
   - Interactive HTML contains the embedded JSON, the filter UI, AND the static SVG fallback (`.am-static`).
   - When the vendored asset is absent, output falls back to the static SVG and contains no Cytoscape init.

4. **Regenerate the live report**
   `python3 scripts/render_report.py out/network_flow_rl_live/report_data.json -o out/network_flow_rl_live/storm_council_report.html`

## Verification / success criteria

- `python3 -m pytest tests/test_render_report.py` passes (old + new tests).
- Regenerated `storm_council_report.html` opens in a browser with a pan/zoom/filter/clickable graph.
- Print preview (or JS disabled) still shows the static SVG map — no regression.
- No network request is made when opening the HTML (verify: works offline / file://).
- Report size increase is bounded (~+400 KB from the inlined library).

## Risks / mitigations

- **`.mmd` format drift** → parsing already exists and is reused; no new parsing surface.
- **Library size** → acceptable for a self-contained artifact; documented in the spec.
- **Asset missing on a fresh checkout** → graceful fallback to static SVG; nothing crashes.
- **Print regression** → explicitly prevented by keeping the static SVG and `@media print` rules.
