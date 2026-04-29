# Requirements Document

## Introduction

The UMass HR RAG Chatbot is a Retrieval-Augmented Generation system designed to help UMass HR staff and employees get accurate answers to HR-related questions. The system ingests public UMass HR documentation (web pages and PDFs), processes and stores it as vector embeddings, and uses an LLM to generate answers grounded in retrieved context with source citations.

The MVP targets a fully local, low-cost stack (ChromaDB, SentenceTransformers, Google Gemini API, Streamlit) with a clear migration path to AWS services.

## Glossary

- **Chatbot**: The end-to-end UMass HR RAG Chatbot application.
- **Scraper**: The component responsible for fetching and converting public UMass HR web pages to Markdown.
- **PDF_Processor**: The component responsible for extracting and converting HR PDF documents to semantic Markdown.
- **Ingestion_Pipeline**: The orchestration component that runs the Scraper and PDF_Processor and loads output into the Vector_Store.
- **Chunk**: A fixed-size segment of text (500–800 tokens with 10–15% overlap) derived from a processed document.
- **Embedder**: The component that converts text Chunks into vector embeddings using the all-MiniLM-L6-v2 SentenceTransformer model.
- **Vector_Store**: The ChromaDB persistent local database that stores Chunks and their embeddings.
- **Retriever**: The component that embeds a user query and retrieves the top-k most relevant Chunks from the Vector_Store.
- **LLM_Client**: The component that sends a constructed prompt (query + retrieved context) to the Google Gemini API and returns a response.
- **UI**: The Streamlit web interface through which users interact with the Chatbot.
- **Metadata**: Structured information stored alongside each Chunk, including source URL or file name, document title, and chunk index.

---

## Requirements

### Requirement 1: Web Scraping and HTML-to-Markdown Conversion

**User Story:** As an HR administrator, I want public UMass HR web pages to be automatically scraped and converted to Markdown, so that the Chatbot has up-to-date textual content to answer questions from.

#### Acceptance Criteria

1. WHEN the Ingestion_Pipeline is executed, THE Scraper SHALL fetch the HTML content of each configured UMass HR URL.
2. WHEN HTML content is fetched, THE Scraper SHALL convert the HTML to clean Markdown, stripping navigation, headers, footers, and non-content elements.
3. WHEN conversion is complete, THE Scraper SHALL write each page's Markdown to a file under `data/raw/` using a deterministic filename derived from the source URL.
4. IF a configured URL returns an HTTP error code (4xx or 5xx), THEN THE Scraper SHALL log the URL and error code and continue processing remaining URLs.
5. THE Scraper SHALL preserve the source URL as Metadata alongside each saved Markdown file.

---

### Requirement 2: PDF Processing and Semantic Markdown Extraction

**User Story:** As an HR administrator, I want HR PDF documents to be parsed and converted to structured Markdown, so that tables, headings, and body text are preserved for accurate retrieval.

#### Acceptance Criteria

1. WHEN a PDF file is provided to the PDF_Processor, THE PDF_Processor SHALL extract all text content, including body paragraphs, headings, and table data.
2. WHEN text is extracted, THE PDF_Processor SHALL convert the content to semantic Markdown, representing headings as `#`/`##`/`###` and tables as Markdown tables.
3. WHEN conversion is complete, THE PDF_Processor SHALL write the Markdown output to `data/raw/` with a filename derived from the source PDF filename.
4. IF a PDF file is corrupt or unreadable, THEN THE PDF_Processor SHALL log the filename and error and skip that file without halting the pipeline.
5. THE PDF_Processor SHALL store the source filename and page range as Metadata alongside each output file.

---

### Requirement 3: Document Chunking

**User Story:** As a developer, I want processed Markdown documents to be split into overlapping chunks, so that semantically coherent segments can be embedded and retrieved independently.

#### Acceptance Criteria

1. WHEN a Markdown document is ingested, THE Ingestion_Pipeline SHALL split it into Chunks of 500–800 tokens each.
2. WHEN splitting, THE Ingestion_Pipeline SHALL apply an overlap of 10–15% of the chunk size between consecutive Chunks to preserve context at boundaries.
3. THE Ingestion_Pipeline SHALL attach Metadata (source URL or filename, document title, chunk index) to each Chunk.
4. FOR ALL Markdown documents, the union of all Chunks produced SHALL cover the full text of the document without omission.

---

### Requirement 4: Embedding and Vector Storage

**User Story:** As a developer, I want document chunks to be embedded and stored in a persistent vector database, so that semantic similarity search can be performed at query time.

#### Acceptance Criteria

