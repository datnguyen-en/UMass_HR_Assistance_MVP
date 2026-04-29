"""
Scraper: fetches HTML from configured URLs and converts to clean Markdown.
"""
import hashlib
import json
import logging
from pathlib import Path

import requests
import trafilatura
from markdownify import markdownify

logger = logging.getLogger(__name__)


class ScraperError(Exception):
    pass


class Scraper:
    def __init__(self, raw_data_dir: str = "data/raw"):
        self.raw_data_dir = Path(raw_data_dir)
        self.raw_data_dir.mkdir(parents=True, exist_ok=True)

    def fetch_and_convert(self, url: str) -> tuple[str, dict] | None:
        """
        Fetch HTML and convert to clean Markdown.
        Returns (markdown_text, metadata) or None on HTTP error.
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

        # Extract title
        title = url
        try:
            from html.parser import HTMLParser
            class TitleParser(HTMLParser):
                def __init__(self):
                    super().__init__()
                    self.title = ""
                    self._in_title = False
                def handle_starttag(self, tag, attrs):
                    if tag == "title":
                        self._in_title = True
                def handle_data(self, data):
                    if self._in_title:
                        self.title = data.strip()
                        self._in_title = False
            p = TitleParser()
            p.feed(html)
            if p.title:
                title = p.title
        except Exception:
            pass

        metadata = {"source_url": url, "document_title": title, "source_hash": self._url_hash(url)}
        return markdown, metadata

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
