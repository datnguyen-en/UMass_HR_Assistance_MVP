"""
Embedder: converts text to 384-dimensional vectors using all-MiniLM-L6-v2.
"""
from typing import List

from sentence_transformers import SentenceTransformer


class Embedder:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self._model = SentenceTransformer(model_name)

    def embed(self, text: str) -> List[float]:
        """Return a 384-dimensional embedding vector."""
        return self._model.encode(text, convert_to_numpy=True).tolist()

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Batch embedding for efficiency during ingestion."""
        return self._model.encode(texts, convert_to_numpy=True).tolist()
