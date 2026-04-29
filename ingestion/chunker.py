"""
Chunker: splits Markdown documents into overlapping token-aware chunks.
"""
import math
import logging
from typing import List

import tiktoken

from models import Chunk, ChunkMetadata

logger = logging.getLogger(__name__)

ENCODING = "cl100k_base"


class Chunker:
    def __init__(self, chunk_size: int = 700, overlap_pct: float = 0.12):
        self.chunk_size = chunk_size
        self.overlap = math.floor(chunk_size * overlap_pct)
        self._enc = tiktoken.get_encoding(ENCODING)

    def chunk(self, text: str, metadata: dict) -> List[Chunk]:
        """
        Split text into overlapping Chunk objects with full coverage guarantee.
        metadata dict must contain 'source_hash', 'document_title', and optionally
        'source_url' / 'source_filename'.
        """
        tokens = self._enc.encode(text)
        if not tokens:
            return []

        source_hash = metadata.get("source_hash", "unknown")
        chunks = []
        start = 0
        chunk_index = 0
        step = self.chunk_size - self.overlap

        while start < len(tokens):
            end = min(start + self.chunk_size, len(tokens))
            chunk_tokens = tokens[start:end]
            chunk_text = self._enc.decode(chunk_tokens)

            chunk_meta = ChunkMetadata(
                source_url=metadata.get("source_url"),
                source_filename=metadata.get("source_filename"),
                document_title=metadata.get("document_title", ""),
                chunk_index=chunk_index,
            )
            chunks.append(Chunk(
                text=chunk_text,
                metadata=chunk_meta,
                chunk_id=f"{source_hash}_{chunk_index}",
            ))
            chunk_index += 1
            if end == len(tokens):
                break
            start += step

        return chunks
