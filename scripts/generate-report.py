#!/usr/bin/env python3
"""
Generate detailed markdown report from merged JSON data.

Reads merged pipeline output and generates a comprehensive report with:
- Full metadata (publish date, source, links)
- Detailed summaries
- Proper categorization by region/agency
- Statistics overview

Usage:
    python3 generate-report.py --input /tmp/fin-pol-merged.json --output /tmp/report.md [--verbose]
"""

import argparse
import json
import logging
import sys
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from collections import defaultdict


# China Standard Time (UTC+8)
CHINA_TZ = timezone(timedelta(hours=8))


# Source categories mapping
SOURCE_CATEGORIES = {
    # Shenzhen
    'sz.gov.cn': {'region': '深圳', 'agency': '市政府'},
    'szft.gov.cn': {'region': '深圳', 'agency': '发改委'},
    'szfb.gov.cn': {'region': '深圳', 'agency': '财政局'},
    # Beijing
    'beijing.gov.cn': {'region': '北京', 'agency': '市政府'},
    'fgw.beijing.gov.cn': {'region': '北京', 'agency': '发改委'},
    # Guangdong
    'gd.gov.cn': {'region': '广东', 'agency': '省政府'},
    'gdrd.gd.gov.cn': {'region': '广东', 'agency': '发改委'},
    # Financial regulators
    'pbc.gov.cn': {'region': '金融监管', 'agency': '人民银行'},
    'nfra.gov.cn': {'region': '金融监管', 'agency': '金融监管总局'},
    'cbirc.gov.cn': {'region': '金融监管', 'agency': '金融监管总局'},
    'csrc.gov.cn': {'region': '金融监管', 'agency': '证监会'},
    # Xuexi Qiangguo
    'xuexi.cn': {'region': '学习强国', 'agency': '学习平台'},
}


def categorize_article(article: Dict[str, Any]) -> Dict[str, str]:
    """Categorize article by region and agency based on URL."""
    url = article.get('link', '')
    source_name = article.get('source', '')

    # Check URL patterns
    for domain, info in SOURCE_CATEGORIES.items():
        if domain in url:
            return {'region': info['region'], 'agency': info['agency']}

    # Check source name
    for domain, info in SOURCE_CATEGORIES.items():
        if domain in source_name:
            return {'region': info['region'], 'agency': info['agency']}

    # Default categorization by source name patterns
    if '学习强国' in source_name or 'xuexi' in url.lower() or 'xuexi' in source_name.lower():
        return {'region': '学习强国', 'agency': '学习平台'}
    if '证监会' in source_name or 'csrc' in url.lower():
        return {'region': '金融监管', 'agency': '证监会'}
    if '央行' in source_name or '人民银行' in source_name:
        return {'region': '金融监管', 'agency': '人民银行'}
    if '金监' in source_name or '银保' in source_name:
        return {'region': '金融监管', 'agency': '金融监管总局'}
    if '深圳' in source_name or 'sz' in url.lower():
        return {'region': '深圳', 'agency': '市政府'}
    if '北京' in source_name or 'beijing' in url.lower():
        return {'region': '北京', 'agency': '市政府'}
    if '广东' in source_name or 'gd' in url.lower():
        return {'region': '广东', 'agency': '省政府'}

    return {'region': '其他', 'agency': '未知'}


