# Implementation Plan: UMass HR RAG Chatbot

## Overview

Implement the RAG chatbot in Python using a layered architecture: ingestion pipeline (scraper, PDF processor, chunker, embedder, vector store), query pipeline (retriever, LLM client), and Streamlit UI. Each component is built and wired incrementally.

## Tasks

- [x] 1. Set up project structure, config, and shared data models
  - Create all directories and skeleton files per the file layout in the design
  - Implement `models.py` with all shared dataclasses (`ChunkMetadata`, `Chunk`, `RetrievedChunk`, `Citation`, `LLMResponse`, `IngestionSummary`)
  - Implement `config.py` to read all parameters from `.env` / environment variables; raise descriptive error on missing required params
  - Populate `.env.example` with all required keys and defaults
  - Populate `requirements.txt` with all dependencies
  - _Requirements: 9.1, 9.2_

- [ ] 2. Implement the Scraper
  - [x] 2.1 Implement `ingestion/scraper.py` — `Scraper` class
    - `fetch_and_convert(url)`: fetch HTML with `requests`, extract main content with `trafilatura`, fall back to `markdownify`; return `(markdown, metadata)`
    - `save(markdown, metadata)`: write to `data/raw/<url_hash>.md` with JSON sidecar; use deterministic URL-safe hash for filename
    - Log and skip on HTTP 4xx/5xx; raise `ScraperError` on unrecoverable failure
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5_

  - [ ]* 2.2 Write unit tests for `Scraper`
    - Test successful fetch-and-convert with a mocked HTTP response
    - Test that HTTP 4xx/5xx logs and continues (does not raise)
    - Test deterministic filename generation
    - _Requirements: 1.3, 1.4_

- [ ] 3. Implement the PDF Processor
  - [x] 3.1 Implement `ingestion/pdf_processor.py` — `PDFProcessor` class
    - `process(pdf_path)`: use `pymupdf4llm` to extract Markdown preserving headings and tables; return `(markdown, metadata)` with `source_filename` and `page_range`
    - `save(markdown, metadata)`: write to `data/raw/<pdf_stem>.md` with JSON sidecar
    - Log and skip corrupt/unreadable files; raise `PDFProcessorError` on unrecoverable failure
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_

  - [ ]* 3.2 Write unit tests for `PDFProcessor`
    - Test successful extraction with a minimal test PDF
    - Test that corrupt file logs and skips without halting
    - _Requirements: 2.3, 2.4_

- [ ] 4. Implement the Chunker
  - [x] 4.1 Implement `ingestion/chunker.py` — `Chunker` class
    - Token-aware sliding window using `tiktoken` (cl100k_base); default `chunk_size=700`, `overlap_pct=0.12`
    - `chunk(text, metadata)`: return `list[Chunk]` with correct `chunk_id` (`{source_hash}_{chunk_index}`) and attached metadata
    - Guarantee full coverage: union of all chunk texts equals original text
    - _Requirements: 3.1, 3.2, 3.3, 3.4_

  - [ ]* 4.2 Write property test for full-coverage guarantee
    - **Property: Full Coverage** — for any non-empty string input, the concatenation of all chunk texts (ignoring overlap) covers every token of the original document
    - **Validates: Requirements 3.4**

  - [ ]* 4.3 Write unit tests for `Chunker`
    - Test chunk size bounds (500–800 tokens)
    - Test overlap percentage is within 10–15%
    - Test metadata is correctly attached to each chunk
    - _Requirements: 3.1, 3.2, 3.3_

- [ ] 5. Implement the Embedder
  - [x] 5.1 Implement `ingestion/embedder.py` — `Embedder` class
    - Load `all-MiniLM-L6-v2` via `sentence-transformers`
    - `embed(text)`: return 384-dim `list[float]`
    - `embed_batch(texts)`: batch encode for ingestion efficiency
    - _Requirements: 4.1_

  - [ ]* 5.2 Write unit tests for `Embedder`
    - Test output dimensionality is 384
    - Test `embed_batch` returns same results as calling `embed` individually
    - _Requirements: 4.1_

