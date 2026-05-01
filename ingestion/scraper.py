"""
Scraper: fetches HTML from configured URLs and converts to clean Markdown.
Also discovers and downloads PDF links found on each page.
"""
import hashlib
import json
import logging
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
import trafilatura
from markdownify import markdownify
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class ScraperError(Exception):
    pass


class Scraper:
    def __init__(self, raw_data_dir: str = "data/raw"):
        self.raw_data_dir = Path(raw_data_dir)
        self.raw_data_dir.mkdir(parents=True, exist_ok=True)

    def fetch_and_convert(self, url: str) -> tuple[str, dict, str] | None:
        """
        Fetch HTML and convert to clean Markdown.
        Returns (markdown_text, metadata, raw_html) or None on HTTP error.
        Raises ScraperError on unrecoverable failure.
        """
        try:
            response = requests.get(url, timeout=15)
        except requests.RequestException as e:
            raise ScraperError(f"Failed to fetch {url}: {e}") from e

        if response.status_code >= 400:
            logger.warning("HTTP %d for URL: %s — skipping.", response.status_code, url)
            return None

        html = response.text

        # Try trafilatura first for clean content extraction
        extracted = trafilatura.extract(html, include_tables=True, include_links=False)
        if extracted:
            markdown = extracted
        else:
            markdown = markdownify(html, strip=["script", "style", "nav", "header", "footer"])

        # Extract title via BeautifulSoup
        title = url
        try:
            soup = BeautifulSoup(html, "html.parser")
            tag = soup.find("title")
            if tag and tag.string:
                title = tag.string.strip()
        except Exception:
            pass

        metadata = {"source_url": url, "document_title": title, "source_hash": self._url_hash(url)}
        return markdown, metadata, html

    def find_pdf_links(self, url: str, html: str) -> list[str]:
        """
        Parse HTML and return a list of absolute PDF URLs found on the page.
        Deduplicates results.
        """
        soup = BeautifulSoup(html, "html.parser")
        pdf_urls = set()
        for tag in soup.find_all("a", href=True):
            href = tag["href"].strip()
            # Resolve relative URLs
            absolute = urljoin(url, href)
            parsed = urlparse(absolute)
            if parsed.path.lower().endswith(".pdf"):
                pdf_urls.add(absolute)
        return list(pdf_urls)

    def download_pdf(self, pdf_url: str) -> Path | None:
        """
        Download a PDF from a URL and save it to data/raw/.
        Returns the local Path, or None on failure.
        """
        try:
            response = requests.get(pdf_url, timeout=30)
        except requests.RequestException as e:
            logger.warning("Failed to download PDF %s: %s", pdf_url, e)
            return None

        if response.status_code >= 400:
            logger.warning("HTTP %d downloading PDF: %s — skipping.", response.status_code, pdf_url)
            return None

        # Use URL hash as filename to keep it deterministic
        pdf_hash = self._url_hash(pdf_url)
        # Try to get a meaningful filename from the URL path
        url_path = urlparse(pdf_url).path
        original_name = Path(url_path).name or f"{pdf_hash}.pdf"
        if not original_name.lower().endswith(".pdf"):
            original_name += ".pdf"

        pdf_path = self.raw_data_dir / f"{pdf_hash}_{original_name}"
        pdf_path.write_bytes(response.content)
        logger.info("Downloaded PDF: %s → %s", pdf_url, pdf_path.name)
        return pdf_path

    def save(self, markdown: str, metadata: dict) -> Path:
        """Write markdown to data/raw/<url_hash>.md with a JSON sidecar."""
        source_hash = metadata.get("source_hash") or self._url_hash(metadata["source_url"])
        md_path = self.raw_data_dir / f"{source_hash}.md"
        meta_path = self.raw_data_dir / f"{source_hash}.json"
        md_path.write_text(markdown, encoding="utf-8")
        meta_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
        logger.info("Saved scraped page: %s", md_path)
        return md_path

    @staticmethod
    def _url_hash(url: str) -> str:
        return hashlib.sha256(url.encode()).hexdigest()[:16]
