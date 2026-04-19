"""Article text cleaning pipeline.

`clean_article_text` is the single entry point used by the HTML/PDF fetch
dispatcher in `articles.py`. It removes common boilerplate (newsletter
pitches, cookie banners, social-share blurbs, copyright lines, nav clutter),
collapses whitespace, and drops lines shorter than `MIN_LINE_WORDS` — which
tend to be menu items, button labels, or other non-article fragments.

Patterns are tuned conservatively: a regex here should only match phrasing
that is almost certainly NOT part of the article body. When in doubt, prefer
leaving text in over stripping it.
"""

import logging
import re

logger = logging.getLogger(__name__)

BOILERPLATE_PATTERNS = [
    re.compile(r'(?i)\b(subscribe|sign\s+up)\s+(to|for)\b[^.]*\.'),
    re.compile(r'(?i)\bcookie\s+(notice|policy|settings|preferences)\b[^.]*\.'),
    re.compile(r'(?i)\b(advertisement|sponsored\s+content|promoted)\b[^.]*\.'),
    re.compile(r'(?i)\b(follow\s+us\s+on|share\s+(this|on))\s+(facebook|twitter|instagram|linkedin|x\b)[^.]*\.'),
    re.compile(r'(?i)\b(read\s+(more|also|next)|click\s+here|learn\s+more)\b[^.]*\.'),
    re.compile(r'(?i)\ball\s+rights\s+reserved[^.]*\.'),
    re.compile(r'(?i)©\s*\d{4}[^.]*\.'),
    re.compile(r'(?i)\b(terms\s+of\s+(service|use)|privacy\s+policy)\b[^.]*\.'),
    re.compile(r'(?i)\bskip\s+to\s+(main\s+)?content\b[^.]*\.?'),
    re.compile(r'(?i)\b(related\s+articles|you\s+may\s+also\s+like|recommended\s+for\s+you)\b[^.]*\.?'),
    re.compile(r'(?i)\b(Oops, something went wrong|This content is not available|Sorry, we can\'t find that page)\b[^.]*\.?'),
    re.compile(r'(?i)\b(to see your saved stories|login|sign in|unlock|offer|trial|subscribe)\b[^.]*\.?'),
    re.compile(r'(?i)\b(newsletter|daily\s+digest|weekly\s+roundup|exclusive\s+insights)\b[^.]*\.?'),
    re.compile(r'(?i)\b(ET Market Watch)\b[^.]*\.?')
]

MIN_LINE_WORDS = 4


def clean_article_text(text):
    """Strip boilerplate phrases, collapse whitespace, drop short lines."""
    if not text:
        return None
    original_len = len(text)
    for pat in BOILERPLATE_PATTERNS:
        text = pat.sub(' ', text)
    lines = []
    for raw in text.splitlines():
        line = re.sub(r'\s+', ' ', raw).strip()
        if not line:
            continue
        if len(line.split()) < MIN_LINE_WORDS:
            continue
        lines.append(line)
    cleaned = '\n'.join(lines).strip()
    if cleaned:
        logger.debug("clean_article_text: %d -> %d chars", original_len, len(cleaned))
    return cleaned or None
