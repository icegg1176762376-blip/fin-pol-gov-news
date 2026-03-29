#!/usr/bin/env python3
"""
Fetch RSS feeds using requests library (fixes SSL ECC issues).

Reads sources.json, filters RSS sources, fetches feeds in parallel with retry mechanism,
and outputs structured JSON with articles tagged by topics.

Usage:
    python3 fetch-rss.py [--config CONFIG_DIR] [--hours 48] [--output FILE] [--verbose]
"""

import json
import re
import sys
import os
import ssl
import argparse
import logging
import time
import tempfile
import shutil
import subprocess
from datetime import datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed
from email.utils import parsedate_to_datetime
from urllib.parse import urljoin, urlparse
from pathlib import Path
from typing import Dict, List, Any, Optional
import threading

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

# Constants
TIMEOUT = 30
MAX_WORKERS = 10
MAX_ARTICLES_PER_FEED = 20
RETRY_COUNT = 3
RETRY_DELAY = 2.0
RSS_CACHE_PATH = os.path.join(tempfile.gettempdir(), "fin-pol-gov-news-rss-cache.json")
RSS_CACHE_TTL_HOURS = 24


def setup_logging(verbose: bool) -> logging.Logger:
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    return logging.getLogger(__name__)


class SSLAdapter(HTTPAdapter):
    """Custom HTTP adapter with TLS 1.2+ support for government websites."""
    def init_poolmanager(self, connections, maxsize, block=False):
        ctx = ssl.create_default_context()
        if hasattr(ctx, "minimum_version"):
            ctx.minimum_version = ssl.TLSVersion.TLSv1_2
        self.poolmanager = PoolManager(
            num_pools=connections,
            maxsize=maxsize,
            block=block,
            ssl_context=ctx,
        )

    def proxy_manager_for(self, *args, **kwargs):
        ctx = ssl.create_default_context()
        if hasattr(ctx, "minimum_version"):
            ctx.minimum_version = ssl.TLSVersion.TLSv1_2
        kwargs["ssl_context"] = ctx
        return super().proxy_manager_for(*args, **kwargs)


def should_retry_with_curl(exc: Exception) -> bool:
    """Detect SSL failures that may succeed with a non-Python TLS stack."""
    msg = str(exc).lower()
    markers = (
        "bad ecpoint",
        "ssl",
        "wrong curve",
        "handshake failure",
        "tlsv1 alert",
        "ecc",
    )
    return any(marker in msg for marker in markers)


def parse_curl_headers(raw_headers: str) -> Dict[str, Any]:
    """Parse the final HTTP header block emitted by curl -D."""
    blocks = [block.strip() for block in raw_headers.replace("\r\n", "\n").split("\n\n") if block.strip()]
    if not blocks:
        return {"status_code": 0, "headers": {}}

    final = blocks[-1].splitlines()
    status_line = final[0] if final else ""
    status_code = 0
    m = re.match(r"HTTP/\S+\s+(\d+)", status_line)
    if m:
        status_code = int(m.group(1))

    headers: Dict[str, str] = {}
    for line in final[1:]:
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        headers[key.strip()] = value.strip()

    return {"status_code": status_code, "headers": headers}


def fetch_with_curl(feed_url: str, headers: Dict[str, str], timeout: int) -> Dict[str, Any]:
    """Fetch a feed via curl as a fallback for OpenSSL handshake failures."""
    curl_bin = shutil.which("curl")
    if not curl_bin:
        raise RuntimeError("curl is not installed")

    with tempfile.NamedTemporaryFile(delete=False) as body_file, tempfile.NamedTemporaryFile(delete=False) as header_file:
        body_path = body_file.name
        header_path = header_file.name

    cmd = [
        curl_bin,
        "--silent",
        "--show-error",
        "--location",
        "--max-time",
        str(timeout),
        "--output",
        body_path,
        "--dump-header",
        header_path,
        "--user-agent",
        headers.get("User-Agent", "FinPolGovNews/1.0"),
    ]

    for key, value in headers.items():
        if key.lower() == "user-agent":
            continue
        cmd.extend(["--header", f"{key}: {value}"])

    cmd.append(feed_url)

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            stderr = (result.stderr or "").strip()
            raise RuntimeError(stderr or f"curl exited with code {result.returncode}")

        with open(header_path, "r", encoding="utf-8", errors="replace") as f:
            header_data = f.read()
        header_info = parse_curl_headers(header_data)

        with open(body_path, "rb") as f:
            body = f.read()

        return {
            "status_code": header_info["status_code"],
            "headers": header_info["headers"],
            "content": body,
            "url": feed_url,
        }
    finally:
        for path_name in (body_path, header_path):
            try:
                os.unlink(path_name)
            except OSError:
                pass