def get_article_type(article: Dict[str, Any]) -> str:
    """Determine article type (政策文件/项目动态/监管通知/政策解读/其他)."""
    title = article.get('title', '')
    content = (article.get('content') or article.get('summary') or '')
    source_name = article.get('source', '')

    # Check if this is from Xuexi Qiangguo
    if '学习强国' in source_name or 'xuexi' in source_name.lower():
        title_lower = title.lower()
        content_lower = content.lower()

        # Xuexi-specific types
        if '解读' in title or '解读' in content:
            return '政策解读'
        if '讲话' in title or '精神' in title:
            return '重要讲话'
        if '改革' in title or '发展' in title:
            return '改革发展'
        return '时政新闻'

    title_lower = title.lower()
    content_lower = content.lower()

    # Policy indicators
    policy_keywords = ['政策', '办法', '规定', '条例', '通知', '意见', '方案',
                       '指引', '实施细则', '发布', '印发', '征求意见']

    # Project indicators
    project_keywords = ['招标', '采购', '公示', '项目', '中标', '成交',
                       '预算', '公告', '资格预审']

    # Regulatory indicators
    regulatory_keywords = ['监管', '处罚', '罚单', '警示', '风险', '合规']

    for keyword in regulatory_keywords:
        if keyword in title_lower or keyword in content_lower:
            return '监管通知'

    for keyword in project_keywords:
        if keyword in title_lower or keyword in content_lower:
            return '项目动态'

    for keyword in policy_keywords:
        if keyword in title_lower:
            return '政策文件'

    return '其他'


def parse_report_datetime(value: str) -> Optional[datetime]:
    """Parse ISO or RFC 2822-style datetimes and normalize to China time."""
    if not isinstance(value, str) or not value.strip():
        return None

    value = value.strip()

    try:
        dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except Exception:
        try:
            dt = parsedate_to_datetime(value)
        except Exception:
            return None

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=CHINA_TZ)

    return dt.astimezone(CHINA_TZ)


def format_date(iso_date: str) -> str:
    """Format ISO or RFC 2822-style date string to readable format."""
    dt = parse_report_datetime(iso_date)
    if dt is not None:
        return dt.strftime('%Y-%m-%d %H:%M')
    return (iso_date or '')[:19]


def truncate_text(text: str, max_len: int = 200) -> str:
    """Truncate text to max length, adding ellipsis if needed."""
    if not text:
        return ''
    text = text.strip()
    if len(text) <= max_len:
        return text
    return text[:max_len].rsplit('，', 1)[0].rsplit('。', 1)[0] + '...'


def strip_html_tags(html: str) -> str:
    """Remove HTML tags from content."""
    import re
    if not html:
        return ''
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', '', html)
    # Remove extra whitespace
    text = ' '.join(text.split())
    return text[:500]


def get_editorial_note(article: Dict[str, Any]) -> str:
    """Get the best available AI/editorial note for an article."""
    for key in (
        'editorial_note',
        'ai_commentary',
        'ai_note',
        'commentary',
        'analysis',
        'note',
    ):
        value = article.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ''


def get_editorial_alert(article: Dict[str, Any]) -> str:
    """Get a warning/reminder style note when available."""
    for key in (
        'editorial_alert',
        'alert',
        'warning',
        'reminder',
        'risk_note',
    ):
        value = article.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ''


