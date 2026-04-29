"""
Retriever: embeds a user query and retrieves the top-k most relevant chunks.
"""
from typing import List

from ingestion.embedder import Embedder
from ingestion.vector_store import VectorStore
from models import RetrievedChunk


class Retriever:
    def __init__(self, embedder: Embedder, vector_store: VectorStore, k: int = 5):
        self._embedder = embedder
        self._vector_store = vector_store
        self._k = k

    def retrieve(self, query: str) -> List[RetrievedChunk]:
        """
        Embed query and return up to k RetrievedChunk objects.
        Returns empty list if vector store is empty.
        """
        if self._vector_store.count() == 0:
            return []
        query_embedding = self._embedder.embed(query)
        return self._vector_store.query(query_embedding, k=self._k)
