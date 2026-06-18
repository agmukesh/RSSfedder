"""Main application routes (blueprint `main_bp`).

Pages: `/` (paginated, filterable by category + source), `/dashboard`,
`/feed/<provider>`, `/search`, `/bookmarks`, `/manage-feeds`. JSON APIs:
`/api/fetch-status` (polled by the UI to show the "updating…" banner) and
`/api/bookmark` (toggle). All routes require login. Note: several handlers
open their own `sqlite3.connect(DB_FILE)` rather than using `db.py` helpers —
both styles coexist intentionally.
"""

import logging
import sqlite3
from flask import Blueprint, request, redirect, url_for, session, flash, render_template, jsonify
from config import DB_FILE, CATEGORIES
from db import (get_active_feeds, get_all_articles, get_articles_by_provider,
                get_sentiment_stats, _row_to_article, get_sources,
                get_article_by_id, update_article_summary)
from feeds import is_fetch_in_progress
from auth import login_required
from articles import summarize_article

logger = logging.getLogger(__name__)

main_bp = Blueprint('main', __name__)


@main_bp.route("/", methods=['GET', 'POST'])
@login_required
def index():
    page = request.args.get('page', 1, type=int)
    category = request.args.get('category', '')
    source = request.args.get('source', '')
    articles, total_articles = get_all_articles(page=page, category=category or None, source=source or None)
    per_page = 10
    total_pages = (total_articles + per_page - 1) // per_page
    sources = get_sources(category=category or None, username=session['user'])
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('SELECT article_id FROM bookmarks WHERE username = ?', (session['user'],))
    bookmarked_ids = {row[0] for row in c.fetchall()}
    conn.close()
    return render_template('index.html', articles=articles, page=page, total_pages=total_pages,
                         categories=CATEGORIES, current_category=category, bookmarked_ids=bookmarked_ids,
                         sources=sources, current_source=source)


@main_bp.route('/search')
@login_required
def search():
    query = request.args.get('q', '')
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('SELECT * FROM articles WHERE title LIKE ? ORDER BY published DESC', ('%' + query + '%',))
    results = c.fetchall()
    conn.close()

    articles = []
    for row in results:
        articles.append({
            'source': row['provider'],
            'title': row['title'],
            'link': row['link'],
            'published': row['published'],
            'summary': row['summary'],
            'sentiment': row['sentiment']
        })
    return render_template('search.html', articles=articles, query=query)


@main_bp.route('/feed/<provider>')
@login_required
def feed(provider):
    feeds = get_active_feeds(session.get('user'))
    provider_names = [f['name'] for f in feeds]
    if provider not in provider_names:
        return render_template('feed.html', provider=provider, articles=[], error="Provider not found",
                             available_providers=provider_names, sentiment_stats={})
    page = request.args.get('page', 1, type=int)
    articles, total_articles = get_articles_by_provider(provider, page=page)
    per_page = 10
    total_pages = (total_articles + per_page - 1) // per_page
    if not articles:
        return render_template('feed.html', provider=provider, articles=[],
                             error="No articles available", available_providers=provider_names,
                             sentiment_stats={})
    sentiment_stats = get_sentiment_stats(provider)
    return render_template('feed.html', provider=provider, articles=articles, page=page,
                         total_pages=total_pages, error=None, available_providers=provider_names,
                         sentiment_stats=sentiment_stats)


@main_bp.route("/dashboard")
@login_required
def dashboard():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    feeds = get_active_feeds(session['user'])
    provider_names = [f['name'] for f in feeds]
    articles = []
    provider_counts = {}
    for name in provider_names:
        c.execute('SELECT COUNT(*) FROM articles WHERE provider = ?', (name,))
        provider_counts[name] = c.fetchone()[0]
        c.execute('SELECT * FROM articles WHERE provider = ? ORDER BY fetched_at DESC LIMIT 5', (name,))
        for row in c.fetchall():
            articles.append(_row_to_article(row))

    c.execute('SELECT COUNT(*) FROM articles')
    total_articles = c.fetchone()[0]
    c.execute('SELECT COUNT(*) FROM users')
    total_users = c.fetchone()[0]
    c.execute('SELECT category, COUNT(*) as cnt FROM articles GROUP BY category ORDER BY cnt DESC')
    category_counts = {row['category']: row['cnt'] for row in c.fetchall()}
    conn.close()

    articles.sort(key=lambda x: x['published'], reverse=True)
    sentiment_stats = get_sentiment_stats()

    return render_template('dashboard.html', user=session['user'], articles=articles,
                         sentiment_stats=sentiment_stats, provider_counts=provider_counts,
                         total_articles=total_articles, total_users=total_users,
                         providers=provider_names, categories=CATEGORIES,
                         category_counts=category_counts)


@main_bp.route("/api/fetch-status")
@login_required
def fetch_status():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM articles')
    count = c.fetchone()[0]
    conn.close()
    return jsonify({"fetching": is_fetch_in_progress(), "article_count": count})


