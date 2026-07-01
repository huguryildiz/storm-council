"""Foundational render primitives: HTML escaping, reference chips, detail/rich text, tables."""

from __future__ import annotations

import html
import re


_REF_RE = re.compile(r"\b[CSXE]-\d{3}\b")


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


def _fmt_datetime_html(val: str) -> str:
    """Wrap ISO datetime strings in a <time> element for JS local-time conversion."""
    s = str(val).strip()
    if re.search(r'[T ]\d{2}:\d{2}', s):
        return f'<time class="ts-local" data-ts="{html.escape(s)}">{html.escape(s)}</time>'
    return html.escape(s)


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
