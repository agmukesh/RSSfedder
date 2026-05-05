"""RSS feed fetch pipeline and background scheduler.

`fetch_and_store_articles` iterates every row in the `feeds` table, parses
each feed with feedparser, fetches and cleans the full article body
via `fetch_full_content` (HTML or PDF), runs sentiment on the title, and
inserts via `INSERT OR IGNORE` keyed on the article `link`. Summarization is
NOT done here — it happens on demand via `/api/summarize`. Fetches run in a
background thread guarded by `_fetch_lock` / `_fetch_in_progress`;
`start_periodic_fetch` and `trigger_background_fetch` are the public entry
points called from `app.py` and `auth.py` respectively.
"""

import sqlite3
import threading
import time
import os
import hashlib
import logging
import feedparser
import requests
from config import DB_FILE
from db import cleanup_old_articles
from articles import analyze_sentiment, categorize_article, fetch_full_content

logger = logging.getLogger(__name__)

FEED_USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'

_fetch_lock = threading.Lock()
_fetch_in_progress = False


def _background_fetch():
    """Run fetch_and_store_articles in background, updating state flag."""
    global _fetch_in_progress
    try:
        fetch_and_store_articles()
    finally:
        with _fetch_lock:
            _fetch_in_progress = False


def trigger_background_fetch():
    """Start a background fetch if one is not already running."""
    global _fetch_in_progress
    with _fetch_lock:
        if _fetch_in_progress:
            return False
        _fetch_in_progress = True
    t = threading.Thread(target=_background_fetch, daemon=True)
    t.start()
    return True


def is_fetch_in_progress():
    """Check if a background fetch is currently running."""
    with _fetch_lock:
        return _fetch_in_progress


def _parse_feed(rss_url):
    """Fetch and parse one RSS URL."""
    try:
        resp = requests.get(rss_url, headers={'User-Agent': FEED_USER_AGENT}, timeout=15)
        resp.raise_for_status()
        return feedparser.parse(resp.content)
    except Exception:
        logger.exception("Failed to fetch feed: %s", rss_url)
        return feedparser.parse(b"")


def _resolve_link(entry, provider, title, published):
    """Return (link, synthesized). Synthesizes a stable key when the entry has no URL."""
    link = entry.get('link') or entry.get('id') or entry.get('guid')
    if link:
        return link, False
    basis = f"{provider}|{title}|{published}"
    digest = hashlib.sha1(basis.encode('utf-8')).hexdigest()[:16]
    return f"synthetic:{provider}:{digest}", True


def _build_article_record(entry, provider, feed_category):
    """Turn a feedparser entry into the DB insert tuple. Returns (record, synthesized)."""
    title = entry.title if isinstance(entry.title, str) else str(entry.title)
    published = entry.get('published', 'N/A')
    link, synthesized = _resolve_link(entry, provider, title, published)
    sentiment, score = analyze_sentiment(title)
    category = categorize_article(title, feed_category)
    content = fetch_full_content(link)
    record = (provider, title, link, published, content, None, sentiment, score, category)
    return record, synthesized


def _insert_article(cursor, record):
    """INSERT OR IGNORE one article row. Returns True if a new row was inserted."""
    cursor.execute('''INSERT OR IGNORE INTO articles
                       (provider, title, link, published, content, summary, sentiment, sentiment_score, category)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''', record)
    return cursor.rowcount > 0


def _process_feed(conn, feed_row):
    """Parse one feed row and ingest its entries, committing per-row and printing a summary."""
    provider = feed_row['name']
    rss_url = feed_row['url']
    feed_category = feed_row['category']
    feed = None
    try:
        logger.info("Starting fetch for: %s", rss_url)
        feed = _parse_feed(rss_url)
        cursor = conn.cursor()
        seen = len(feed.entries)
        inserted = synthesized = errs = 0
        for entry in feed.entries:
            try:
                logger.info("Processing: %s", entry.get('title'))
                record, was_synth = _build_article_record(entry, provider, feed_category)
                if was_synth:
                    synthesized += 1
                if _insert_article(cursor, record):
                    inserted += 1
                    logger.info("Inserted: %s", record[2])
                conn.commit()
            except sqlite3.IntegrityError:
                pass
            except Exception:
                errs += 1
                logger.exception("Error processing article from %s", provider)
        logger.info("[%s] entries=%d inserted=%d synthesized_link=%d errors=%d",
                    provider, seen, inserted, synthesized, errs)
    except Exception:
        entries_count = len(getattr(feed, 'entries', [])) if feed is not None else 0
        bozo = getattr(feed, 'bozo', None) if feed is not None else None
        logger.error("Failed to fetch: %s", rss_url)
        logger.exception("Error fetching %s (entries=%s bozo=%s)", provider, entries_count, bozo)


def fetch_and_store_articles():
    """Fetch from all active RSS feeds, analyze sentiment, categorize, and store."""
    cleanup_old_articles()
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    try:
        feeds = conn.execute('SELECT * FROM feeds WHERE enabled = 1').fetchall()
        for feed_row in feeds:
            _process_feed(conn, feed_row)
    finally:
        conn.close()


def start_periodic_fetch():
    """Start periodic feed refresh if configured via FEED_REFRESH_INTERVAL_MINUTES."""
    interval = int(os.environ.get('FEED_REFRESH_INTERVAL_MINUTES', '0'))
    if interval <= 0:
        return

    def _periodic():
        while True:
            time.sleep(interval * 60)
            trigger_background_fetch()

    t = threading.Thread(target=_periodic, daemon=True)
    t.start()
