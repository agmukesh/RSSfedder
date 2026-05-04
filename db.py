"""SQLite schema, seed helpers, and query helpers for the app.

Creates and owns the `articles`, `users` (bcrypt password hashes + reset
tokens), `feeds` (default + per-user, unique on (url, added_by)), and
`bookmarks` tables. Provides helpers for reading/writing each table, seeding
the default user and feed list, cleaning up old articles, and mapping DB rows
to the article dict shape expected by templates (note: DB column `provider`
is exposed as dict key `source`).
"""

import sqlite3
import os
import bcrypt
from config import DB_FILE, DEFAULT_FEEDS


def init_db():
    """Initialize database schema."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS articles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        provider TEXT NOT NULL,
        title TEXT NOT NULL,
        link TEXT UNIQUE NOT NULL,
        published TEXT,
        content TEXT,
        summary TEXT,
        sentiment TEXT,
        sentiment_score REAL,
        category TEXT DEFAULT 'Other',
        fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        reset_token TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS feeds (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        url TEXT NOT NULL,
        category TEXT NOT NULL DEFAULT 'Other',
        is_default INTEGER DEFAULT 0,
        added_by TEXT,
        enabled INTEGER DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(url, added_by)
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS bookmarks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL,
        article_id INTEGER NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(username, article_id),
        FOREIGN KEY (article_id) REFERENCES articles(id) ON DELETE CASCADE
    )''')
    # Add category column if missing (migration for existing DBs)
    c.execute("PRAGMA table_info(articles)")
    article_cols = [row[1] for row in c.fetchall()]
    if 'category' not in article_cols:
        c.execute('ALTER TABLE articles ADD COLUMN category TEXT DEFAULT "Other"')

    c.execute("PRAGMA table_info(feeds)")
    feed_cols = [row[1] for row in c.fetchall()]
    if 'enabled' not in feed_cols:
        c.execute('ALTER TABLE feeds ADD COLUMN enabled INTEGER DEFAULT 1')

    conn.commit()
    conn.close()


def seed_default_feeds():
    """Seed default RSS feeds if none exist."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM feeds WHERE is_default = 1')
    if c.fetchone()[0] == 0:
        for name, url, category in DEFAULT_FEEDS:
            c.execute('INSERT OR IGNORE INTO feeds (name, url, category, is_default) VALUES (?, ?, ?, 1)',
                      (name, url, category))
    conn.commit()
    conn.close()


def seed_default_user():
    """Create default admin user if no users exist."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM users')
    if c.fetchone()[0] == 0:
        username = os.environ.get('DEFAULT_USERNAME', 'admin')
        password = os.environ.get('DEFAULT_PASSWORD', 'changeme')
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        try:
            c.execute('INSERT INTO users (username, password_hash) VALUES (?, ?)',
                      (username, password_hash))
            conn.commit()
        except sqlite3.IntegrityError:
            pass
    conn.close()


# User helpers

def hash_password(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def check_password(password, password_hash):
    return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))


def create_user(username, password):
    """Create a new user. Returns True on success, False if username exists."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    try:
        c.execute('INSERT INTO users (username, password_hash) VALUES (?, ?)',
                  (username, hash_password(password)))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


def get_user(username):
    """Get user by username."""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE username = ?', (username,))
    user = c.fetchone()
    conn.close()
    return user


# Feed helpers

def get_active_feeds(username=None):
    """Get all feeds: defaults + user-added feeds for the given user."""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('SELECT * FROM feeds WHERE is_default = 1 OR added_by = ? ORDER BY category, name',
              (username,))
    feeds = c.fetchall()
    conn.close()
    return feeds


# Article query helpers

def _row_to_article(row):
    return {
        'id': row['id'],
        'source': row['provider'],
        'title': row['title'],
        'link': row['link'],
        'published': row['published'],
        'content': row['content'],
        'summary': row['summary'],
        'sentiment': row['sentiment'],
        'sentiment_score': row['sentiment_score'],
        'category': row['category'] if 'category' in row.keys() else 'Other',
    }


def cleanup_old_articles():
    """Delete articles older than 24 hours."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('DELETE FROM articles WHERE fetched_at < datetime("now", "-1 day")')
    conn.commit()
    conn.close()


def get_article_by_id(article_id):
    """Return an article dict by id, or None if not found."""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    row = conn.execute('SELECT * FROM articles WHERE id = ?', (article_id,)).fetchone()
    conn.close()
    return _row_to_article(row) if row else None


def update_article_summary(article_id, summary):
    """Persist a newly-computed summary for an article row."""
    conn = sqlite3.connect(DB_FILE)
    conn.execute('UPDATE articles SET summary = ? WHERE id = ?', (summary, article_id))
    conn.commit()
    conn.close()


def get_articles_by_provider(provider, page=1, per_page=10):
    """Get paginated articles from database for a provider."""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('SELECT * FROM articles WHERE provider = ? ORDER BY fetched_at DESC', (provider,))
    all_articles = c.fetchall()
    total = len(all_articles)
    start = (page - 1) * per_page
    articles = [_row_to_article(r) for r in all_articles[start:start + per_page]]
    conn.close()
    return articles, total


def get_all_articles(page=1, per_page=10, category=None, source=None):
    """Get all articles, optionally filtered by category and/or source."""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    query = 'SELECT * FROM articles'
    conditions = []
    params = []
    if category:
        conditions.append('category = ?')
        params.append(category)
    if source:
        conditions.append('provider = ?')
        params.append(source)
    if conditions:
        query += ' WHERE ' + ' AND '.join(conditions)
    query += ' ORDER BY fetched_at DESC'
    c.execute(query, params)
    all_articles = c.fetchall()
    total = len(all_articles)
    start = (page - 1) * per_page
    articles = [_row_to_article(r) for r in all_articles[start:start + per_page]]
    conn.close()
    return articles, total


def get_sources(category=None, username=None):
    """Get all feed source names, optionally filtered by category. Includes feeds with no articles yet."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    if category:
        c.execute('''SELECT DISTINCT name FROM feeds
                     WHERE category = ? AND (is_default = 1 OR added_by = ?)
                     ORDER BY name''', (category, username))
    else:
        c.execute('''SELECT DISTINCT name FROM feeds
                     WHERE is_default = 1 OR added_by = ?
                     ORDER BY name''', (username,))
    sources = [row[0] for row in c.fetchall()]
    conn.close()
    return sources


def get_sentiment_stats(provider=None):
    """Get sentiment statistics."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    if provider:
        c.execute('SELECT sentiment FROM articles WHERE provider = ?', (provider,))
    else:
        c.execute('SELECT sentiment FROM articles')
    sentiments = [row[0] for row in c.fetchall()]
    conn.close()

    total = len(sentiments)
    if total == 0:
        return {'positive': 0, 'negative': 0, 'neutral': 0, 'positive_pct': 0, 'negative_pct': 0, 'neutral_pct': 0}

    positive = sentiments.count('positive')
    negative = sentiments.count('negative')
    neutral = sentiments.count('neutral')

    return {
        'positive': positive,
        'negative': negative,
        'neutral': neutral,
        'positive_pct': (positive / total) * 100,
        'negative_pct': (negative / total) * 100,
        'neutral_pct': (neutral / total) * 100
    }
