"""BibTeX parsing and APA-7 citation HTML."""

from __future__ import annotations

import html
import re


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
