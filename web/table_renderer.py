"""
Pure-Python table parser + HTML renderer for economics comparison tables.
No AI, no internet, no external packages — works offline permanently.

Parses the `diagram_description` text (written by Claude during answer generation)
into structured data, then renders it as a styled dark-theme HTML table.

Handles 4 description formats found in the IES DB:
  Format A — "Columns: [A | B | C] / Rows: / 1. val | val | val"  (most common ~65%)
  Format B — "Column headers: 'A', 'B' / Row 1 — label: val; val" (narrative ~15%)
  Format C — "Row headers (X): ... / Column 1 (Y): ..." (inverted layout ~5%)
  Format D — Already-formatted ASCII table (payoff matrix, etc.) (~10%)
  Fallback — render as styled pre-formatted text
"""
import re


# ── HTML render helpers ────────────────────────────────────────────────────────

def _html_table(title, headers, rows, footer=None, highlight_col0=True):
    """Build a styled dark-theme HTML table from structured data."""

    def _esc(s):
        return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    header_cells = "".join(
        f'<th style="padding:10px 14px;color:#E8EAED;font-weight:700;'
        f'text-align:left;background:#2d2f31;border-bottom:2px solid rgba(138,180,248,0.5)">'
        f'{_esc(h)}</th>'
        for h in headers
    )

    body_rows = ""
    for i, row in enumerate(rows):
        bg = "rgba(255,255,255,0.03)" if i % 2 == 0 else "transparent"
        cells = ""
        for j, cell in enumerate(row):
            if j == 0 and highlight_col0 and len(headers) >= 2:
                # First column = dimension label — highlighted blue
                cells += (
                    f'<td style="padding:9px 14px;background:#1e2022;color:#8AB4F8;'
                    f'font-weight:600;font-size:0.87rem;border-right:1px solid rgba(138,180,248,0.2)">'
                    f'{_esc(cell)}</td>'
                )
            else:
                cells += (
                    f'<td style="padding:9px 14px;color:#C9CACE;font-size:0.87rem;'
                    f'background:{bg}">{_esc(cell)}</td>'
                )
        body_rows += f"<tr>{cells}</tr>"

    footer_html = ""
    if footer:
        footer_html = (
            f'<tfoot><tr><td colspan="{len(headers)}" style="padding:10px 14px;'
            f'color:#9AA0A6;font-style:italic;font-size:0.82rem;'
            f'border-top:1px solid rgba(255,255,255,0.1)">{_esc(footer)}</td></tr></tfoot>'
        )

    title_html = ""
    if title:
        title_html = (
            f'<div style="font-size:0.82rem;font-weight:600;color:#8AB4F8;'
            f'margin-bottom:8px;text-transform:uppercase;letter-spacing:0.04em">'
            f'{_esc(title)}</div>'
        )

    return (
        f'{title_html}'
        f'<div style="overflow-x:auto;border-radius:8px;'
        f'border:1px solid rgba(255,255,255,0.1);margin:4px 0 12px">'
        f'<table style="width:100%;border-collapse:collapse;background:transparent">'
        f'<thead><tr>{header_cells}</tr></thead>'
        f'<tbody>{body_rows}</tbody>'
        f'{footer_html}'
        f'</table></div>'
    )


def _html_preformatted(desc, title=None):
    """Fallback: display description as styled preformatted text."""
    title_html = (
        f'<div style="font-size:0.82rem;font-weight:600;color:#FDD663;'
        f'margin-bottom:6px">{title}</div>' if title else ""
    )
    return (
        f'{title_html}'
        f'<div style="background:#1a1a1a;border:1px solid rgba(255,255,255,0.08);'
        f'border-radius:8px;padding:14px 16px;overflow-x:auto">'
        f'<pre style="color:#C9CACE;font-size:0.82rem;margin:0;'
        f'white-space:pre-wrap;word-break:break-word">'
        f'{desc.strip()}</pre></div>'
    )


# ── Parser helpers ─────────────────────────────────────────────────────────────

def _split_pipes(s):
    """Split on ' | ' or '|', strip whitespace from each part."""
    parts = re.split(r'\s*\|\s*', s.strip())
    return [p.strip() for p in parts if p.strip()]


def _split_arrows(s):
    """Split 'Name → val1 | val2' into [Name, val1, val2]."""
    if '→' in s:
        left, rest = s.split('→', 1)
        return [left.strip()] + _split_pipes(rest)
    return _split_pipes(s)


