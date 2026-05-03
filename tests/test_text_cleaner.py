from text_cleaner import clean_article_text


def test_clean_article_text_removes_boilerplate_and_short_lines():
    text = """
    Home
    Subscribe to our newsletter for daily updates.
    This article explains how renewable energy storage is changing grid planning.
    Advertisement.
    Engineers are testing larger batteries across several regional networks.
    """

    cleaned = clean_article_text(text)

    assert cleaned == (
        "This article explains how renewable energy storage is changing grid planning.\n"
        "Engineers are testing larger batteries across several regional networks."
    )


def test_clean_article_text_returns_none_for_empty_or_only_boilerplate():
    assert clean_article_text("") is None
    assert clean_article_text("Skip to content\nLogin\nAdvertisement.") is None
