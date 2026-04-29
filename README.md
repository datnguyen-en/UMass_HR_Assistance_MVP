# UMass HR RAG Chatbot

A Retrieval-Augmented Generation (RAG) chatbot that answers HR-related questions using official UMass HR documentation. Built as a summer intern project.

## How It Works

1. **Ingestion** — Scrapes public UMass HR web pages and processes PDF documents, converts them to Markdown, chunks the text, generates embeddings, and stores everything in a local ChromaDB vector database.
2. **Query** — When you ask a question, it finds the most relevant document chunks using semantic search, then sends them to Google Gemini to generate a grounded answer with source citations.

## Tech Stack

| Component | Technology |
|---|---|
| Web scraping | `requests` + `trafilatura` + `markdownify` |
| PDF processing | `pymupdf4llm` |
| Embeddings | `sentence-transformers` (all-MiniLM-L6-v2) |
| Vector store | ChromaDB (local persistent) |
| LLM | Google Gemini API |
| UI | Streamlit |

## Project Structure

```
umass-hr-chatbot/
├── ingestion/
│   ├── ingest.py          # Pipeline entry point
│   ├── scraper.py         # Web scraper
│   ├── pdf_processor.py   # PDF → Markdown
│   ├── chunker.py         # Text chunking
│   ├── embedder.py        # Embedding generation
│   └── vector_store.py    # ChromaDB wrapper
├── retrieval/
│   ├── retriever.py       # Semantic search
│   └── llm_client.py      # Gemini API client
├── ui/
│   └── app.py             # Streamlit chatbot UI
├── data/
│   ├── raw/               # Scraped Markdown files
│   └── chroma/            # Vector database
├── config.py              # Config loader
├── models.py              # Shared data models
├── .env.example           # Environment variable template
└── requirements.txt
```

## Setup

### 1. Clone the repo

```bash
git clone https://github.com/your-username/umass-hr-chatbot.git
cd umass-hr-chatbot
```

### 2. Create and activate a virtual environment

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

```bash
cp .env.example .env
```

Open `.env` and fill in your values:

```
GEMINI_API_KEY=your-gemini-api-key-here
SOURCE_URLS=https://www.umass.edu/hr/,https://www.umass.edu/hr/benefits
```

Get a free Gemini API key at [aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey).

## Running the Project

### Step 1 — Ingest HR documents

```bash
python ingestion/ingest.py
```

This scrapes the configured URLs, processes any PDFs in `data/raw/`, and builds the vector database. Run this once to get started, and again whenever you want to refresh the data.

### Step 2 — Launch the chatbot

```bash
streamlit run ui/app.py
```

Opens the chatbot in your browser at `http://localhost:8501`.

## Adding PDF Documents

Drop any HR PDF files into `data/raw/` before running the ingestion pipeline. They will be automatically processed alongside the scraped web pages.

## Configuration Options

All settings are controlled via `.env`:

| Variable | Default | Description |
|---|---|---|
| `GEMINI_API_KEY` | *(required)* | Google Gemini API key |
| `LLM_MODEL` | `gemini-1.5-flash` | Gemini model name |
| `SOURCE_URLS` | *(required)* | Comma-separated URLs to scrape |
| `CHUNK_SIZE` | `700` | Tokens per chunk |
| `OVERLAP_PCT` | `0.12` | Overlap between chunks (12%) |
| `TOP_K` | `5` | Number of chunks retrieved per query |
| `RAW_DATA_DIR` | `data/raw` | Directory for raw Markdown files |
| `CHROMA_DIR` | `data/chroma` | Directory for vector database |

## Future Migration to AWS

The local stack maps cleanly to AWS services when ready to scale:

| Local | AWS |
|---|---|
| Local folder | S3 |
| ChromaDB | pgvector on Aurora |
| Python script | Lambda |
| Gemini API | Amazon Bedrock |
| Local machine | EC2 / ECS |
