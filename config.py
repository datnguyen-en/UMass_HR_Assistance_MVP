"""
Reads all runtime configuration from environment variables / .env file.
Call load_config() at startup; raises ConfigError if required params are missing.
"""
import os
from dataclasses import dataclass, field


class ConfigError(Exception):
    pass


def _require(key: str) -> str:
    value = os.getenv(key)
    if not value:
        raise ConfigError(f"Required configuration parameter '{key}' is missing. "
                          f"Set it in your .env file or environment.")
    return value


def _optional(key: str, default: str) -> str:
    return os.getenv(key, default)


@dataclass
class Config:
    # LLM
    llm_model: str
    gemini_api_key: str

    # Chunking
    chunk_size: int
    overlap_pct: float

    # Retrieval
    top_k: int

    # Paths
    raw_data_dir: str
    chroma_dir: str

    # Sources
    source_urls: list[str] = field(default_factory=list)


def load_config() -> Config:
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass  # python-dotenv is optional; env vars may already be set

    llm_model = _optional("LLM_MODEL", "gemini-1.5-flash")
    gemini_api_key = os.getenv("GEMINI_API_KEY", "")

    if not gemini_api_key:
        raise ConfigError(
            "Required configuration parameter 'GEMINI_API_KEY' is missing. "
            "Set it in your .env file or environment."
        )

    raw_urls = os.getenv("SOURCE_URLS", "")
    source_urls = [u.strip() for u in raw_urls.split(",") if u.strip()]

    return Config(
        llm_model=llm_model,
        gemini_api_key=gemini_api_key,
        chunk_size=int(_optional("CHUNK_SIZE", "700")),
        overlap_pct=float(_optional("OVERLAP_PCT", "0.12")),
        top_k=int(_optional("TOP_K", "5")),
        raw_data_dir=_optional("RAW_DATA_DIR", "data/raw"),
        chroma_dir=_optional("CHROMA_DIR", "data/chroma"),
        source_urls=source_urls,
    )
