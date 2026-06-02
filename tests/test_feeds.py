import pytest
from feeds import is_safe_url, _parse_feed
from unittest.mock import patch, MagicMock

def test_is_safe_url_valid():
    # We mock socket.getaddrinfo to return a public IP for testing,
    # to avoid tests failing without internet or when google.com resolves to something unexpected.
    with patch('socket.getaddrinfo') as mock_getaddrinfo:
        # Format: [(family, type, proto, canonname, sockaddr)]
        mock_getaddrinfo.return_value = [(2, 1, 6, '', ('8.8.8.8', 80))]
        assert is_safe_url("http://google.com") is True
        assert is_safe_url("https://google.com") is True

def test_is_safe_url_invalid_schemes():
    assert is_safe_url("ftp://google.com") is False
    assert is_safe_url("file:///etc/passwd") is False
    assert is_safe_url("gopher://google.com") is False
    assert is_safe_url("javascript:alert(1)") is False
    assert is_safe_url("data:text/plain;base64,SGVsbG8sIFdvcmxkIQ==") is False

def test_is_safe_url_private_ips():
    # Localhost
    assert is_safe_url("http://localhost") is False
    assert is_safe_url("http://127.0.0.1") is False
    assert is_safe_url("http://[::1]") is False

    # Private IPs
    assert is_safe_url("http://192.168.1.1") is False
    assert is_safe_url("http://10.0.0.1") is False
    assert is_safe_url("http://172.16.0.1") is False

    # Other unsafe IPs
    assert is_safe_url("http://169.254.169.254") is False  # AWS Metadata

def test_is_safe_url_dns_resolution_failure():
    with patch('socket.getaddrinfo', side_effect=Exception("DNS resolution failed")):
        assert is_safe_url("http://nonexistent.domain.internal") is False

def test_parse_feed_safe_url():
    with patch('feeds.is_safe_url', return_value=True):
        with patch('requests.get') as mock_get:
            mock_resp = MagicMock()
            mock_resp.content = b"<rss><channel><title>Test Feed</title></channel></rss>"
            mock_get.return_value = mock_resp

            feed = _parse_feed("http://safe-feed.com")

            mock_get.assert_called_once()
            assert "entries" in feed

def test_parse_feed_unsafe_url():
    with patch('feeds.is_safe_url', return_value=False):
        with patch('requests.get') as mock_get:
            feed = _parse_feed("http://localhost/feed.xml")

            mock_get.assert_not_called()
            assert len(feed.get("entries", [])) == 0

def test_is_safe_url_unspecified():
    # 0.0.0.0 acts as loopback on linux
    assert is_safe_url("http://0.0.0.0") is False

def test_parse_feed_redirect():
    with patch('feeds.is_safe_url', return_value=True):
        with patch('requests.get') as mock_get:
            mock_resp = MagicMock()
            mock_resp.status_code = 301
            mock_get.return_value = mock_resp

            feed = _parse_feed("http://safe-feed.com")

            mock_get.assert_called_once()
            # Redirect blocks parsing
            assert len(feed.get("entries", [])) == 0
