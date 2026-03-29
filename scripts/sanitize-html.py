#!/usr/bin/env python3
"""
Convert markdown digest report to sanitized HTML email.

Supports tables, lists, blockquotes, inline formatting with proper HTML escaping.

Usage:
    python3 sanitize-html.py --input /tmp/report.md --output /tmp/email.html [--verbose]
"""

import argparse
import html
import re
import sys
import logging
from urllib.parse import urlparse
from typing import List, Tuple


def escape(text: str) -> str:
    """HTML-escape text content."""
    return html.escape(text, quote=True)


def is_safe_url(url: str) -> bool:
    """Validate URL is http(s) only."""
    try:
        parsed = urlparse(url.strip())
        return parsed.scheme in ('http', 'https')
    except Exception:
        return False


def safe_link(url: str, label: str = None, style: str = "color:#0969da;font-size:13px;text-decoration:none;") -> str:
    """Generate a safe HTML link with escaped content."""
    url = url.strip()
    if not is_safe_url(url):
        return escape(label or url)
    escaped_url = escape(url)
    escaped_label = escape(label or url)
    return f'<a href="{escaped_url}" style="{style}">{escaped_label}</a>'


def parse_table_row(line: str) -> List[str]:
    """Parse a markdown table row, returning list of cell contents."""
    # Remove leading/trailing pipes
    line = line.strip()
    if line.startswith('|'):
        line = line[1:]
    if line.endswith('|'):
        line = line[:-1]

    # Split by pipe (but not escaped pipes)
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
    """Check if a table row is a separator row (contains only ---, :---, etc.)."""
    return all(re.match(r'^:?-+:?$', cell.strip()) for cell in cells)


