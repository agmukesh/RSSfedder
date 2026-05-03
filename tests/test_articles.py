import articles


def test_categorize_article_uses_feed_category():
    assert articles.categorize_article("AI stocks rally", "Technology") == "Technology"
    assert articles.categorize_article("Unclassified story") == "Other"


def test_analyze_sentiment_handles_empty_text():
    assert articles.analyze_sentiment("") == ("neutral", 0.5)


def test_summarize_article_requires_enough_text():
    assert articles.summarize_article("Too short.") is None


def test_summarize_article_returns_first_requested_sentences():
    sentences = [
        "This is a detailed sentence about market structure and long term planning.",
        "Another sentence adds context about implementation decisions and user impact.",
        "A third sentence explains the current tradeoffs in plain language.",
        "A fourth sentence should not be included in the final summary.",
    ]
    text = " ".join(sentences * 4)

    assert articles.summarize_article(text, sentences=2) == " ".join(sentences[:2])


def test_fetch_full_content_skips_synthetic_and_non_web_links(monkeypatch):
    def fail_fetch(_url):
        raise AssertionError("fetch_article_content should not be called")

    monkeypatch.setattr(articles, "fetch_article_content", fail_fetch)

    assert articles.fetch_full_content("synthetic:provider:abc123") is None
    assert articles.fetch_full_content("https://example.com/report.zip") is None
