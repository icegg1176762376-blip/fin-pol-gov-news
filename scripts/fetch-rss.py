#!/usr/bin/env python3
"""
Fetch RSS feeds using requests library (fixes SSL ECC issues).

Reads sources.json, filters RSS sources, fetches feeds in parallel with retry mechanism,
and outputs structured JSON with articles tagged by topics.

Usage:
 python3 fetch-rss.py [--config CONFIG_DIR] [--hours 48] [--output FILE] [--verbose]
"""

import json
import sys
import os
import argparse
import logging
import time
from datetime import datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, List, Any, Optional
import threading
from email.utils import parsedate_to_datetime

# Use requests instead of urllib to fix SSL ECC issues
import requests
from requests.adapters import HTTPAdapter
from urllib3.poolmanager import PoolManager

# Try to import feedparser
try:
    import feedparser
    HAS_FEEDPARSER = True
except ImportError:
    HAS_FEEDPARSER = False

def setup_logging(verbose: bool) -> logging.Logger:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )
    return logging.getLogger(__name__)

class SSLAdapter(HTTPAdapter):
    """Custom HTTP adapter with relaxed SSL verification for government websites."""
    def init_poolmanager(self, connections, maxsize, block=False):
        self.poolmanager = PoolManager(
            num_pools=connections,
            maxsize=maxsize,
            block=block,
            ssl_version=131072,  # TLS 1.2+
        )

def fetch_feed(source: Dict[str, Any], hours: int, retries: int = 3, timeout: int = 30) -> Dict[str, Any]:
    """Fetch single RSS feed with requests library."""
    feed_url = source['url']
    source_id = source.get('id', 'unknown')
    source_name = source.get('name', 'Unknown')
    
    session = requests.Session()
    session.mount('https://', SSLAdapter())
    session.mount('http://', SSLAdapter())
    
    articles = []
    success = False
    error_msg = ""
    
    for attempt in range(retries):
        try:
            response = session.get(feed_url, timeout=timeout)
            response.raise_for_status()
            
            if HAS_FEEDPARSER:
                feed = feedparser.parse(response.content)
                if feed.bozo:
                    error_msg = f"Bozo feed: {feed.bozo_exception}"
                    continue
                
                cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
                
                for entry in feed.entries:
                    try:
                        # Parse published date
                        published = None
                        if hasattr(entry, 'published') and entry.published:
                            try:
                                published = parsedate_to_datetime(entry.published)
                            except:
                                published = datetime.now(timezone.utc)
                        elif hasattr(entry, 'updated') and entry.updated:
                            try:
                                published = parsedate_to_datetime(entry.updated)
                            except:
                                published = datetime.now(timezone.utc)
                        else:
                            published = datetime.now(timezone.utc)
                        
                        # Filter by date
                        if published and published < cutoff:
                            continue
                        
                        # Extract content
                        content = ""
                        if hasattr(entry, 'content') and entry.content:
                            content = entry.content[0].get('value', '')
                        elif hasattr(entry, 'summary') and entry.summary:
                            content = entry.summary
                        
                        article = {
                            'title': entry.get('title', ''),
                            'link': entry.get('link', ''),
                            'published': published.isoformat() if published else datetime.now(timezone.utc).isoformat(),
                            'source': source_name,
                            'source_id': source_id,
                            'source_type': 'rss',
                            'content': content,
                            'topics': source.get('topics', []),
                        }
                        articles.append(article)
                    except Exception as e:
                        logging.debug(f"Error processing entry: {e}")
                        continue
            else:
                # Fallback to regex parsing (simplified)
                import re
                content = response.text
                # Simple regex for common RSS elements
                items = re.findall(r'<item>(.*?)</item>', content, re.DOTALL)
                for item in items[:10]:  # Limit to 10 items
                    title_match = re.search(r'<title>(.*?)</title>', item)
                    link_match = re.search(r'<link>(.*?)</link>', item)
                    title = title_match.group(1) if title_match else ''
                    link = link_match.group(1) if link_match else ''
                    
                    article = {
                        'title': title,
                        'link': link,
                        'published': datetime.now(timezone.utc).isoformat(),
                        'source': source_name,
                        'source_id': source_id,
                        'source_type': 'rss',
                        'content': '',
                        'topics': source.get('topics', []),
                    }
                    articles.append(article)
            
            success = True
            break
            
        except Exception as e:
            error_msg = str(e)
            if attempt < retries - 1:
                time.sleep(2 ** attempt)  # Exponential backoff
            continue
    
    return {
        'source_id': source_id,
        'source_name': source_name,
        'articles': articles,
        'success': success,
        'error': error_msg if not success else None,
        'count': len(articles),
    }

def main() -> int:
    parser = argparse.ArgumentParser(description='Fetch RSS feeds with requests library')
    parser.add_argument('--defaults', type=Path, default=None)
    parser.add_argument('--config', type=Path, default=None)
    parser.add_argument('--hours', type=int, default=48)
    parser.add_argument('--output', type=Path, default=None)
    parser.add_argument('--verbose', '-v', action='store_true')
    parser.add_argument('--force', action='store_true')
    
    args = parser.parse_args()
    logger = setup_logging(args.verbose)
    
    # Load sources
    sources_file = args.defaults / 'sources.json' if args.defaults else None
    if not sources_file or not sources_file.exists():
        logger.error("sources.json not found")
        return 1
    
    with open(sources_file) as f:
        sources_data = json.load(f)
    
    sources = [s for s in sources_data.get('sources', []) if s.get('enabled', True) and s.get('type') == 'rss']
    logger.info(f"Loaded {len(sources)} enabled RSS sources")
    
    # Fetch feeds in parallel
    results = []
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(fetch_feed, source, args.hours): source for source in sources}
        for future in as_completed(futures):
            result = future.result()
            results.append(result)
            status = "✅" if result['success'] else "❌"
            logger.info(f"{status} {result['source_name']}: {result['count']} articles")
            if result['error']:
                logger.debug(f"Error: {result['error']}")
    
    # Aggregate results
    all_articles = []
    for result in results:
        all_articles.extend(result['articles'])
    
    output = {
        'generated': datetime.now(timezone.utc).isoformat(),
        'sources': [r['source_id'] for r in results],
        'articles': all_articles,
        'total_articles': len(all_articles),
        'success_count': sum(1 for r in results if r['success']),
        'total_sources': len(sources),
    }
    
    # Write output
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        logger.info(f"✅ Done: {output['total_articles']} articles → {args.output}")
    else:
        print(json.dumps(output, indent=2, ensure_ascii=False))
    
    return 0 if output['total_articles'] > 0 else 1

if __name__ == '__main__':
    sys.exit(main())