class MarkdownParser:
    """Parse markdown and convert to safe HTML."""

    def __init__(self):
        self.lines: List[str] = []
        self.idx: int = 0
        self.html_parts: List[str] = []
        self.in_table: bool = False
        self.table_rows: List[List[str]] = []
        self.table_header: bool = False
        self.in_list: bool = False
        self.list_char: str = ''

    def parse(self, md_content: str) -> str:
        """Parse markdown content and return HTML."""
        self.lines = md_content.strip().split('\n')
        self.idx = 0
        self.html_parts = []
        self.in_table = False
        self.table_rows = []
        self.table_header = False
        self.in_list = False

        # Email wrapper open
        self.html_parts.append(
            '<div style="max-width:700px;margin:0 auto;font-family:'
            '-apple-system,BlinkMacSystemFont,\'Segoe UI\',Roboto,\'PingFang SC\','
            '\'Microsoft YaHei\',sans-serif;color:#1a1a1a;line-height:1.7;'
            'font-size:14px;padding:16px">'
        )

        while self.idx < len(self.lines):
            line = self.lines[self.idx].rstrip()
            self._process_line(line)
            self.idx += 1

        # Close any open elements
        if self.in_table:
            self._close_table()
        if self.in_list:
            self.html_parts.append('</ul>')

        self.html_parts.append('</div>')
        return '\n'.join(self.html_parts)

    def _peek(self, offset: int = 1) -> str:
        """Look at next line without advancing."""
        if self.idx + offset < len(self.lines):
            return self.lines[self.idx + offset].rstrip()
        return ''

    def _process_line(self, line: str):
        """Process a single line of markdown."""
        stripped = line.strip()

        # Skip empty lines (but close table if needed)
        if not stripped:
            if self.in_table and not self._peek(1).startswith('|'):
                self._close_table()
            return

        # Table row
        if stripped.startswith('|'):
            self._handle_table_row(stripped)
            return

        # Close table if we're in one and next line is not a table row
        if self.in_table and not stripped.startswith('|'):
            self._close_table()

        # H1: # Title
        if stripped.startswith('# '):
            self._close_list_if_needed()
            title = escape(stripped[2:])
            self.html_parts.append(
                f'<h1 style="font-size:24px;font-weight:700;color:#111;'
                f'border-bottom:3px solid #2563eb;padding-bottom:10px;'
                f'margin-top:24px;margin-bottom:16px">{title}</h1>'
            )
            return

        # H2: ## Section
        if stripped.startswith('## '):
            self._close_list_if_needed()
            section = escape(stripped[3:])
            self.html_parts.append(
                f'<h2 style="font-size:18px;font-weight:600;color:#1e40af;'
                f'margin-top:28px;margin-bottom:12px;padding-bottom:6px;'
                f'border-bottom:1px solid #e5e7eb">{section}</h2>'
            )
            return

        # H3: ### Subsection
        if stripped.startswith('### '):
            self._close_list_if_needed()
            section = escape(stripped[4:])
            self.html_parts.append(
                f'<h3 style="font-size:16px;font-weight:600;color:#374151;'
                f'margin-top:20px;margin-bottom:10px">{section}</h3>'
            )
            return

        # Blockquote: > text
        if stripped.startswith('> '):
            self._close_list_if_needed()
            text = self._process_inline(stripped[2:])
            self.html_parts.append(
                f'<blockquote style="background:#f0f9ff;border-left:4px solid #2563eb;'
                f'padding:14px 16px;margin:16px 0;color:#334155;'
                f'font-size:13px;border-radius:0 8px 8px 0">{text}</blockquote>'
            )
            return

        # Horizontal rule
        if stripped == '---' or stripped == '***':
            self._close_list_if_needed()
            self.html_parts.append('<hr style="border:none;border-top:1px solid #e5e7eb;margin:24px 0">')
            return

        # Bullet items: • or -
        if stripped.startswith('• ') or stripped.startswith('- '):
            self._handle_list_item(stripped)
            return

        # Code block
        if stripped.startswith('```'):
            self._handle_code_block()
            return

        # Stats/footer line
        if stripped.startswith('📊') or stripped.startswith('🤖') or stripped.startswith('📅') or stripped.startswith('⏰'):
            text = self._process_inline(stripped)
            self.html_parts.append(f'<p style="font-size:12px;color:#6b7280;margin-top:4px">{text}</p>')
            return

        # Regular paragraph
        self._close_list_if_needed()
        text = self._process_inline(stripped)
        self.html_parts.append(f'<p style="margin:12px 0">{text}</p>')

    def _handle_table_row(self, line: str):
        """Handle a table row."""
        cells = parse_table_row(line)

        if not self.in_table:
            self.in_table = True
            self.table_rows = []
            self.table_header = False

        # Check if this is a separator row
        if is_separator_row(cells):
            self.table_header = True
            return

        self.table_rows.append(cells)

        # Check if next line is also a table row
        if not self._peek(1).startswith('|'):
            self._render_table()

    def _close_table(self):
        """Close and render the current table."""
        if self.in_table:
            self._render_table()
            self.in_table = False

    def _render_table(self):
        """Render accumulated table rows as HTML."""
        if not self.table_rows:
            self.in_table = False
            return

        self.html_parts.append(
            '<table style="width:100%;border-collapse:collapse;'
            'margin:16px 0;font-size:13px;background:#fff">'
        )

        for i, row in enumerate(self.table_rows):
            is_header = (i == 0 and self.table_header) or (i == 0 and len(self.table_rows) > 1)
            tag = 'th' if is_header else 'td'

            self.html_parts.append('<tr>')
            for cell in row:
                processed = self._process_inline(cell)
                align = self._detect_alignment(cell)

                cell_style = 'padding:10px 12px;'
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
        """Detect column alignment from markdown syntax."""
        cell = cell.strip()
        if re.match(r'^:-+:$', cell):
            return 'center'
        elif re.match(r'^:-+$', cell):
            return 'left'
        elif re.match(r'^-+:$', cell):
            return 'right'
        return None

    def _handle_list_item(self, line: str):
        """Handle a list item."""
        char = '•' if '•' in line[:2] else '-'

        if not self.in_list:
            self.html_parts.append(
                '<ul style="padding-left:24px;margin:12px 0;list-style-type:disc">'
            )
            self.in_list = True
            self.list_char = char

        item_text = line[2:].strip()
        safe_item = self._process_inline(item_text)
        self.html_parts.append(
            f'<li style="margin-bottom:8px;line-height:1.6">{safe_item}</li>'
        )

    def _close_list_if_needed(self):
        """Close list if open."""
        if self.in_list:
            self.html_parts.append('</ul>')
            self.in_list = False

    def _handle_code_block(self):
        """Handle a code block."""
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
            f'<pre style="background:#f8fafc;border:1px solid #e2e8f0;'
            f'border-radius:6px;padding:12px;overflow-x:auto;'
            f'font-size:12px;font-family:\'SF Mono\',\'Fira Code\',monospace;'
            f'color:#334155;margin:12px 0"><code>{code}</code></pre>'
        )

    def _process_inline(self, text: str) -> str:
        """Process inline markdown (bold, links, code)."""
        # First escape everything
        result = escape(text)

        # Restore bold: **text** → <strong>
        result = re.sub(
            r'\*\*(.+?)\*\*',
            r'<strong style="color:#111;font-weight:600">\1</strong>',
            result
        )

        # Restore italic: *text* → <em>
        result = re.sub(
            r'(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)',
            r'<em style="font-style:italic">\1</em>',
            result
        )

        # Restore inline code: `text` → <code>
        result = re.sub(
            r'`(.+?)`',
            r'<code style="font-size:12px;color:#dc2623;background:#fef2f2;'
            r'padding:2px 6px;border-radius:4px;font-family:\'SF Mono\',monospace">\1</code>',
            result
        )

        # Restore angle-bracket links: <url>
        def restore_bracket_link(m):
            url = html.unescape(m.group(1))
            if is_safe_url(url):
                escaped_url = escape(url)
                try:
                    domain = urlparse(url).netloc
                    return f'<a href="{escaped_url}" style="color:#0969da;font-size:12px;text-decoration:none">{escape(domain)}</a>'
                except Exception:
                    return f'<a href="{escaped_url}" style="color:#0969da;font-size:12px">{escaped_url}</a>'
            return escape(url)

        result = re.sub(r'&lt;(https?://[^&]+?)&gt;', restore_bracket_link, result)

        # Restore markdown links: [text](url)
        def restore_md_link(m):
            label = html.unescape(m.group(1))
            url = html.unescape(m.group(2))
            if is_safe_url(url):
                return f'<a href="{escape(url)}" style="color:#0969da;text-decoration:none;font-weight:500">{escape(label)}</a>'
            return escape(label)

        result = re.sub(r'\[([^\]]+?)\]\(([^)]+?)\)', restore_md_link, result)

        return result


def markdown_to_safe_html(md_content: str) -> str:
    """Convert markdown digest report to sanitized HTML email."""
    parser = MarkdownParser()
    return parser.parse(md_content)


def main():
    parser = argparse.ArgumentParser(
        description="Convert markdown digest to sanitized HTML email"
    )
    parser.add_argument("--input", "-i", required=True, help="Input markdown file")
    parser.add_argument("--output", "-o", required=True, help="Output HTML file")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s: %(message)s"
    )

    try:
        with open(args.input, 'r', encoding='utf-8') as f:
            md_content = f.read()
    except FileNotFoundError:
        logging.error(f"Input file not found: {args.input}")
        sys.exit(1)

    logging.info(f"Converting {args.input} ({len(md_content)} chars)")

    html_output = markdown_to_safe_html(md_content)

    with open(args.output, 'w', encoding='utf-8') as f:
        f.write(html_output)

    logging.info(f"Wrote sanitized HTML to {args.output} ({len(html_output)} chars)")


if __name__ == "__main__":
    main()
