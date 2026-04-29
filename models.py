from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ChunkMetadata:
    source_url: Optional[str]       # For web-scraped content
    source_filename: Optional[str]  # For PDF content
    document_title: str
    chunk_index: int


@dataclass
class Chunk:
    text: str
    metadata: ChunkMetadata
    chunk_id: str  # "{source_hash}_{chunk_index}"


@dataclass
class RetrievedChunk:
    text: str
    metadata: ChunkMetadata
    similarity_score: float


@dataclass
class Citation:
    source: str   # URL or filename
    title: str


@dataclass
class LLMResponse:
    answer: str
    citations: list[Citation]


@dataclass
class IngestionSummary:
    documents_processed: int
    chunks_stored: int
    failures: list[str] = field(default_factory=list)