def _extract_footer(text):
    """Pull out a trailing footer line (Key insight, Note, etc.)."""
    footer_patterns = [
        r'Key (?:insight|analytical point|note).*?:\s*["\']?(.+)',
        r'(?:Note|Interpretation|Relationship Note):\s*(.+)',
        r'Key Points?:\s*(.+)',
    ]
    for pat in footer_patterns:
        m = re.search(pat, text, re.IGNORECASE | re.DOTALL)
        if m:
            footer = m.group(1).strip().strip("'\"")
            # Truncate very long footers to first 300 chars
            return footer[:300] + ("…" if len(footer) > 300 else "")
    return None


def _extract_title(text):
    """First non-empty line that looks like a title (before 'Columns:' or 'Row')."""
    for line in text.strip().split('\n'):
        line = line.strip()
        if not line:
            continue
        lower = line.lower()
        if any(k in lower for k in ('column', 'row', 'table has', 'structure:')):
            break
        # Skip lines that are purely markdown/bullets
        if re.match(r'^[-•*]', line):
            continue
        if len(line) > 5:
            # Strip leading "Comparative Table —" or "TABLE TITLE:" prefixes
            line = re.sub(r'^(?:comparative|comparison|classification|summary)\s+table[\s—:-]*',
                          '', line, flags=re.IGNORECASE).strip()
            line = re.sub(r'^TABLE TITLE:\s*', '', line, flags=re.IGNORECASE).strip()
            if line:
                return line
    return None


# ── Format A: "Columns: [A | B | C]\nRows:\n1. X | Y | Z" ─────────────────────

def _parse_format_a(text):
    """Most common format: Columns block + numbered rows with pipe separators.
    Handles: '1. X | Y', 'Row 1: X | Y', 'Row 1 (Label): X | Y', '1. X → Y | Z'
    """
    # ── Extract headers ────────────────────────────────────────────────────────
    # Try: "Columns: [A | B | C]" or "Columns: A | B | C"
    col_match = re.search(
        r'Columns?\s*(?:Headers?)?\s*[:\-]?\s*[\[\(]?([^\]\)\n]+?)[\]\)]?\s*$',
        text, re.IGNORECASE | re.MULTILINE
    )
    if col_match:
        headers = _split_pipes(col_match.group(1).strip())
        if len(headers) < 2:
            headers = [h.strip().strip("'\"") for h in col_match.group(1).split(',') if h.strip()]
    else:
        headers = None

    # Fallback: "Column 1: X / Column 2: Y / Column 3: Z" on separate bullet lines
    if not headers or len(headers) < 2:
        col_bullet_matches = re.findall(
            r'[-•]\s*Column\s+\d+\s*[:\(][^)]*\)?\s*[:\-]?\s*(.+)',
            text, re.IGNORECASE
        )
        if col_bullet_matches and len(col_bullet_matches) >= 2:
            headers = [h.strip().rstrip('.').strip("'\"") for h in col_bullet_matches]

    # Second fallback: paragraph "Column headers: A | B" or "with N columns: [A | B | C]"
    if not headers or len(headers) < 2:
        inline = re.search(
            r'(?:with\s+\d+\s+columns?|column\s+headers?)\s*[:\-]?\s*[\[\(]?([^\]\)\.\n]{5,})[\]\)]?',
            text, re.IGNORECASE
        )
        if inline:
            candidate = inline.group(1).strip()
            h = _split_pipes(candidate)
            if len(h) < 2:
                h = [x.strip().strip("'\"") for x in candidate.split(',') if x.strip()]
            if len(h) >= 2:
                headers = h

    if not headers or len(headers) < 2:
        return None

    # ── Extract rows ───────────────────────────────────────────────────────────
    # Patterns:
    #   "1. val | val | val"           (period)
    #   "Row 1: val | val | val"       (Row N:)
    #   "Row 1 (Label): val | val"     (Row N (Label):)
    row_pattern = re.compile(
        r'(?:'
        r'^\s*\d+[\.\)]\s+(.+)'           # "1. ..." or "1) ..."
        r'|'
        r'^\s*Row\s+\d+\s*(?:\([^)]*\))?\s*[:\-]\s*(.+)'   # "Row N: ..." or "Row N (lbl): ..."
        r')',
        re.MULTILINE | re.IGNORECASE
    )
    raw_rows = []
    for m in row_pattern.finditer(text):
        raw = (m.group(1) or m.group(2) or "").strip()
        if raw:
            raw_rows.append(raw)

    # If no numbered rows, try inline paragraph "Row N — label: val vs val" short form
    if not raw_rows:
        inline_rows = re.findall(
            r'Row\s+\d+\s*\(([^)]+)\)\s*[:]\s*([^.R]+)',
            text, re.IGNORECASE
        )
        if inline_rows:
            for label, vals in inline_rows:
                raw_rows.append(f"{label} | {' | '.join(_split_pipes(vals))}")

    if not raw_rows:
        return None

    rows = []
    for raw in raw_rows:
        cells = _split_arrows(raw) if '→' in raw else _split_pipes(raw)
        if len(cells) >= 2:
            while len(cells) < len(headers):
                cells.append("")
            rows.append(cells[:len(headers)])

    if not rows:
        return None

    return {"headers": headers, "rows": rows, "footer": _extract_footer(text)}


