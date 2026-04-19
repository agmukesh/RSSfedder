"""Pure article-processing helpers used by the feed-fetch pipeline.

Provides `analyze_sentiment` (VADER, compound score thresholded at ±0.05,
normalized to 0-1), `categorize_article` (returns the feed's declared
category), `fetch_article_content` (BeautifulSoup HTML scrape that strips
script/style/nav/footer, 10s timeout, no length cap), `fetch_full_content`
(HTML/PDF dispatcher that routes to `pdf_utils.extract_pdf_text` or the HTML
scraper and runs the result through `text_cleaner.clean_article_text`), and
`summarize_article` (first N cleaned sentences). No DB access here.
"""

import logging
import re
import requests
from bs4 import BeautifulSoup
from config import analyzer
from pdf_utils import is_pdf_url, extract_pdf_text
from text_cleaner import clean_article_text

logger = logging.getLogger(__name__)

SCRAPE_USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
SCRAPE_TIMEOUT = 10

NON_WEB_EXTENSIONS = (
    '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
    '.zip', '.rar', '.7z', '.tar', '.gz',
    '.mp3', '.mp4', '.mov', '.avi', '.wav', '.m4a', '.ogg',
    '.jpg', '.jpeg', '.png', '.gif', '.svg', '.webp', '.bmp',
    '.exe', '.dmg', '.iso', '.apk',
)


def categorize_article(title, feed_category='Other'):
    """Use the feed's declared category as-is."""
    return feed_category


def analyze_sentiment(text):
    """Analyze sentiment of text using VADER."""
    if not text:
        return 'neutral', 0.5
    try:
        scores = analyzer.polarity_scores(text)
        compound = scores['compound']

        if compound >= 0.05:
            sentiment_label = 'positive'
        elif compound <= -0.05:
            sentiment_label = 'negative'
        else:
            sentiment_label = 'neutral'

        normalized_score = (compound + 1) / 2
        return sentiment_label, normalized_score
    except Exception:
        logger.exception("Sentiment analysis failed")
        return 'neutral', 0.5


def fetch_article_content(article_url):
    """Fetch full article text from an HTML URL. Returns None on failure."""
    try:
        headers = {'User-Agent': SCRAPE_USER_AGENT}
        response = requests.get(article_url, headers=headers, timeout=SCRAPE_TIMEOUT)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, 'html.parser')
        for el in soup(['script', 'style', 'nav', 'footer', 'aside', 'header', 'form', 'iframe']):
            el.decompose()

        text = soup.get_text(separator='\n', strip=True)
        return text or None
    except Exception:
        logger.exception("HTML scrape failed for %s", article_url)
        return None


def fetch_full_content(url):
    """Dispatch to PDF or HTML fetcher, then clean. HTML and PDF only — other types return None."""
    if not url or url.startswith('synthetic:'):
        return None
    if is_pdf_url(url):
        raw = extract_pdf_text(url)
    else:
        path = url.lower().split('?')[0].split('#')[0]
        if any(path.endswith(ext) for ext in NON_WEB_EXTENSIONS):
            logger.info("skip non-web content: %s", url)
            return None
        raw = fetch_article_content(url)
    if not raw:
        return None
    cleaned = clean_article_text(raw)
    logger.info("fetch_full_content: url=%s raw=%d cleaned=%d",
                url, len(raw), len(cleaned) if cleaned else 0)
    return cleaned


def summarize_article(text, sentences=3):
    """Summarize article using first-N-sentences heuristic."""
    try:
        if not text or len(text.split()) < 50:
            return None

        sentence_list = [s.strip() for s in re.split(r'(?<=[.!?])\s+', text.strip()) if s.strip()]
        if not sentence_list:
            return None

        summary_text = " ".join(sentence_list[:sentences])
        return summary_text if summary_text else None
    except Exception:
        logger.exception("Summarization failed")
        return None
