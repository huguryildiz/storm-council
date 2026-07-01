#!/usr/bin/env python3
"""Render a Storm Council decision-brief report (JSON -> single HTML).

Pure standard library. No network, no LLM, no API key. The reasoning is done by
the skill (Claude); this script only fixes the *format* so every report looks
identical. Honesty: the status banner reflects whatever the input says -- render
a "verified" state only if verification actually happened.

This module is the public facade for the ``report`` renderer package
(``report/components`` primitives, ``report/layers`` section builders,
``report/styles.css``). It re-exports the full API so existing callers and tests
keep importing ``render_report`` unchanged; ``build()``/``main()``/the CLI and the
``LENS_ICONS`` single-source invariant live in the package.

Usage:
    python3 render_report.py report_data.json -o storm_council_report.html
"""

from __future__ import annotations

import os
import sys

# Loaded standalone (spec_from_file_location) or run as a script: make the sibling
# ``report`` package importable by putting this file's directory on sys.path.
_PKG_DIR = os.path.dirname(os.path.abspath(__file__))
if _PKG_DIR not in sys.path:
    sys.path.insert(0, _PKG_DIR)

from report.components.base import (
    _REF_RE,
    e,
    _ANCHORS,
    _EMITTED_CLAIM_TARGETS,
    _ref_chip,
    text_refs,
    refs,
    _detail_value,
    _field_details,
    _rich_text,
    _fmt_datetime_html,
    _is_table_row,
    _is_table_separator,
    _table_cells,
    _table_html,
    _md_block,
)
from report.components.bib import (
    _BIB_FIELD_RE,
    _bib_normalize_id,
    _parse_bibtex,
    _bib_initials,
    _bib_author_apa,
    _format_apa_html,
)
from report.components.icons import (
    _logo_svg,
    _cytoscape_js,
    _LENS_DOT,
    LENS_ICONS,
    LENS_ICON_FALLBACK,
    _lens_icon_inner,
    _lens_icon_svg,
    _lens_icon_ca,
)
from report.components.badges import (
    _STRENGTH,
    _CONFLICT,
    _EVIDENCE_TAG,
    _MOVE_TAG,
    _SOURCE_CLASS_LABELS,
    _locator_text,
    _evidence_source_badges,
    _source_identity_badges,
    _source_class_badges,
    _verdicts_by_evidence,
    _verdict_badge_html,
    _evidence_verdicts_html,
)
from report.layers.lenses import (
    _clamped_score,
    _radar_point,
    _fmt_points,
    _lens_snapshot_html,
    _evidence_plan_html,
    _lens_plans_html,
    _lens_charters_html,
)
from report.layers.deliberation import (
    _round_label,
    _move_effect_html,
    _claim_effects_from_deliberation,
    _run_manifest_html,
    _deliberation_html,
    _cx_detail_html,
)
from report.layers.evidence import (
    _evidence_table_html,
)
from report.layers.claims import (
    _claims_table_html,
)
from report.layers.argument_map import (
    _MMD_NODE_RE,
    _MMD_EDGE_RE,
    _wrap,
    _node_parts,
    _parse_mmd,
    _am_node_class,
    _AM_TYPE_CLASS,
    _am_node_type,
    _cyto_node_note,
    _argument_map_cyto,
    _svg_ref,
    _am_edge_path,
    _argument_map_svg,
    _AM_FILTER_LABELS,
    _AM_CY_INIT_JS,
    _argument_map_interactive_html as _am_interactive_impl,
)
from report.layers.document import (
    CSS,
    _STATUS_CLASS,
    _LAYERS,
    _layer_visible,
    _provenance_html,
    _refresh_diff_html,
    build,
    _enrich_source_urls,
    _read_jsonl,
    _fold_in_artifacts,
    main,
)

__all__ = [
    "_REF_RE",
    "e",
    "_ANCHORS",
    "_EMITTED_CLAIM_TARGETS",
    "_ref_chip",
    "text_refs",
    "refs",
    "_detail_value",
    "_field_details",
    "_rich_text",
    "_fmt_datetime_html",
    "_is_table_row",
    "_is_table_separator",
    "_table_cells",
    "_table_html",
    "_md_block",
    "_BIB_FIELD_RE",
    "_bib_normalize_id",
    "_parse_bibtex",
    "_bib_initials",
    "_bib_author_apa",
    "_format_apa_html",
    "_logo_svg",
    "_cytoscape_js",
    "_LENS_DOT",
    "LENS_ICONS",
    "LENS_ICON_FALLBACK",
    "_lens_icon_inner",
    "_lens_icon_svg",
    "_lens_icon_ca",
    "_STRENGTH",
    "_CONFLICT",
    "_EVIDENCE_TAG",
    "_MOVE_TAG",
    "_SOURCE_CLASS_LABELS",
    "_locator_text",
    "_evidence_source_badges",
    "_source_identity_badges",
    "_source_class_badges",
    "_verdicts_by_evidence",
    "_verdict_badge_html",
    "_evidence_verdicts_html",
    "_clamped_score",
    "_radar_point",
    "_fmt_points",
    "_lens_snapshot_html",
    "_evidence_plan_html",
    "_lens_plans_html",
    "_lens_charters_html",
    "_round_label",
    "_move_effect_html",
    "_claim_effects_from_deliberation",
    "_run_manifest_html",
    "_deliberation_html",
    "_cx_detail_html",
    "_evidence_table_html",
    "_claims_table_html",
    "_MMD_NODE_RE",
    "_MMD_EDGE_RE",
    "_wrap",
    "_node_parts",
    "_parse_mmd",
    "_am_node_class",
    "_AM_TYPE_CLASS",
    "_am_node_type",
    "_cyto_node_note",
    "_argument_map_cyto",
    "_svg_ref",
    "_am_edge_path",
    "_argument_map_svg",
    "_AM_FILTER_LABELS",
    "_AM_CY_INIT_JS",
    "_argument_map_interactive_html",
    "CSS",
    "_STATUS_CLASS",
    "_LAYERS",
    "_layer_visible",
    "_provenance_html",
    "_refresh_diff_html",
    "build",
    "_enrich_source_urls",
    "_read_jsonl",
    "_fold_in_artifacts",
    "main",
]


def _argument_map_interactive_html(mmd, data):
    """Facade wrapper over the package implementation.

    Injects this module's ``_cytoscape_js`` so tests that monkeypatch
    ``render_report._cytoscape_js`` still control the vendored-library gate
    (interactive canvas vs. static-SVG fallback). Output is identical to the
    package function when ``_cytoscape_js`` is unpatched.
    """
    return _am_interactive_impl(mmd, data, cytoscape_js=_cytoscape_js)


if __name__ == "__main__":
    raise SystemExit(main())