def extract_cdata(text: str) -> str:
    """Extract content from CDATA sections."""
    m = re.search(r"<!\[CDATA\[(.*?)\]\]>", text, re.DOTALL)
    return m.group(1) if m else text


def strip_tags(html: str) -> str:
    """Remove HTML tags from text."""
    return re.sub(r"<[^>]+>", "", html).strip()


def get_tag(xml: str, tag: str) -> str:
    """Extract content from XML tag using regex with namespace support."""
    # Try with namespace first
    patterns = [
        rf"<{tag}[^>]*>(.*?)</{tag}>",  # No namespace
        rf"<[\w-]+:{tag}[^>]*>(.*?)</[\w-]+:{tag}>",  # With namespace
    ]
    for pattern in patterns:
        m = re.search(pattern, xml, re.DOTALL | re.IGNORECASE)
        if m:
            return extract_cdata(m.group(1)).strip()
    return ""


def validate_article_domain(article_link: str, source: Dict[str, Any]) -> bool:
    """Validate that article links from mirror sources point to expected domains.

    Sources with 'expected_domains' field will have their article links checked.
    Returns True if valid or if no domain restriction is set.
    """
    expected = source.get("expected_domains")
    if not expected:
        return True
    if not article_link:
        return False
    domain = urlparse(article_link).hostname or ""
    return any(domain == d or domain.endswith("." + d) for d in expected)


def resolve_link(link: str, base_url: str) -> str:
    """Resolve relative links against the feed URL. Rejects non-HTTP(S) schemes."""
    if not link:
        return link
    if link.startswith(("http://", "https://")):
        return link
    resolved = urljoin(base_url, link)
    if not resolved.startswith(("http://", "https://")):
        return ""  # reject javascript:, data:, etc.
    return resolved


