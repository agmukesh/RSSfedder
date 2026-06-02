import sys
from unittest.mock import MagicMock, patch

# Mock dependencies before importing feeds
mock_modules = [
    'requests',
    'feedparser',
    'vaderSentiment',
    'vaderSentiment.vaderSentiment',
    'sumy',
    'sumy.parsers.plaintext',
    'sumy.nlp.tokenizers',
    'sumy.summarizers.lsa',
    'nltk',
    'bs4',
    'bcrypt',
    'pymupdf',
    'fitz',
    'dotenv'
]
for mod in mock_modules:
    if mod not in sys.modules:
        sys.modules[mod] = MagicMock()

import unittest
# We need to make sure feeds is imported AFTER mocks are set
import feeds

class TestFeeds(unittest.TestCase):
    @patch('feeds.requests.get')
    @patch('feeds.feedparser.parse')
    def test_parse_feed_error_handling(self, mock_parse, mock_get):
        # Configure mock_get to raise an exception
        mock_get.side_effect = Exception("Network error")

        # Configure mock_parse to return a specific object when called with b""
        empty_feed = MagicMock()
        mock_parse.return_value = empty_feed

        url = "http://example.com/rss"
        result = feeds._parse_feed(url)

        # Verify requests.get was called
        mock_get.assert_called_once_with(url, headers={'User-Agent': feeds.FEED_USER_AGENT}, timeout=15)

        # Verify feedparser.parse was called with empty bytes
        mock_parse.assert_called_once_with(b"")

        # Verify the result is what feedparser.parse(b"") returned
        self.assertEqual(result, empty_feed)

    @patch('feeds.requests.get')
    @patch('feeds.feedparser.parse')
    def test_parse_feed_success(self, mock_parse, mock_get):
        # Configure mock_get to return a successful response
        mock_resp = MagicMock()
        mock_resp.content = b"fake rss content"
        mock_get.return_value = mock_resp

        # Configure mock_parse
        parsed_feed = MagicMock()
        mock_parse.return_value = parsed_feed

        url = "http://example.com/rss"
        result = feeds._parse_feed(url)

        # Verify raise_for_status was called
        mock_resp.raise_for_status.assert_called_once()

        # Verify feedparser.parse was called with content
        mock_parse.assert_called_once_with(b"fake rss content")

        self.assertEqual(result, parsed_feed)

if __name__ == '__main__':
    unittest.main()