class ReportGenerator:
    """Generate detailed markdown report."""

    def __init__(self, data: Dict[str, Any], rss_data: Optional[Dict[str, Any]] = None,
                 web_data: Optional[Dict[str, Any]] = None):
        self.data = data
        self.rss_data = rss_data or {}
        self.web_data = web_data or {}
        self.articles = self._extract_articles()
        self.categorized = self._categorize_articles()
        self.stats = self._calculate_stats()

    def _extract_articles(self) -> List[Dict[str, Any]]:
        """Extract all articles from merged data."""
        articles = []

        # Handle different data structures
        if 'articles' in self.data:
            articles = self.data['articles']
        elif 'topics' in self.data:
            for topic_data in self.data['topics'].values():
                if isinstance(topic_data, dict) and 'articles' in topic_data:
                    articles.extend(topic_data['articles'])
        elif 'sources' in self.data:
            for source in self.data['sources']:
                if isinstance(source, dict) and 'articles' in source:
                    articles.extend(source['articles'])

        return articles

    def _categorize_articles(self) -> Dict[str, Dict[str, List[Dict[str, Any]]]]:
        """Categorize articles by region and type."""
        categorized = defaultdict(lambda: defaultdict(list))

        for article in self.articles:
            if not isinstance(article, dict):
                continue

            cat = categorize_article(article)
            article_type = get_article_type(article)

            # Add metadata
            article['_region'] = cat['region']
            article['_agency'] = cat['agency']
            article['_type'] = article_type

            categorized[cat['region']][article_type].append(article)

        return dict(categorized)

    def _calculate_stats(self) -> Dict[str, Any]:
        """Calculate statistics for the report."""
        stats = {
            'total': len(self.articles),
            'by_region': defaultdict(lambda: defaultdict(int)),
            'by_type': defaultdict(int),
        }

        for region, types in self.categorized.items():
            for article_type, articles in types.items():
                stats['by_region'][region][article_type] = len(articles)
                stats['by_type'][article_type] += len(articles)

        return stats

    def _categorize_source_region(self, name: str, url: str) -> str:
        article_like = {'source': name or '', 'link': url or ''}
        return categorize_article(article_like)['region']

    def _get_region_empty_reason(self, region: str) -> str:
        rss_sources = []
        for source in self.rss_data.get('sources', []) if isinstance(self.rss_data, dict) else []:
            source_region = self._categorize_source_region(source.get('name', ''), source.get('url', ''))
            if source_region == region:
                rss_sources.append(source)

        rss_errors = [s for s in rss_sources if s.get('status') != 'ok']
        rss_ok_zero = [s for s in rss_sources if s.get('status') == 'ok' and int(s.get('count', 0) or 0) == 0]
        rss_ok_nonzero = [s for s in rss_sources if s.get('status') == 'ok' and int(s.get('count', 0) or 0) > 0]

        web_topics = self.web_data.get('topics', []) if isinstance(self.web_data, dict) else []
        filtered_empty_topics = [t for t in web_topics if t.get('status') == 'filtered_empty']
        web_error_topics = [t for t in web_topics if t.get('status') == 'error']
        web_ok_topics = [t for t in web_topics if t.get('status') in ('ok', 'filtered_empty')]

        if rss_sources and len(rss_errors) == len(rss_sources):
            return '抓取异常：相关 RSS 源本轮未成功返回结果。'

        if rss_ok_nonzero:
            return '48小时内该分类未形成可汇报条目，可能已在其他分类呈现。'

        if rss_sources and rss_ok_zero and not rss_errors:
            if filtered_empty_topics:
                return '48小时内相关 RSS 无新消息，且 Web 检索结果被筛选规则全部排除。'
            return '48小时内无新消息。'

        if filtered_empty_topics and not web_error_topics:
            return 'Web 检索有候选结果，但本轮被筛选规则全部排除。'

        if web_error_topics and not web_ok_topics and not rss_sources:
            return '抓取异常：相关 Web 检索本轮未取得有效结果。'

        return '48小时内无新消息，或未检索到有效结果。'

    def generate(self) -> str:
        """Generate the complete markdown report."""
        lines = []

        # Header
        lines.extend(self._generate_header())
        lines.append('')

        # Top articles
        lines.extend(self._generate_top_articles())
        lines.append('')

        # Regional sections
        region_order = ['深圳', '北京', '广东', '金融监管', '学习强国', '其他']
        for region in region_order:
            lines.extend(self._generate_region_section(region))
            lines.append('')

        # Put the stats table at the end so the narrative comes first
        lines.extend(self._generate_stats_table())
        lines.append('')

        # Footer
        lines.extend(self._generate_footer())

        return '\n'.join(lines)

    def _generate_header(self) -> List[str]:
        """Generate report header."""
        now = datetime.now(CHINA_TZ)
        date_str = now.strftime('%Y年%m月%d日')
        time_str = now.strftime('%H:%M')

        return [
            '# 金融政策日报 | Policy & Finance Daily',
            '',
            f'**日期**: {date_str} | **生成时间**: {time_str} | **覆盖范围**: 近48小时',
        ]

    def _generate_stats_table(self) -> List[str]:
        """Generate statistics overview table."""
        lines = [
            '## 📊 数据概览',
            '',
            '| 地区/机构 | 政策文件 | 项目动态 | 监管通知 | 其他 | 合计 |',
            '| :--- | :---: | :---: | :---: | :---: | :---: |',
        ]

        region_order = ['深圳', '北京', '广东', '金融监管', '学习强国', '其他']
        grand_total = 0

        for region in region_order:
            if region not in self.stats['by_region']:
                continue

            region_stats = self.stats['by_region'][region]
            policy = region_stats.get('政策文件', 0)
            project = region_stats.get('项目动态', 0)
            regulatory = region_stats.get('监管通知', 0)
            other = region_stats.get('其他', 0)
            total = sum([policy, project, regulatory, other])
            grand_total += total

            # Region emoji
            emoji = {
                '深圳': '🏙️',
                '北京': '🏛️',
                '广东': '🌏',
                '金融监管': '🏦',
                '其他': '📋',
            }.get(region, '')

            lines.append(f'| {emoji} {region} | {policy} | {project} | {regulatory} | {other} | **{total}** |')

        # Total row
        total_policy = self.stats['by_type'].get('政策文件', 0)
        total_project = self.stats['by_type'].get('项目动态', 0)
        total_regulatory = self.stats['by_type'].get('监管通知', 0)
        total_other = self.stats['by_type'].get('其他', 0)

        lines.append(f'| **总计** | **{total_policy}** | **{total_project}** | **{total_regulatory}** | **{total_other}** | **{grand_total}** |')

        return lines

    def _generate_top_articles(self) -> List[str]:
        """Generate top 5 articles section."""
        # Sort by quality score or recency
        scored_articles = []
        for article in self.articles:
            if not isinstance(article, dict):
                continue
            score = article.get('quality_score', 0)
            # Use published date as secondary sort
            published = article.get('published', '')
            scored_articles.append((score, published, article))

        scored_articles.sort(key=lambda x: (x[0], x[1]), reverse=True)
        top_articles = [a for _, _, a in scored_articles[:5]]

        lines = ['## 🔥 核心焦点 (Top 5)', '']

        for i, article in enumerate(top_articles, 1):
            title = article.get('title', '无标题')[:80]
            source = article.get('source', '未知')
            article_type = article.get('_type', '其他')
            published = format_date(article.get('published', ''))
            summary = truncate_text(strip_html_tags(article.get('content', '') or article.get('summary', '')), 260)
            link = article.get('link', '')
            editorial_note = truncate_text(strip_html_tags(get_editorial_note(article)), 180)
            editorial_alert = truncate_text(strip_html_tags(get_editorial_alert(article)), 120)

            lines.append(f'### {i}. {title}')
            lines.append('')
            lines.append(f'- 📅 时间: {published}')
            lines.append(f'- 🏛️ 来源: {source}')
            lines.append(f'- 📄 类型: {article_type}')
            if summary:
                lines.append(f'- 📝 原文摘要: {summary}')
            if editorial_note:
                lines.append(f'- 💡 点评: {editorial_note}')
            if editorial_alert:
                lines.append(f'- ⚠️ 提醒: {editorial_alert}')
            if link:
                lines.append(f'- 🔗 链接: [{link}]({link})')
            lines.append('')

        return lines

    def _generate_region_section(self, region: str) -> List[str]:
        """Generate section for a region."""
        lines = [f'## {self._region_emoji(region)} {region}', '']

        types = self.categorized[region]
        # Different type order for different regions
        if region == '学习强国':
            type_order = ['政策解读', '重要讲话', '改革发展', '时政新闻', '其他']
        else:
            type_order = ['政策文件', '项目动态', '监管通知', '其他']

        has_content = False
        for article_type in type_order:
            if article_type not in types or not types[article_type]:
                continue

            has_content = True
            lines.append(f'### {self._type_emoji(article_type)} {article_type}')
            lines.append('')

            # Generate list for this type
            lines.extend(self._generate_article_list(types[article_type], article_type))
            lines.append('')

        if not has_content:
            lines.append(f'*{self._get_region_empty_reason(region)}*')
            lines.append('')

        return lines

    def _generate_article_list(self, articles: List[Dict[str, Any]], article_type: str) -> List[str]:
        """Generate list for articles of a specific type."""
        lines = []

        for article in articles[:20]:  # Limit to 20 per type
            title = article.get('title', '无标题')
            published = format_date(article.get('published', ''))
            source = article.get('source', '未知')
            # Get content from either 'content' or 'summary' field
            content = article.get('content', '') or article.get('summary', '')
            summary = truncate_text(strip_html_tags(content), 320)
            link = article.get('link', '')
            editorial_note = truncate_text(strip_html_tags(get_editorial_note(article)), 220)
            editorial_alert = truncate_text(strip_html_tags(get_editorial_alert(article)), 140)

            lines.append(f'#### {title}')
            lines.append('')
            lines.append(f'- 📅 时间: {published}')
            lines.append(f'- 🏛️ 来源: {source}')
            if summary:
                lines.append(f'- 📝 原文摘要: {summary}')
            if editorial_note:
                lines.append(f'- 💡 点评: {editorial_note}')
            if editorial_alert:
                lines.append(f'- ⚠️ 提醒: {editorial_alert}')
            if link:
                lines.append(f'- 🔗 链接: [查看原文]({link})')
            lines.append('')

        return lines

    def _generate_footer(self) -> List[str]:
        """Generate report footer."""
        return [
            '---',
            '',
            '📊 **统计信息**',
            f'- 总文章数: {self.stats["total"]}',
            f'- 生成时间: {datetime.now(CHINA_TZ).strftime("%Y-%m-%d %H:%M:%S UTC+8")}',
            '',
            '**本报告由 `fin-pol-gov-news` 自动生成**',
            '**数据来源**: 深圳市政府、北京市政府、广东省政府、人民银行、金融监管总局官网、学习强国平台',
        ]

    def _region_emoji(self, region: str) -> str:
        """Get emoji for region."""
        return {
            '深圳': '🏙️',
            '北京': '🏛️',
            '广东': '🌏',
            '金融监管': '🏦',
            '学习强国': '📖',
            '其他': '📋',
        }.get(region, '')

    def _type_emoji(self, article_type: str) -> str:
        """Get emoji for article type."""
        return {
            '政策文件': '📄',
            '项目动态': '🏗️',
            '监管通知': '⚠️',
            '政策解读': '📖',
            '重要讲话': '🎯',
            '改革发展': '🚀',
            '时政新闻': '📰',
            '其他': '📌',
        }.get(article_type, '')


