"""
Ingestion Pipeline entry point.
Usage: python ingestion/ingest.py
"""
import logging
import sys
from pathlib import Path

# Allow imports from project root
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import load_config
from models import IngestionSummary

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


class IngestionPipeline:
    def __init__(self):
        self.config = load_config()

    def run(self) -> IngestionSummary:
        """
        Execute: scrape URLs → process PDFs → chunk → embed → upsert.
        Logs per-document failures and continues.
        Returns IngestionSummary.
        """
        from ingestion.scraper import Scraper, ScraperError
        from ingestion.pdf_processor import PDFProcessor
        from ingestion.chunker import Chunker
        from ingestion.embedder import Embedder
        from ingestion.vector_store import VectorStore

        cfg = self.config
        scraper = Scraper(raw_data_dir=cfg.raw_data_dir)
        pdf_processor = PDFProcessor(raw_data_dir=cfg.raw_data_dir)
        chunker = Chunker(chunk_size=cfg.chunk_size, overlap_pct=cfg.overlap_pct)
        embedder = Embedder()
        vector_store = VectorStore(persist_directory=cfg.chroma_dir)

        all_chunks = []
        docs_processed = 0
        failures = []

        # Scrape web URLs
        for url in cfg.source_urls:
            try:
                result = scraper.fetch_and_convert(url)
                if result is None:
                    failures.append(url)
                    continue
                markdown, metadata = result
                scraper.save(markdown, metadata)
                chunks = chunker.chunk(markdown, metadata)
                all_chunks.extend(chunks)
                docs_processed += 1
                logger.info("Scraped and chunked: %s (%d chunks)", url, len(chunks))
            except ScraperError as e:
                logger.error("Scraper error for %s: %s", url, e)
                failures.append(url)
            except Exception as e:
                logger.error("Unexpected error for %s: %s", url, e)
                failures.append(url)

        # Process PDFs from data/raw/
        pdf_dir = Path(cfg.raw_data_dir)
        for pdf_path in pdf_dir.glob("*.pdf"):
            try:
                result = pdf_processor.process(pdf_path)
                if result is None:
                    failures.append(str(pdf_path))
                    continue
                markdown, metadata = result
                pdf_processor.save(markdown, metadata)
                chunks = chunker.chunk(markdown, metadata)
                all_chunks.extend(chunks)
                docs_processed += 1
                logger.info("Processed PDF: %s (%d chunks)", pdf_path.name, len(chunks))
            except Exception as e:
                logger.error("Error processing PDF %s: %s", pdf_path, e)
                failures.append(str(pdf_path))

        # Embed and upsert
        chunks_stored = 0
        if all_chunks:
            logger.info("Embedding %d chunks...", len(all_chunks))
            texts = [c.text for c in all_chunks]
            embeddings = embedder.embed_batch(texts)
            vector_store.upsert(all_chunks, embeddings)
            chunks_stored = len(all_chunks)

        return IngestionSummary(
            documents_processed=docs_processed,
            chunks_stored=chunks_stored,
            failures=failures,
        )


if __name__ == "__main__":
    pipeline = IngestionPipeline()
    summary = pipeline.run()
    logger.info(
        "Ingestion complete: %d documents processed, %d chunks stored, %d failures.",
        summary.documents_processed,
        summary.chunks_stored,
        len(summary.failures),
    )
    if summary.failures:
        logger.warning("Failed sources: %s", summary.failures)
