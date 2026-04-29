"""
VectorStore: persists chunks and embeddings in ChromaDB; supports similarity search.
"""
from typing import List

import chromadb

from models import Chunk, RetrievedChunk


class VectorStore:
    COLLECTION_NAME = "hr_docs"

    def __init__(self, persist_directory: str = "data/chroma"):
        self._client = chromadb.PersistentClient(path=persist_directory)
        self._collection = self._client.get_or_create_collection(
            name=self.COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )

    def upsert(self, chunks: List[Chunk], embeddings: List[List[float]]) -> None:
        """Upsert chunks by composite ID. Updates existing records."""
        if not chunks:
            return
        self._collection.upsert(
            ids=[c.chunk_id for c in chunks],
            documents=[c.text for c in chunks],
            embeddings=embeddings,
            metadatas=[{
                "source_url": c.metadata.source_url or "",
                "source_filename": c.metadata.source_filename or "",
                "document_title": c.metadata.document_title,
                "chunk_index": c.metadata.chunk_index,
            } for c in chunks],
        )

    def query(self, query_embedding: List[float], k: int = 5) -> List[RetrievedChunk]:
        """Return top-k chunks ranked by cosine similarity."""
        count = self.count()
        if count == 0:
            return []
        n = min(k, count)
        results = self._collection.query(
            query_embeddings=[query_embedding],
            n_results=n,
            include=["documents", "metadatas", "distances"],
        )
        chunks = []
        for doc, meta, dist in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        ):
            from models import ChunkMetadata
            chunks.append(RetrievedChunk(
                text=doc,
                metadata=ChunkMetadata(
                    source_url=meta.get("source_url") or None,
                    source_filename=meta.get("source_filename") or None,
                    document_title=meta.get("document_title", ""),
                    chunk_index=int(meta.get("chunk_index", 0)),
                ),
                similarity_score=1.0 - dist,  # cosine distance → similarity
            ))
        return chunks

    def count(self) -> int:
        """Return total number of stored chunks."""
        return self._collection.count()