def escape_md_table(text: str) -> str:
    """Escape markdown table special characters."""
    if not text:
        return ''
    return text.replace('|', '\\|').replace('\n', ' ')


def main():
    parser = argparse.ArgumentParser(
        description="Generate detailed markdown report from merged JSON data. "
                    "--input must point to merged output from merge-sources.py; "
                    "--rss-input and --web-input are optional diagnostics only."
    )
    parser.add_argument("--input", "-i", required=True, type=Path,
                        help="Required merged JSON from merge-sources.py")
    parser.add_argument("--output", "-o", required=True, type=Path,
                        help="Output markdown report path")
    parser.add_argument("--rss-input", type=Path,
                        help="Optional raw rss.json used only to explain empty sections")
    parser.add_argument("--web-input", type=Path,
                        help="Optional raw web.json used only to explain empty sections")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s: %(message)s"
    )

    if not args.input.exists():
        logging.error(f"Input file not found: {args.input}")
        sys.exit(1)

    logging.info(f"Reading {args.input}")
    with open(args.input, 'r', encoding='utf-8') as f:
        data = json.load(f)

    rss_data = None
    web_data = None
    if args.rss_input and args.rss_input.exists():
        with open(args.rss_input, 'r', encoding='utf-8') as f:
            rss_data = json.load(f)
    if args.web_input and args.web_input.exists():
        with open(args.web_input, 'r', encoding='utf-8') as f:
            web_data = json.load(f)

    generator = ReportGenerator(data, rss_data=rss_data, web_data=web_data)
    report = generator.generate()

    with open(args.output, 'w', encoding='utf-8') as f:
        f.write(report)

    logging.info(f"✅ Report generated: {args.output}")
    logging.info(f"   Total articles: {generator.stats['total']}")


if __name__ == "__main__":
    main()
