#!/usr/bin/env python3
"""
Generate styled PDF from markdown digest report.

Converts a markdown report into a professional PDF with Chinese font support,
proper table rendering, and clean typography.

Usage:
    python3 generate-pdf.py --input /tmp/report.md --output /tmp/report.pdf [--verbose]

Requirements:
    - weasyprint (pip install weasyprint)
    - Noto Sans CJK SC font (apt install fonts-noto-cjk)
"""

import argparse
import html
import re
import sys
import logging
from pathlib import Path
from urllib.parse import urlparse
from typing import List


def escape(text: str) -> str:
    return html.escape(text, quote=True)


def is_safe_url(url: str) -> bool:
    try:
        parsed = urlparse(url.strip())
        return parsed.scheme in ('http', 'https')
    except Exception:
        return False


def parse_table_row(line: str) -> List[str]:
    """Parse a markdown table row, returning list of cell contents."""
    line = line.strip()
    if line.startswith('|'):
        line = line[1:]
    if line.endswith('|'):
        line = line[:-1]

    cells = []
    current = []
    in_escape = False

    for char in line:
        if char == '\\':
            in_escape = True
        elif char == '|' and not in_escape:
            cells.append(''.join(current).strip())
            current = []
        else:
            current.append(char)
            in_escape = False

    if current:
        cells.append(''.join(current).strip())

    return cells


def is_separator_row(cells: List[str]) -> bool:
    """Check if a table row is a separator row."""
    return all(re.match(r'^:?-+:?$', cell.strip()) for cell in cells)


def _process_inline(text: str) -> str:
    """Process inline markdown with HTML escaping."""
    result = escape(text)

    # Bold: **text**
    result = re.sub(
        r'\*\*(.+?)\*\*',
        r'<strong style="font-weight:600;color:#111">\1</strong>',
        result
    )

    # Italic: *text*
    result = re.sub(
        r'(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)',
        r'<em style="font-style:italic">\1</em>',
        result
    )

    # Inline code: `text`
    result = re.sub(
        r'`(.+?)`',
        r'<code style="font-size:11px;color:#dc2623;background:#fef2f2;'
        r'padding:2px 5px;border-radius:3px;font-family:\'SF Mono\',monospace">\1</code>',
        result
    )

    # Angle-bracket links: <url>
    def restore_bracket_link(m):
        url = html.unescape(m.group(1))
        if is_safe_url(url):
            escaped_url = escape(url)
            try:
                domain = urlparse(url).netloc
                return f'<a href="{escaped_url}">{escape(domain)}</a>'
            except Exception:
                return f'<a href="{escaped_url}">{escaped_url}</a>'
        return escape(url)

    result = re.sub(r'&lt;(https?://[^&]+?)&gt;', restore_bracket_link, result)

    # Markdown links: [text](url)
    def restore_md_link(m):
        label = html.unescape(m.group(1))
        url = html.unescape(m.group(2))
        if is_safe_url(url):
            return f'<a href="{escape(url)}" style="color:#2563eb;text-decoration:none;font-weight:500">{escape(label)}</a>'
        return escape(label)

    result = re.sub(r'\[([^\]]+?)\]\(([^)]+?)\)', restore_md_link, result)

    return result


