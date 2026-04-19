"""Application configuration and shared constants.

Loads environment variables from `.env`, exposes `DB_FILE`, the list of
`CATEGORIES`, the `DEFAULT_FEEDS` seed list, the `CATEGORY_KEYWORDS` map used
for auto-categorization, and the shared VADER `analyzer` instance. Also
contains a compatibility shim that restores `collections.Sequence` / `Iterable`
/ `Mapping` on Python 3.10+ so older `sumy` imports keep working.
"""

import os
import collections
import collections.abc
from dotenv import load_dotenv

load_dotenv()

# Compatibility shim for old sumy versions that import collections.Sequence from collections
if not hasattr(collections, 'Sequence'):
    collections.Sequence = collections.abc.Sequence
if not hasattr(collections, 'Iterable'):
    collections.Iterable = collections.abc.Iterable
if not hasattr(collections, 'Mapping'):
    collections.Mapping = collections.abc.Mapping

from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

# Database configuration
DB_FILE = os.environ.get('DB_FILE', 'feeds.db')

# Sentiment analyzer
analyzer = SentimentIntensityAnalyzer()

CATEGORIES = ['Finance', 'Technology', 'Entertainment', 'Education', 'Sports', 'Science', 'World News', 'Other']

DEFAULT_FEEDS = [
    # Finance
    ('Yahoo Finance', 'https://finance.yahoo.com/news/rssindex', 'Finance'),
    ('CNBCTV 18', 'https://www.cnbctv18.com/market/rssfeed.xml', 'Finance'),
    ('Money Control', 'https://www.moneycontrol.com/news/rss/markets.xml', 'Finance'),
    ('Economic Times', 'https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms', 'Finance'),
    ('Business Standard', 'https://www.business-standard.com/rss/home_page_top_stories.rss', 'Finance'),
    ('Livemint', 'https://www.livemint.com/rss/news', 'Finance'),
    # Technology
    ('TechCrunch', 'https://techcrunch.com/feed/', 'Technology'),
    ('The Verge', 'https://www.theverge.com/rss/index.xml', 'Technology'),
    ('Ars Technica', 'https://feeds.arstechnica.com/arstechnica/index', 'Technology'),
    ('Wired', 'https://www.wired.com/feed/rss', 'Technology'),
    # Entertainment
    ('Entertainment Weekly', 'https://ew.com/feed/', 'Entertainment'),
    ('Variety', 'https://variety.com/feed/', 'Entertainment'),
    ('Hollywood Reporter', 'https://www.hollywoodreporter.com/feed/', 'Entertainment'),
    # Education
    ('EdSurge', 'https://www.edsurge.com/articles_rss', 'Education'),
    ('Inside Higher Ed', 'https://www.insidehighered.com/rss/feed', 'Education'),
    ('Education Week', 'https://www.edweek.org/feed', 'Education'),
    # Sports
    ('ESPN', 'https://www.espn.com/espn/rss/news', 'Sports'),
    ('BBC Sport', 'https://feeds.bbci.co.uk/sport/rss.xml', 'Sports'),
    ('Sky Sports', 'https://www.skysports.com/rss/12040', 'Sports'),
    # Science
    ('Nature News', 'https://www.nature.com/nature.rss', 'Science'),
    ('Science Daily', 'https://www.sciencedaily.com/rss/all.xml', 'Science'),
    ('New Scientist', 'https://www.newscientist.com/feed/home/', 'Science'),
    # World News
    ('BBC News', 'https://feeds.bbci.co.uk/news/world/rss.xml', 'World News'),
    ('Reuters', 'https://www.reutersagency.com/feed/', 'World News'),
    ('Al Jazeera', 'https://www.aljazeera.com/xml/rss/all.xml', 'World News'),
]

# Keyword map for auto-categorizing articles
CATEGORY_KEYWORDS = {
    'Finance': ['stock', 'market', 'trading', 'invest', 'bank', 'finance', 'economy', 'gdp', 'inflation',
                'crypto', 'bitcoin', 'nifty', 'sensex', 'forex', 'commodity', 'bond', 'ipo', 'dividend',
                'revenue', 'profit', 'earnings', 'fund', 'portfolio', 'fiscal', 'monetary'],
    'Technology': ['tech', 'software', 'ai', 'artificial intelligence', 'startup', 'app', 'cyber', 'cloud',
                   'data', 'algorithm', 'robot', 'chip', 'semiconductor', 'internet', 'digital', 'code',
                   'programming', 'machine learning', 'blockchain', 'saas', 'api'],
    'Entertainment': ['movie', 'film', 'music', 'celebrity', 'hollywood', 'bollywood', 'album', 'concert',
                      'streaming', 'netflix', 'disney', 'actor', 'actress', 'box office', 'tv show',
                      'series', 'entertainment', 'award', 'grammy', 'oscar'],
    'Education': ['education', 'university', 'college', 'school', 'student', 'teacher', 'curriculum',
                  'exam', 'degree', 'scholarship', 'learning', 'academic', 'research', 'campus', 'course'],
    'Sports': ['sports', 'cricket', 'football', 'soccer', 'tennis', 'basketball', 'nba', 'nfl', 'ipl',
               'olympic', 'world cup', 'match', 'tournament', 'championship', 'league', 'goal', 'run',
               'wicket', 'athlete', 'medal', 'coach', 'fifa'],
    'Science': ['science', 'nasa', 'space', 'planet', 'climate', 'biology', 'physics', 'chemistry',
                'experiment', 'discovery', 'genome', 'quantum', 'evolution', 'vaccine', 'medicine',
                'health', 'disease', 'fossil', 'species', 'environment'],
    'World News': ['war', 'politics', 'election', 'government', 'diplomat', 'united nations', 'treaty',
                   'conflict', 'refugee', 'sanction', 'summit', 'parliament', 'prime minister', 'president'],
}