def parse_date_fallback(date_str: str) -> Optional[datetime]:
    """Parse date string using multiple format patterns (fallback method)."""
    if not date_str:
        return None

    date_str = date_str.strip()

    # Try email.utils parsedate first (RFC 2822)
    try:
        return parsedate_to_datetime(date_str)
    except (TypeError, ValueError, IndexError):
        pass

    # Common date formats
    formats = [
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
    ]

    for fmt in formats:
        try:
            dt = datetime.strptime(date_str, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            continue

    # ISO 8601 fallback
    try:
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        return dt
    except ValueError:
        pass

    return None


# RSS Cache management
_rss_cache: Optional[Dict[str, Any]] = None
_rss_cache_dirty = False
_rss_cache_lock = threading.RLock()


def _load_rss_cache() -> Dict[str, Any]:
    """Load RSS ETag/Last-Modified cache."""
    try:
        with open(RSS_CACHE_PATH, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save_rss_cache(cache: Dict[str, Any]) -> None:
    """Save RSS ETag/Last-Modified cache."""
    try:
        with open(RSS_CACHE_PATH, 'w') as f:
            json.dump(cache, f)
    except Exception as e:
        logging.warning(f"Failed to save RSS cache: {e}")


def _get_rss_cache(no_cache: bool = False) -> Dict[str, Any]:
    global _rss_cache
    with _rss_cache_lock:
        if _rss_cache is None:
            _rss_cache = {} if no_cache else _load_rss_cache()
        return _rss_cache


def _flush_rss_cache() -> None:
    global _rss_cache, _rss_cache_dirty
    with _rss_cache_lock:
        if _rss_cache_dirty and _rss_cache is not None:
            _save_rss_cache(_rss_cache)
            _rss_cache_dirty = False


def fetch_feed(source: Dict[str, Any], hours: int, retries: int = RETRY_COUNT, timeout: int = TIMEOUT,
               no_cache: bool = False) -> Dict[str, Any]:
    """Fetch single RSS feed with requests library."""
    feed_url = source['url']
    source_id = source.get('id', 'unknown')
    source_name = source.get('name', 'Unknown')
    priority = source.get('priority', False)
    topics = source.get('topics', [])

    session = requests.Session()
    session.mount('https://', SSLAdapter())
    session.mount('http://', SSLAdapter())

    articles = []
    success = False
    error_msg = ""
    not_modified = False
    final_url = feed_url

    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)

    for attempt in range(retries):
        try:
            req_headers = {"User-Agent": "FinPolGovNews/1.0"}

            # Add conditional headers from cache (thread-safe)
            cache = _get_rss_cache(no_cache)
            cache_entry = cache.get(feed_url)
            now = time.time()
            ttl_seconds = RSS_CACHE_TTL_HOURS * 3600

            if cache_entry and not no_cache and (now - cache_entry.get("ts", 0)) < ttl_seconds:
                if cache_entry.get("etag"):
                    req_headers["If-None-Match"] = cache_entry["etag"]
                if cache_entry.get("last_modified"):
                    req_headers["If-Modified-Since"] = cache_entry["last_modified"]

            try:
                response = session.get(feed_url, headers=req_headers, timeout=timeout)
                response_data = {
                    "status_code": response.status_code,
                    "headers": response.headers,
                    "content": response.content,
                    "url": response.url,
                }
            except requests.exceptions.SSLError as e:
                if not should_retry_with_curl(e):
                    raise
                logging.debug(f"Retrying {source_name} with curl fallback after SSL error: {e}")
                response_data = fetch_with_curl(feed_url, req_headers, timeout)

            # Handle 304 Not Modified
            if response_data["status_code"] == 304:
                logging.info(f"鈴?{source_name}: not modified (304)")
                return {
                    "source_id": source_id,
                    "source_type": "rss",
                    "name": source_name,
                    "url": feed_url,
                    "priority": priority,
                    "topics": topics,
                    "status": "ok",
                    "attempts": attempt + 1,
                    "not_modified": True,
                    "count": 0,
                    "articles": [],
                }

            if response_data["status_code"] >= 400:
                raise requests.HTTPError(f"HTTP {response_data['status_code']} for {feed_url}")

            final_url = response_data["url"]

            # Update cache with response headers (thread-safe)
            global _rss_cache, _rss_cache_dirty
            etag = response_data["headers"].get("ETag") or response_data["headers"].get("Etag")
            last_mod = response_data["headers"].get("Last-Modified")
            if etag or last_mod:
                with _rss_cache_lock:
                    if _rss_cache is None:
                        _rss_cache = {}
                    _rss_cache[feed_url] = {"etag": etag, "last_modified": last_mod, "ts": now}
                    _rss_cache_dirty = True

            raw_content = response_data["content"]
            text_content = raw_content.decode("utf-8", errors="replace")

            if HAS_FEEDPARSER:
                feed = feedparser.parse(raw_content)
                if feed.bozo and feed.feed.get('bozo_exception'):
                    # Some feeds have recoverable parse errors, continue if we got entries
                    if not feed.entries:
                        error_msg = f"Bozo feed: {feed.bozo_exception}"
                        continue

                for entry in feed.entries[:MAX_ARTICLES_PER_FEED]:
                    try:
                        # Parse published date - skip if unparseable
                        published = None
                        date_fields = [
                            (entry, 'published_parsed'),
                            (entry, 'updated_parsed'),
                        ]

                        for obj, field in date_fields:
                            if hasattr(obj, field) and getattr(obj, field):
                                try:
                                    published = datetime(*getattr(obj, field)[:6], tzinfo=timezone.utc)
                                    break
                                except (TypeError, ValueError, IndexError):
                                    continue

                        # Fallback to string parsing
                        if published is None:
                            for date_field in ['published', 'updated']:
                                if hasattr(entry, date_field) and getattr(entry, date_field):
                                    published = parse_date_fallback(getattr(entry, date_field))
                                    if published:
                                        break

                        # Skip article if date cannot be parsed or is too old
                        if published is None or published < cutoff:
                            continue

                        # Extract title and link
                        title = entry.get('title', '').strip()[:200]
                        link = entry.get('link', '').strip()

                        # Resolve relative links
                        link = resolve_link(link, final_url)

                        if not title or not link:
                            continue

                        # Validate domain if expected_domains is set
                        if not validate_article_domain(link, source):
                            logging.warning(f"鈿狅笍 {source_name}: rejected article with unexpected domain: {link}")
                            continue

                        # Extract content
                        content = ""
                        if hasattr(entry, 'content') and entry.content:
                            content = entry.content[0].get('value', '')
                        elif hasattr(entry, 'summary') and entry.summary:
                            content = entry.summary

                        article = {
                            'title': title,
                            'link': link,
                            'published': published.isoformat(),
                            'source': source_name,
                            'source_id': source_id,
                            'source_type': 'rss',
                            'content': content,
                            'topics': topics[:],  # Copy to avoid mutation
                        }
                        articles.append(article)
                    except Exception as e:
                        logging.debug(f"Error processing entry: {e}")
                        continue
            else:
                # Fallback to regex parsing with better support
                content = text_content

                # RSS 2.0 items
                for item in re.finditer(r"<item[^>]*>(.*?)</item>", content, re.DOTALL):
                    title = strip_tags(get_tag(item.group(1), "title"))[:200]
                    link = resolve_link(get_tag(item.group(1), "link"), final_url)
                    date_str = get_tag(item.group(1), "pubDate") or get_tag(item.group(1), "dc:date")
                    pub_date = parse_date_fallback(date_str)

                    if title and link and pub_date and pub_date >= cutoff:
                        if validate_article_domain(link, source):
                            articles.append({
                                'title': title,
                                'link': link,
                                'published': pub_date.isoformat(),
                                'source': source_name,
                                'source_id': source_id,
                                'source_type': 'rss',
                                'content': '',
                                'topics': topics[:],
                            })

                # Atom entries fallback
                if not articles:
                    for entry in re.finditer(r"<entry[^>]*>(.*?)</entry>", content, re.DOTALL):
                        block = entry.group(1)
                        title = strip_tags(get_tag(block, "title"))[:200]

                        # Find link with href attribute
                        link_match = re.search(r'<link[^>]*href=["\']([^"\']+)["\']', block)
                        if link_match:
                            link = link_match.group(1)
                        else:
                            link = get_tag(block, "link")

                        link = resolve_link(link, final_url)
                        date_str = get_tag(block, "updated") or get_tag(block, "published")
                        pub_date = parse_date_fallback(date_str)

                        if title and link and pub_date and pub_date >= cutoff:
                            if validate_article_domain(link, source):
                                articles.append({
                                    'title': title,
                                    'link': link,
                                    'published': pub_date.isoformat(),
                                    'source': source_name,
                                    'source_id': source_id,
                                    'source_type': 'rss',
                                    'content': '',
                                    'topics': topics[:],
                                })

                articles = articles[:MAX_ARTICLES_PER_FEED]

            success = True
            break

        except requests.RequestException as e:
            error_msg = str(e)[:200]
            logging.debug(f"Attempt {attempt + 1} failed for {source_name}: {error_msg}")
            if attempt < retries - 1:
                time.sleep(RETRY_DELAY * (2 ** attempt))
            continue
        except Exception as e:
            error_msg = str(e)[:200]
            logging.debug(f"Unexpected error for {source_name}: {error_msg}")
            if attempt < retries - 1:
                time.sleep(RETRY_DELAY * (2 ** attempt))
            continue

    return {
        "source_id": source_id,
        "source_type": "rss",
        "name": source_name,
        "url": feed_url,
        "priority": priority,
        "topics": topics,
        "status": "ok" if success else "error",
        "attempts": retries if not success else attempt + 1,
        "not_modified": not_modified,
        "count": len(articles),
        "articles": articles,
        "error": error_msg if not success else None,
    }


def load_sources(defaults_dir: Path, config_dir: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Load RSS sources from unified configuration with overlay support."""
    try:
        from config_loader import load_merged_sources
    except ImportError:
        sys.path.append(str(Path(__file__).parent))
        from config_loader import load_merged_sources

    all_sources = load_merged_sources(defaults_dir, config_dir)

    rss_sources = []
    for source in all_sources:
        if source.get("type") == "rss" and source.get("enabled", True):
            rss_sources.append(source)

    logging.info(f"Loaded {len(rss_sources)} enabled RSS sources")
    return rss_sources


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Parallel RSS/Atom feed fetcher for fin-pol-gov-news.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--defaults",
        type=Path,
        default=Path("config/defaults"),
        help="Default configuration directory (default: config/defaults)"
    )

    parser.add_argument(
        "--config",
        type=Path,
        help="User configuration directory for overlays (optional)"
    )

    parser.add_argument(
        "--hours",
        type=int,
        default=48,
        help="Time window in hours for articles (default: 48)"
    )

    parser.add_argument(
        "--output", "-o",
        type=Path,
        help="Output JSON path (default: auto-generated temp file)"
    )

    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )

    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Bypass ETag/Last-Modified conditional request cache"
    )

    parser.add_argument(
        "--force",
        action="store_true",
        help="Force re-fetch even if cached output exists"
    )

    args = parser.parse_args()
    logger = setup_logging(args.verbose)

    # Resume support: skip if output exists, is valid JSON, and < 1 hour old
    if args.output and args.output.exists() and not args.force:
        try:
            age_seconds = time.time() - args.output.stat().st_mtime
            if age_seconds < 3600:
                with open(args.output, 'r') as f:
                    json.load(f)
                logger.info(f"Skipping (cached output exists): {args.output}")
                return 0
        except (json.JSONDecodeError, OSError):
            pass

    # Auto-generate unique output path if not specified
    if not args.output:
        fd, temp_path = tempfile.mkstemp(prefix="fin-pol-gov-news-rss-", suffix=".json")
        os.close(fd)
        args.output = Path(temp_path)

    try:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=args.hours)

        # Backward compatibility
        if args.config and args.defaults == Path("config/defaults") and not args.defaults.exists():
            logger.debug("Backward compatibility mode: using --config as sole source")
            sources = load_sources(args.config, None)
        else:
            sources = load_sources(args.defaults, args.config)

        if not sources:
            logger.warning("No RSS sources found or all disabled")

        logger.info(f"Fetching {len(sources)} RSS feeds (window: {args.hours}h)")

        if HAS_FEEDPARSER:
            logger.debug("Using feedparser library for parsing")
        else:
            logger.info("feedparser not available, using regex parsing")

        # Initialize cache
        _get_rss_cache(no_cache=args.no_cache)

        results = []
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
            futures = {pool.submit(fetch_feed, source, args.hours, RETRY_COUNT, TIMEOUT, args.no_cache): source
                      for source in sources}

            for future in as_completed(futures):
                result = future.result()
                results.append(result)

                if result["status"] == "ok":
                    if result.get("not_modified"):
                        logger.debug(f"鈴?{result['name']}: not modified")
                    else:
                        logger.debug(f"鉁?{result['name']}: {result['count']} articles")
                else:
                    logger.debug(f"鉂?{result['name']}: {result.get('error', 'unknown error')}")

        # Flush conditional request cache
        _flush_rss_cache()

        # Sort: priority first, then by article count
        results.sort(key=lambda x: (not x.get("priority", False), -x.get("count", 0)))

        ok_count = sum(1 for r in results if r["status"] == "ok")
        total_articles = sum(r.get("count", 0) for r in results)

        output = {
            "generated": datetime.now(timezone.utc).isoformat(),
            "source_type": "rss",
            "defaults_dir": str(args.defaults),
            "config_dir": str(args.config) if args.config else None,
            "hours": args.hours,
            "feedparser_available": HAS_FEEDPARSER,
            "sources_total": len(results),
            "sources_ok": ok_count,
            "total_articles": total_articles,
            "sources": results,
        }

        # Write output
        json_str = json.dumps(output, ensure_ascii=False, indent=2)
        with open(args.output, "w", encoding='utf-8') as f:
            f.write(json_str)

        logger.info(f"鉁?Done: {ok_count}/{len(results)} feeds ok, "
                   f"{total_articles} articles 鈫?{args.output}")

        return 0

    except Exception as e:
        logger.error(f"馃挜 RSS fetch failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())