class MarkdownToHTML:
    """Convert markdown to HTML for PDF rendering."""

    def __init__(self):
        self.lines: List[str] = []
        self.idx: int = 0
        self.html_parts: List[str] = []
        self.in_table: bool = False
        self.table_rows: List[List[str]] = []
        self.table_header: bool = False
        self.in_list: bool = False

    def convert(self, md_content: str) -> str:
        """Convert markdown content to HTML."""
        self.lines = md_content.strip().split('\n')
        self.idx = 0
        self.html_parts = []
        self.in_table = False
        self.table_rows = []
        self.in_list = False

        while self.idx < len(self.lines):
            line = self.lines[self.idx].rstrip()
            self._process_line(line)
            self.idx += 1

        if self.in_table:
            self._close_table()
        if self.in_list:
            self.html_parts.append('</ul>')

        return '\n'.join(self.html_parts)

    def _peek(self, offset: int = 1) -> str:
        if self.idx + offset < len(self.lines):
            return self.lines[self.idx + offset].rstrip()
        return ''

    def _process_line(self, line: str):
        stripped = line.strip()

        if not stripped:
            if self.in_table and not self._peek(1).startswith('|'):
                self._close_table()
            return

        # Table row
        if stripped.startswith('|'):
            self._handle_table_row(stripped)
            return

        if self.in_table and not stripped.startswith('|'):
            self._close_table()

        # H1
        if stripped.startswith('# '):
            self._close_list_if_needed()
            title = _process_inline(stripped[2:])
            self.html_parts.append(
                f'<h1 style="font-size:22pt;color:#111;border-bottom:3px solid #2563eb;'
                f'padding-bottom:10px;margin-bottom:20px;margin-top:0">{title}</h1>'
            )
            return

        # H2
        if stripped.startswith('## '):
            self._close_list_if_needed()
            section = _process_inline(stripped[3:])
            self.html_parts.append(
                f'<h2 style="font-size:15pt;color:#1e40af;margin-top:28px;margin-bottom:12px;'
                f'padding-bottom:4px;border-bottom:1px solid #e5e7eb">{section}</h2>'
            )
            return

        # H3
        if stripped.startswith('### '):
            self._close_list_if_needed()
            section = _process_inline(stripped[4:])
            self.html_parts.append(
                f'<h3 style="font-size:13pt;color:#374151;margin-top:20px;margin-bottom:8px">{section}</h3>'
            )
            return

        if stripped.startswith('#### '):
            self._close_list_if_needed()
            section = _process_inline(stripped[5:])
            self.html_parts.append(
                f'<h4 style="font-size:11.5pt;color:#4b5563;margin-top:16px;margin-bottom:6px">{section}</h4>'
            )
            return

        # Blockquote
        if stripped.startswith('> '):
            self._close_list_if_needed()
            text = _process_inline(stripped[2:])
            self.html_parts.append(
                f'<blockquote style="background:#f0f9ff;border-left:4px solid #2563eb;'
                f'padding:12px 16px;margin:16px 0;color:#334155;font-size:10.5pt;'
                f'border-radius:0 6px 6px 0">{text}</blockquote>'
            )
            return

        # Horizontal rule
        if stripped == '---' or stripped == '***':
            self._close_list_if_needed()
            self.html_parts.append('<hr style="border:none;border-top:1px solid #e5e7eb;margin:28px 0">')
            return

        if len(stripped) >= 2 and stripped[0] in {'-', '*', '•'} and stripped[1] == ' ':
            self._handle_list_item(stripped)
            return

        # Bullet items
        if stripped.startswith('• ') or stripped.startswith('- '):
            self._handle_list_item(stripped)
            return

        # Code block
        if stripped.startswith('```'):
            self._handle_code_block()
            return

        # Footer/stats
        if stripped.startswith('📊') or stripped.startswith('🤖') or stripped.startswith('📅'):
            text = _process_inline(stripped)
            self.html_parts.append(f'<p class="footer">{text}</p>')
            return

        # Regular paragraph
        self._close_list_if_needed()
        text = _process_inline(stripped)
        self.html_parts.append(f'<p style="margin:10px 0">{text}</p>')

    def _handle_table_row(self, line: str):
        cells = parse_table_row(line)

        if not self.in_table:
            self.in_table = True
            self.table_rows = []
            self.table_header = False

        if is_separator_row(cells):
            self.table_header = True
            return

        self.table_rows.append(cells)

        if not self._peek(1).startswith('|'):
            self._render_table()

    def _close_table(self):
        if self.in_table:
            self._render_table()
            self.in_table = False

    def _render_table(self):
        if not self.table_rows:
            self.in_table = False
            return

        self.html_parts.append(
            '<table style="width:100%;border-collapse:collapse;margin:16px 0;font-size:10pt">'
        )

        for i, row in enumerate(self.table_rows):
            is_header = (i == 0 and self.table_header) or (i == 0 and len(self.table_rows) > 1)
            tag = 'th' if is_header else 'td'

            self.html_parts.append('<tr>')
            for cell in row:
                processed = _process_inline(cell)
                align = self._detect_alignment(cell)

                cell_style = 'padding:8px 10px;'
                if is_header:
                    cell_style += 'font-weight:600;text-align:left;color:#1f2937;border-bottom:2px solid #e5e7eb;'
                else:
                    cell_style += 'border-bottom:1px solid #f3f4f6;'

                if align:
                    cell_style += f'text-align:{align};'

                self.html_parts.append(f'<{tag} style="{cell_style}">{processed}</{tag}>')
            self.html_parts.append('</tr>')

        self.html_parts.append('</table>')
        self.table_rows = []
        self.table_header = False

    def _detect_alignment(self, cell: str) -> str:
        cell = cell.strip()
        if re.match(r'^:-+:$', cell):
            return 'center'
        elif re.match(r'^:-+$', cell):
            return 'left'
        elif re.match(r'^-+:$', cell):
            return 'right'
        return None

    def _handle_list_item(self, line: str):
        if not self.in_list:
            self.html_parts.append('<ul style="padding-left:20px;margin:8px 0">')
            self.in_list = True

        item_text = line[2:].strip()
        safe_item = _process_inline(item_text)
        self.html_parts.append(f'<li style="margin-bottom:6px;line-height:1.6">{safe_item}</li>')

    def _close_list_if_needed(self):
        if self.in_list:
            self.html_parts.append('</ul>')
            self.in_list = False

    def _handle_code_block(self):
        self._close_list_if_needed()
        self.idx += 1
        code_lines = []
        while self.idx < len(self.lines):
            line = self.lines[self.idx]
            if line.strip().startswith('```'):
                break
            code_lines.append(escape(line))
            self.idx += 1

        code = '\n'.join(code_lines)
        self.html_parts.append(
            f'<pre style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:6px;'
            f'padding:12px;overflow-x:auto;font-size:9pt;font-family:\'SF Mono\',monospace;'
            f'color:#334155;margin:12px 0"><code>{code}</code></pre>'
        )


