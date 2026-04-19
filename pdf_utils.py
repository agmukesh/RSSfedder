"""PDF text extraction via PyMuPDF (fitz).

Exposes `is_pdf_url` (cheap extension check used by the HTML/PDF dispatcher in
`articles.py`) and `extract_pdf_text`, which downloads a PDF by URL and returns
its concatenated page text (or None on any failure). A 20 MB hard cap and
15-second download timeout protect the fetch loop from a runaway file.
"""

import logging
import requests
import fitz

logger = logging.getLogger(__name__)

PDF_TIMEOUT = 15
PDF_MAX_BYTES = 20 * 1024 * 1024
PDF_USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'


def is_pdf_url(url):
    return url.lower().split('?')[0].endswith('.pdf')


def extract_pdf_text(url):
    """Download the PDF at `url` and return its text, or None on failure."""
    try:
        resp = requests.get(url, headers={'User-Agent': PDF_USER_AGENT}, timeout=PDF_TIMEOUT)
        resp.raise_for_status()
        if len(resp.content) > PDF_MAX_BYTES:
            logger.warning("PDF too large (%d bytes): %s", len(resp.content), url)
            return None
        with fitz.open(stream=resp.content, filetype='pdf') as doc:
            pages = doc.page_count
            text = "\n".join(page.get_text() for page in doc)
        logger.info("PDF extracted %d chars from %s (%d pages)", len(text), url, pages)
        return text or None
    except Exception:
        logger.exception("PDF extraction failed for %s", url)
        return None
