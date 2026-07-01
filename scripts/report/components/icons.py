"""Brand/lens icons. LENS_ICONS is the single source of truth for the five lens icons."""

from __future__ import annotations

from pathlib import Path


def _logo_svg() -> str:
    icon = Path(__file__).resolve().parents[3] / "assets" / "icon.svg"
    try:
        return icon.read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def _cytoscape_js() -> str:
    """Read the vendored Cytoscape.js library for inline embedding (no network).

    Returns '' if the asset is absent, so the report degrades to the static SVG.
    """
    lib = Path(__file__).resolve().parents[3] / "assets" / "vendor" / "cytoscape.min.js"
    try:
        return lib.read_text(encoding="utf-8")
    except OSError:
        return ""


_LENS_DOT = {
    "practitioner": "var(--green)",
    "academic": "var(--brand)",
    "skeptic": "var(--red)",
    "economist": "var(--amber)",
    "historian": "var(--faint)",
}


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