PDF_CSS = """
@page {
    size: A4;
    margin: 2cm 2cm;
    @top-center {
        content: "金融政策日报";
        font-size: 9px;
        color: #999;
        font-family: 'Noto Sans CJK SC', 'Noto Sans SC', 'PingFang SC', sans-serif;
    }
    @bottom-center {
        content: counter(page) " / " counter(pages);
        font-size: 9px;
        color: #999;
        font-family: 'Noto Sans CJK SC', 'Noto Sans SC', 'PingFang SC', sans-serif;
    }
}

body {
    font-family: 'Noto Sans CJK SC', 'Noto Sans SC', 'PingFang SC',
                 'Microsoft YaHei', 'Segoe UI', Roboto, sans-serif;
    font-size: 11pt;
    line-height: 1.7;
    color: #1a1a1a;
}

h1 {
    font-size: 22pt;
    color: #111;
    border-bottom: 3px solid #2563eb;
    padding-bottom: 8px;
    margin-bottom: 20px;
    margin-top: 0;
}

h2 {
    font-size: 15pt;
    color: #1e40af;
    margin-top: 28px;
    margin-bottom: 12px;
    padding-bottom: 4px;
    border-bottom: 1px solid #e5e7eb;
}

h3 {
    font-size: 13pt;
    color: #374151;
    margin-top: 20px;
    margin-bottom: 8px;
}

h4 {
    font-size: 11.5pt;
    color: #4b5563;
    margin-top: 16px;
    margin-bottom: 6px;
}

blockquote {
    background: #f0f9ff;
    border-left: 4px solid #2563eb;
    padding: 12px 16px;
    margin: 16px 0;
    color: #334155;
    font-size: 10.5pt;
    border-radius: 0 6px 6px 0;
}

ul {
    padding-left: 20px;
    margin: 8px 0;
}

li {
    margin-bottom: 6px;
    line-height: 1.6;
}

a {
    color: #2563eb;
    text-decoration: none;
}

a:hover {
    text-decoration: underline;
}

strong {
    color: #111;
    font-weight: 600;
}

em {
    font-style: italic;
}

code {
    font-family: 'SF Mono', 'Fira Code', monospace;
    font-size: 9pt;
    background: #fef2f2;
    padding: 2px 5px;
    border-radius: 3px;
    color: #dc2623;
}

hr {
    border: none;
    border-top: 1px solid #e5e7eb;
    margin: 28px 0;
}

p.footer {
    font-size: 8.5pt;
    color: #9ca3af;
    margin-top: 4px;
}
"""


def wrap_html(body: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<style>
{PDF_CSS}
</style>
</head>
<body>
{body}
</body>
</html>"""


def main():
    parser = argparse.ArgumentParser(
        description="Generate styled PDF from markdown digest report",
    )
    parser.add_argument("--input", "-i", required=True, help="Input markdown file")
    parser.add_argument("--output", "-o", required=True, help="Output PDF file")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s: %(message)s"
    )

    try:
        import weasyprint
    except ImportError:
        logging.error("weasyprint not installed. Run: pip install weasyprint")
        sys.exit(1)

    input_path = Path(args.input)
    if not input_path.exists():
        logging.error(f"Input file not found: {args.input}")
        sys.exit(1)

    md_content = input_path.read_text(encoding='utf-8')
    logging.info(f"Converting {args.input} ({len(md_content)} chars)")

    # Convert markdown → HTML → PDF
    converter = MarkdownToHTML()
    body_html = converter.convert(md_content)
    full_html = wrap_html(body_html)

    if args.verbose:
        html_debug = Path(args.output).with_suffix('.html')
        html_debug.write_text(full_html, encoding='utf-8')
        logging.debug(f"Debug HTML saved: {html_debug}")

    logging.info("Generating PDF...")
    doc = weasyprint.HTML(string=full_html)
    doc.write_pdf(args.output)

    output_size = Path(args.output).stat().st_size
    logging.info(f"✅ PDF generated: {args.output} ({output_size / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