- [ ] 6. Implement the Vector Store
  - [x] 6.1 Implement `ingestion/vector_store.py` — `VectorStore` class
    - Use `chromadb.PersistentClient` with cosine distance; collection name `hr_docs`
    - `upsert(chunks, embeddings)`: upsert by composite ID `{source_hash}_{chunk_index}`
    - `query(query_embedding, k)`: return `list[RetrievedChunk]` ranked by cosine similarity
    - `count()`: return total stored chunks
    - _Requirements: 4.2, 4.3, 4.4, 4.5_

  - [ ]* 6.2 Write property test for upsert idempotency
    - **Property: Upsert Idempotency** — upserting the same set of chunks twice produces the same `count()` as upserting once
    - **Validates: Requirements 4.4, 8.4**

  - [ ]* 6.3 Write unit tests for `VectorStore`
    - Test that `count()` increases after upsert
    - Test that re-upserting same IDs does not duplicate records
    - Test `query` returns at most k results
    - _Requirements: 4.3, 4.4_

- [ ] 7. Checkpoint — Ingestion components complete
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 8. Implement the Ingestion Pipeline
  - [x] 8.1 Implement `ingestion/ingest.py` — `IngestionPipeline` class and `__main__` entry point
    - `run()`: orchestrate scrape URLs → process PDFs → chunk all docs → embed (batch) → upsert; log per-document failures and continue
    - Return `IngestionSummary` with `documents_processed`, `chunks_stored`, `failures`
    - Log summary on completion
    - _Requirements: 8.1, 8.2, 8.3, 8.4_

  - [ ]* 8.2 Write integration test for `IngestionPipeline`
    - Use a small fixture (one mock URL + one test PDF) to verify end-to-end: scrape → chunk → embed → upsert → `count() > 0`
    - Verify idempotency: running pipeline twice yields same `count()`
    - _Requirements: 8.1, 8.4_

- [ ] 9. Implement the Retriever
  - [x] 9.1 Implement `retrieval/retriever.py` — `Retriever` class
    - `retrieve(query)`: embed query with shared `Embedder`, call `VectorStore.query(k=5)`, return `list[RetrievedChunk]`
    - Return empty list (no error) when vector store is empty
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

  - [ ]* 9.2 Write unit tests for `Retriever`
    - Test returns empty list when store is empty
    - Test returns ≤ k results when store has fewer than k chunks
    - _Requirements: 5.4, 5.5_

- [ ] 10. Implement the LLM Client
  - [x] 10.1 Implement `retrieval/llm_client.py` — `LLMClient` class
    - Use `google-generativeai` SDK; configure with `GEMINI_API_KEY` and `LLM_MODEL`
    - `generate(query, context_chunks)`: build prompt from template in design, call `genai.GenerativeModel.generate_content()`, parse `LLMResponse` with `answer` and `citations`
    - Raise `LLMError` and log on API failure
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 9.1, 9.2, 9.3_

  - [ ]* 10.2 Write unit tests for `LLMClient`
    - Test prompt construction includes query and all chunk texts
    - Test citations are extracted for each context chunk
    - Test `LLMError` is raised and logged on API failure (mock the API call)
    - _Requirements: 6.1, 6.3, 6.4_

- [ ] 11. Checkpoint — Query pipeline complete
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 12. Implement the Streamlit UI
  - [x] 12.1 Implement `ui/app.py` — Streamlit application
    - Text input for HR question; loading spinner during retrieval + generation
    - Display answer and source citations (title + URL/filename) below the answer
    - Session-state conversation history showing all prior Q&A pairs
    - If vector store is empty, display "No documents have been ingested yet."
    - Display user-friendly error messages on retrieval or LLM failure (no stack traces)
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 5.5_

- [ ] 13. Wire everything together and final validation
  - [ ] 13.1 Verify `config.py` is imported by all components; confirm missing-param error exits with descriptive message
    - _Requirements: 9.1, 9.2_

  - [ ] 13.2 Verify `python ingestion/ingest.py` runs end-to-end with at least one real URL from config
    - _Requirements: 8.1, 8.2_

  - [ ]* 13.3 Write end-to-end smoke test
    - Ingest a fixture document, run a retrieval query, assert at least one chunk is returned with correct metadata
    - _Requirements: 4.5, 5.3_

- [ ] 14. Final checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for a faster MVP
- Each task references specific requirements for traceability
- The same `Embedder` instance must be shared between ingestion and retrieval to guarantee embedding space consistency
- Property tests validate universal correctness guarantees (full coverage, upsert idempotency)