1. WHEN Chunks are produced by the Ingestion_Pipeline, THE Embedder SHALL generate a vector embedding for each Chunk using the all-MiniLM-L6-v2 SentenceTransformer model.
2. WHEN embeddings are generated, THE Ingestion_Pipeline SHALL store each Chunk's text, embedding, and Metadata in the Vector_Store.
3. THE Vector_Store SHALL persist embeddings to disk so that data survives process restarts without re-ingestion.
4. WHEN a Chunk with an identical source and chunk index already exists in the Vector_Store, THE Ingestion_Pipeline SHALL update the existing record rather than create a duplicate.
5. FOR ALL Chunks stored, the Metadata stored in the Vector_Store SHALL match the Metadata attached during chunking (round-trip property).

---

### Requirement 5: Query Retrieval

**User Story:** As an HR employee, I want the system to find the most relevant HR document segments for my question, so that the LLM answer is grounded in accurate source material.

#### Acceptance Criteria

1. WHEN a user submits a query, THE Retriever SHALL embed the query using the same all-MiniLM-L6-v2 model used during ingestion.
2. WHEN the query embedding is produced, THE Retriever SHALL retrieve the top-k Chunks (default k=5) from the Vector_Store ranked by cosine similarity.
3. THE Retriever SHALL return each retrieved Chunk's text and its associated Metadata (source URL or filename, document title, chunk index).
4. IF the Vector_Store contains fewer than k Chunks, THEN THE Retriever SHALL return all available Chunks without error.
5. WHILE the Vector_Store is empty, THE Retriever SHALL return an empty result set and THE UI SHALL display a message indicating no documents have been ingested.

---

### Requirement 6: LLM Answer Generation

**User Story:** As an HR employee, I want the chatbot to generate a clear, accurate answer to my HR question using retrieved context, so that I can trust the response is grounded in official UMass HR documentation.

#### Acceptance Criteria

1. WHEN retrieved Chunks are available, THE LLM_Client SHALL construct a prompt containing the user query and the text of all retrieved Chunks as context.
2. WHEN the prompt is constructed, THE LLM_Client SHALL send it to the Google Gemini API and return the generated response text.
3. THE LLM_Client SHALL include source citations (source URL or filename) in the response for each Chunk used as context.
4. IF the LLM API returns an error, THEN THE LLM_Client SHALL log the error and THE UI SHALL display a user-facing message indicating the answer could not be generated.

---

### Requirement 7: Streamlit User Interface

**User Story:** As an HR employee, I want a simple web interface to submit questions and read answers with source citations, so that I can use the chatbot without technical knowledge.

#### Acceptance Criteria

1. THE UI SHALL provide a text input field for the user to enter an HR question.
2. WHEN the user submits a question, THE UI SHALL display a loading indicator while the Retriever and LLM_Client process the request.
3. WHEN an answer is returned, THE UI SHALL display the answer text and a list of source citations (document title and URL or filename) below the answer.
4. THE UI SHALL display the full conversation history (all prior questions and answers) within the current session.
5. IF an error occurs during retrieval or generation, THE UI SHALL display a descriptive error message to the user without exposing internal stack traces.

---

### Requirement 8: Ingestion Pipeline Orchestration

**User Story:** As a developer, I want a single command to trigger the full ingestion pipeline (scrape → PDF process → chunk → embed → store), so that the vector database can be refreshed easily.

#### Acceptance Criteria

1. THE Ingestion_Pipeline SHALL provide a single entry-point command (`python ingestion/ingest.py`) that executes scraping, PDF processing, chunking, embedding, and storage in sequence.
2. WHEN the pipeline completes successfully, THE Ingestion_Pipeline SHALL log a summary including the number of documents processed and Chunks stored.
3. IF any individual document fails during processing, THEN THE Ingestion_Pipeline SHALL log the failure and continue processing remaining documents.
4. THE Ingestion_Pipeline SHALL be idempotent: running it multiple times on the same source data SHALL produce the same Vector_Store state as running it once.

---

### Requirement 9: Configuration Management

**User Story:** As a developer, I want all runtime parameters (LLM provider, model name, chunk size, top-k, source URLs) to be configurable without code changes, so that the system can be tuned and migrated easily.

#### Acceptance Criteria

1. THE Chatbot SHALL read all configurable parameters (LLM model name, API key, chunk size, overlap percentage, top-k, list of source URLs, data directories) from a `.env` file or environment variables.
2. IF a required configuration parameter is missing at startup, THEN THE Chatbot SHALL log a descriptive error message identifying the missing parameter and exit.
3. THE LLM_Client SHALL use the Google Gemini API with the configured `GEMINI_API_KEY` and `LLM_MODEL`.
