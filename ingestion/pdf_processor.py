"""
PDFProcessor: extracts text, headings, and tables from PDFs and converts to Markdown.
"""
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class PDFProcessorError(Exception):
    pass


class PDFProcessor:
    def __init__(self, raw_data_dir: str = "data/raw"):
        self.raw_data_dir = Path(raw_data_dir)
        self.raw_data_dir.mkdir(parents=True, exist_ok=True)

    def process(self, pdf_path: Path) -> tuple[str, dict] | None:
        """
        Extract and convert PDF to Markdown.
        Returns (markdown_text, metadata) or None on corrupt/unreadable file.
        """
        try:
            import pymupdf4llm
            import fitz  # PyMuPDF
            doc = fitz.open(str(pdf_path))
            page_count = len(doc)
            doc.close()
            markdown = pymupdf4llm.to_markdown(str(pdf_path))
            metadata = {
                "source_filename": pdf_path.name,
                "page_range": f"1-{page_count}",
                "document_title": pdf_path.stem,
                "source_hash": pdf_path.stem,
            }
            return markdown, metadata
        except Exception as e:
            logger.warning("Failed to process PDF %s: %s — skipping.", pdf_path, e)
            return None

    def save(self, markdown: str, metadata: dict) -> Path:
        """Write markdown to data/raw/<pdf_stem>.md with a JSON sidecar."""
        stem = metadata.get("source_hash") or Path(metadata["source_filename"]).stem
        md_path = self.raw_data_dir / f"{stem}.md"
        meta_path = self.raw_data_dir / f"{stem}.json"
        md_path.write_text(markdown, encoding="utf-8")
        meta_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
        logger.info("Saved PDF: %s", md_path)
        return md_path