# ── Format B: narrative "Row N — label: val1; val2" ───────────────────────────

def _parse_format_b(text):
    """Narrative format: 'Row 1 — Natural resource extraction: GDP...; Green NP...'"""
    # Headers from "Column headers: 'A', 'B'" or "two-column... Column 1: X, Column 2: Y"
    col_match = re.search(
        r"Column headers?\s*[:\-]\s*(.+?)(?=\.|Row|\n)",
        text, re.IGNORECASE
    )
    if not col_match:
        # Try "Column 1 (Name): ... Column 2 (Name): ..."
        col_match = re.search(
            r"two[\s-]+column.*?Left header:\s*['\"](.+?)['\"].*?Column\s+1.*?:\s*['\"](.+?)['\"].*?Column\s+2.*?:\s*['\"](.+?)['\"]",
            text, re.IGNORECASE | re.DOTALL
        )
        if col_match:
            headers = [col_match.group(1), col_match.group(2), col_match.group(3)]
        else:
            return None
    else:
        # Parse "'A', 'B', 'C'" or "A, B, C"
        headers = [h.strip().strip("'\"") for h in col_match.group(1).split(',') if h.strip()]

    if len(headers) < 2:
        return None

    # Find rows: "Row N — label: val1; val2" or "(N) label: val1 vs val2"
    row_pattern = re.compile(
        r'Row\s+\d+\s*[\-—]\s*(.+?):\s*(.+?)(?=\.\s*Row\s+\d|\.\s*Key\s|$)',
        re.IGNORECASE | re.DOTALL
    )
    raw_rows = row_pattern.findall(text)
    if not raw_rows:
        return None

    rows = []
    for label, values in raw_rows:
        # Split values on "; " or " vs " or ";"
        parts = re.split(r';\s*(?=[A-Z])|(?<=[a-z\.]);\s*|(?<=\))\s*;\s*', values.strip())
        if len(parts) == 1:
            parts = re.split(r'\s+vs\s+', parts[0], flags=re.IGNORECASE)
        row = [label.strip()] + [p.strip() for p in parts]
        while len(row) < len(headers):
            row.append("")
        rows.append(row[:len(headers)])

    if not rows:
        return None

    return {"headers": headers, "rows": rows, "footer": _extract_footer(text)}


# ── Format C: "ROW HEADERS (X): ... / COLUMN 1 (Y): ..." ─────────────────────

def _parse_format_c(text):
    """Inverted layout where columns define the data (BoP format)."""
    rh_match = re.search(r'Row headers?\s*\((.+?)\)\s*[:\-]\s*(.+)', text, re.IGNORECASE)
    if not rh_match:
        return None

    col_headers_raw = re.findall(
        r'Column\s+\d+\s*\((.+?)\)\s*[:\-]\s*(.+?)(?=Column\s+\d|$)',
        text, re.IGNORECASE | re.DOTALL
    )
    if not col_headers_raw:
        return None

    # Build as a transposed structure
    dim_label = rh_match.group(1).strip()
    row_labels = [r.strip() for r in re.split(r'\s*[\|;,]\s*', rh_match.group(2)) if r.strip()]
    col_names = [c[0].strip() for c in col_headers_raw]

    headers = [dim_label] + col_names
    # Parse each column's values
    col_values = []
    for _, vals_raw in col_headers_raw:
        vals = [v.strip() for v in re.split(r'\s*[\|;,]\s*', vals_raw.strip()) if v.strip()]
        col_values.append(vals)

    rows = []
    for i, label in enumerate(row_labels):
        row = [label]
        for cv in col_values:
            row.append(cv[i] if i < len(cv) else "")
        rows.append(row)

    if not rows:
        return None

    return {"headers": headers, "rows": rows, "footer": _extract_footer(text)}


# ── Format D: inline "Row N (Label): col1 val | col2 val" ─────────────────────

