import sqlite3

import db


def insert_article(
    db_path,
    provider="Example",
    title="Example title",
    link="https://example.com/article",
    category="Other",
    sentiment="neutral",
    fetched_at="2026-01-01 10:00:00",
):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        """INSERT INTO articles
           (provider, title, link, published, content, summary, sentiment, sentiment_score, category, fetched_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            provider,
            title,
            link,
            "2026-01-01",
            "Full article content",
            None,
            sentiment,
            0.5,
            category,
            fetched_at,
        ),
    )
    article_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return article_id


def test_create_user_hashes_password_and_rejects_duplicates(temp_db):
    assert db.create_user("alice", "secret") is True
    assert db.create_user("alice", "secret") is False

    user = db.get_user("alice")

    assert user["username"] == "alice"
    assert user["password_hash"] != "secret"
    assert db.check_password("secret", user["password_hash"]) is True
    assert db.check_password("wrong", user["password_hash"]) is False


def test_seed_default_feeds_is_idempotent(temp_db, monkeypatch):
    monkeypatch.setattr(
        db,
        "DEFAULT_FEEDS",
        [
            ("Feed A", "https://example.com/a.xml", "Technology"),
            ("Feed B", "https://example.com/b.xml", "Finance"),
        ],
    )

    db.seed_default_feeds()
    db.seed_default_feeds()

    sources = db.get_sources()

    assert sources == ["Feed A", "Feed B"]


def test_get_all_articles_filters_and_paginates(temp_db):
    insert_article(
        temp_db,
        provider="Tech Feed",
        title="First tech story",
        link="https://example.com/1",
        category="Technology",
        fetched_at="2026-01-01 10:00:00",
    )
    insert_article(
        temp_db,
        provider="Finance Feed",
        title="Finance story",
        link="https://example.com/2",
        category="Finance",
        fetched_at="2026-01-01 11:00:00",
    )
    insert_article(
        temp_db,
        provider="Tech Feed",
        title="Second tech story",
        link="https://example.com/3",
        category="Technology",
        fetched_at="2026-01-01 12:00:00",
    )

    articles, total = db.get_all_articles(page=1, per_page=1, category="Technology")

    assert total == 2
    assert articles[0]["title"] == "Second tech story"
    assert articles[0]["source"] == "Tech Feed"

    articles, total = db.get_all_articles(page=1, per_page=10, source="Finance Feed")

    assert total == 1
    assert articles[0]["category"] == "Finance"


def test_article_summary_update_and_sentiment_stats(temp_db):
    article_id = insert_article(
        temp_db,
        provider="Example",
        title="Positive story",
        link="https://example.com/positive",
        sentiment="positive",
    )
    insert_article(
        temp_db,
        provider="Example",
        title="Negative story",
        link="https://example.com/negative",
        sentiment="negative",
    )

    db.update_article_summary(article_id, "Short summary")
    article = db.get_article_by_id(article_id)
    stats = db.get_sentiment_stats("Example")

    assert article["summary"] == "Short summary"
    assert stats["positive"] == 1
    assert stats["negative"] == 1
    assert stats["neutral"] == 0
    assert stats["positive_pct"] == 50