@main_bp.route("/manage-feeds", methods=["GET", "POST"])
@login_required
def manage_feeds():
    username = session['user']
    if request.method == "POST":
        action = request.form.get("action")
        if action == "add":
            name = request.form.get("name", "").strip()
            url = request.form.get("url", "").strip()
            category = request.form.get("category", "Other")
            if not name or not url:
                flash("Feed name and URL are required.", "error")
            elif category not in CATEGORIES:
                flash("Invalid category.", "error")
            else:
                conn = sqlite3.connect(DB_FILE)
                c = conn.cursor()
                try:
                    c.execute('INSERT INTO feeds (name, url, category, is_default, added_by) VALUES (?, ?, ?, 0, ?)',
                              (name, url, category, username))
                    conn.commit()
                    flash(f"Feed '{name}' added successfully!", "success")
                except sqlite3.IntegrityError:
                    flash("You already have a feed with that URL.", "error")
                finally:
                    conn.close()
        elif action == "edit":
            feed_id = request.form.get("feed_id", type=int)
            name = request.form.get("name", "").strip()
            url = request.form.get("url", "").strip()
            category = request.form.get("category", "Other")
            if not name or not url:
                flash("Feed name and URL are required.", "error")
            elif category not in CATEGORIES:
                flash("Invalid category.", "error")
            else:
                conn = sqlite3.connect(DB_FILE)
                c = conn.cursor()
                c.execute('UPDATE feeds SET name = ?, url = ?, category = ? WHERE id = ? AND (added_by = ? OR is_default = 1)',
                          (name, url, category, feed_id, username))
                conn.commit()
                conn.close()
                flash("Feed updated.", "success")
        elif action == "delete":
            feed_id = request.form.get("feed_id", type=int)
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute('DELETE FROM feeds WHERE id = ? AND (added_by = ? OR is_default = 1)', (feed_id, username))
            conn.commit()
            conn.close()
            flash("Feed removed.", "success")
        elif action == "toggle":
            feed_id = request.form.get("feed_id", type=int)
            enabled = 1 if request.form.get("enabled") == "1" else 0
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute('UPDATE feeds SET enabled = ? WHERE id = ? AND (added_by = ? OR is_default = 1)',
                      (enabled, feed_id, username))
            if not enabled:
                c.execute('SELECT name FROM feeds WHERE id = ?', (feed_id,))
                row = c.fetchone()
                if row:
                    c.execute('DELETE FROM articles WHERE provider = ?', (row[0],))
            conn.commit()
            conn.close()
        return redirect(url_for("main.manage_feeds"))

    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('SELECT * FROM feeds WHERE is_default = 1 ORDER BY category, name')
    default_feeds = c.fetchall()
    c.execute('SELECT * FROM feeds WHERE added_by = ? AND is_default = 0 ORDER BY category, name', (username,))
    user_feeds = c.fetchall()
    conn.close()
    return render_template('manage_feeds.html', default_feeds=default_feeds, user_feeds=user_feeds,
                         categories=CATEGORIES)


@main_bp.route("/api/bookmark", methods=["POST"])
@login_required
def toggle_bookmark():
    article_id = request.json.get("article_id")
    if not article_id:
        return jsonify({"error": "missing article_id"}), 400
    username = session['user']
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('SELECT id FROM bookmarks WHERE username = ? AND article_id = ?', (username, article_id))
    existing = c.fetchone()
    if existing:
        c.execute('DELETE FROM bookmarks WHERE username = ? AND article_id = ?', (username, article_id))
        conn.commit()
        conn.close()
        return jsonify({"bookmarked": False})
    else:
        c.execute('INSERT INTO bookmarks (username, article_id) VALUES (?, ?)', (username, article_id))
        conn.commit()
        conn.close()
        return jsonify({"bookmarked": True})


@main_bp.route("/api/summarize", methods=["POST"])
@login_required
def summarize():
    article_id = request.json.get("article_id") if request.is_json else None
    if not article_id:
        return jsonify({"error": "missing article_id"}), 400
    article = get_article_by_id(article_id)
    if not article:
        return jsonify({"error": "not found"}), 404
    if article['summary']:
        logger.info("summarize cache hit id=%s", article_id)
        return jsonify({"summary": article['summary'], "cached": True})
    if not article['content']:
        logger.info("summarize no-content id=%s link=%s", article_id, article['link'])
        return jsonify({"error": "no content to summarize"}), 422
    summary = summarize_article(article['content'])
    if not summary:
        logger.warning("summarize produced empty result id=%s", article_id)
        return jsonify({"error": "summarization produced empty result"}), 502
    update_article_summary(article_id, summary)
    logger.info("summarize stored id=%s len=%d", article_id, len(summary))
    return jsonify({"summary": summary, "cached": False})


@main_bp.route("/bookmarks")
@login_required
def bookmarks():
    username = session['user']
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('''SELECT a.*, b.created_at as bookmarked_at FROM bookmarks b
                 JOIN articles a ON b.article_id = a.id
                 WHERE b.username = ? ORDER BY b.created_at DESC''', (username,))
    rows = c.fetchall()
    articles = [_row_to_article(r) for r in rows]
    conn.close()
    return render_template('bookmarks.html', articles=articles)