def _parse_format_d(text):
    """Two-column table with 'Row N (Label): val1 vs val2' pattern."""
    # Detect: "A two-column comparative table ... rows: (1) label — X vs Y"
    rows_pat = re.compile(
        r'\((\d+)\)\s+(.+?)\s*[—\-]+\s*(.+?)(?=\(\d+\)|Key\s|$)',
        re.DOTALL
    )
    raw = rows_pat.findall(text)
    if len(raw) < 2:
        return None

    # Try to extract headers from "Column 1 header: X; Column 2 header: Y"
    h_match = re.search(
        r"Column\s+1\s+header:\s*['\"]?(.+?)['\"]?\s*[;,]\s*Column\s+2\s+header:\s*['\"]?(.+?)['\"]",
        text, re.IGNORECASE
    )
    if h_match:
        headers = ["Dimension", h_match.group(1).strip(), h_match.group(2).strip()]
    else:
        headers = ["Dimension", "Option A", "Option B"]

    rows = []
    for _, label, vals in raw:
        parts = re.split(r'\s+vs\s+|\s*[;]\s*', vals.strip(), maxsplit=1)
        row = [label.strip()] + [p.strip() for p in parts]
        while len(row) < 3:
            row.append("")
        rows.append(row[:3])

    return {"headers": headers, "rows": rows, "footer": _extract_footer(text)}


# ── Format E: 2×2 matrix (Cell 1 (R+C): val, Cell 2 ...) ─────────────────────

def _parse_format_2x2(text):
    """Handle: 'rows representing X (A/B), columns representing Y (C/D). Cell 1 (A+C): val...'"""
    row_dim = re.search(r'rows?\s+representing\s+(\w[\w\s]+?)\s*\(([^)]+)\)', text, re.IGNORECASE)
    col_dim = re.search(r'columns?\s+representing\s+(\w[\w\s]+?)\s*\(([^)]+)\)', text, re.IGNORECASE)
    cells   = re.findall(r'Cell\s+\d+\s*\([^)]+\)\s*[:\-]\s*(.+?)(?=Cell\s+\d+|This matrix|$)',
                         text, re.IGNORECASE | re.DOTALL)
    if not (row_dim and col_dim and len(cells) == 4):
        return None

    row_labels = [x.strip() for x in row_dim.group(2).split('/')]
    col_labels = [x.strip() for x in col_dim.group(2).split('/')]
    headers = [f"{row_dim.group(1)} \\ {col_dim.group(1)}"] + col_labels
    rows = [
        [row_labels[0], cells[0].strip().strip('.'), cells[1].strip().strip('.')],
        [row_labels[1], cells[2].strip().strip('.'), cells[3].strip().strip('.')],
    ]
    return {"headers": headers, "rows": rows, "footer": _extract_footer(text)}


# ── Format F: ASCII payoff matrix with existing | lines ──────────────────────

def _parse_ascii_table(text):
    """Extract tables already formatted as ASCII '| col1 | col2 |' in the description."""
    # Find all lines that look like table rows: at least 2 | separators
    table_lines = [l for l in text.split('\n')
                   if l.count('|') >= 2 and not re.match(r'^\s*[-|]+\s*$', l)]
    if len(table_lines) < 2:
        return None

    parsed = []
    for line in table_lines:
        cells = [c.strip() for c in line.split('|') if c.strip()]
        if len(cells) >= 2:
            parsed.append(cells)

    if len(parsed) < 2:
        return None

    # First row = headers
    max_cols = max(len(r) for r in parsed)
    headers = parsed[0]
    rows = []
    for row in parsed[1:]:
        while len(row) < max_cols:
            row.append("")
        rows.append(row[:max_cols])

    if not rows:
        return None

    return {"headers": headers, "rows": rows, "footer": _extract_footer(text)}


# ── Main entry point ───────────────────────────────────────────────────────────

def render_table(diagram_description: str) -> str:
    """
    Parse a table diagram_description and return rendered HTML.
    Falls back to preformatted text if parsing fails.
    """
    if not diagram_description:
        return ""

    title = _extract_title(diagram_description)

    # Try each parser in order of specificity
    for parser in (_parse_format_a, _parse_format_b, _parse_format_c,
                   _parse_format_d, _parse_format_2x2, _parse_ascii_table):
        result = parser(diagram_description)
        if result and result.get("rows"):
            return _html_table(
                title=title,
                headers=result["headers"],
                rows=result["rows"],
                footer=result.get("footer"),
            )

    # Fallback: preformatted text
    return _html_preformatted(diagram_description, title=title)
