"""
LLMClient: constructs a grounded prompt and calls the Google Gemini API.
"""
import logging
from typing import List

import google.generativeai as genai

from models import Citation, LLMResponse, RetrievedChunk

logger = logging.getLogger(__name__)

PROMPT_TEMPLATE = """\
You are a helpful UMass HR assistant. Answer the question using ONLY the provided context.
If the context does not contain enough information, say so clearly.
Do NOT include any source references, filenames, or citations in your answer.

Context:
{context}

Question: {query}

Answer:"""


class LLMError(Exception):
    pass


class LLMClient:
    def __init__(self, model: str, api_key: str):
        self._model_name = model
        genai.configure(api_key=api_key)
        self._model = genai.GenerativeModel(model)

    def generate(self, query: str, context_chunks: List[RetrievedChunk]) -> LLMResponse:
        """
        Build prompt, call Gemini API, return LLMResponse with answer and citations.
        Raises LLMError on API failure.
        """
        prompt = self._build_prompt(query, context_chunks)
        try:
            response = self._model.generate_content(prompt)
            answer = response.text
        except Exception as e:
            logger.error("Gemini API error: %s", e)
            raise LLMError(f"Gemini API call failed: {e}") from e

        citations = []
        seen = set()
        for chunk in context_chunks:
            source = chunk.metadata.source_url or chunk.metadata.source_filename or "unknown"
            title = chunk.metadata.document_title or source
            if source not in seen:
                citations.append(Citation(source=source, title=title))
                seen.add(source)

        return LLMResponse(answer=answer, citations=citations)

    def _build_prompt(self, query: str, chunks: List[RetrievedChunk]) -> str:
        # Pass chunk text only — no source tags so Gemini doesn't echo filenames
        context = "\n\n".join(chunk.text for chunk in chunks)
        return PROMPT_TEMPLATE.format(context=context, query=query)
