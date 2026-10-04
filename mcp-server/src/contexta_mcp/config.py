import os
from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class Config:
    qdrant_url: str
    embeddings_api: Literal["ollama", "tei"]
    embeddings_url: str
    embeddings_model: str
    collection: str
    vector_size: int
    search_default_limit: int
    mcp_host: str
    mcp_port: int


def load() -> Config:
    api = os.environ.get("EMBEDDINGS_API", "ollama").lower()
    if api not in {"ollama", "tei"}:
        raise ValueError(f"EMBEDDINGS_API must be 'ollama' or 'tei', got {api!r}")
    return Config(
        qdrant_url=os.environ.get("QDRANT_URL", "http://qdrant:6333"),
        embeddings_api=api,  # type: ignore[arg-type]
        embeddings_url=os.environ.get("EMBEDDINGS_URL", "http://ollama:11434"),
        embeddings_model=os.environ.get("EMBEDDINGS_MODEL", "nomic-embed-text:v1.5"),
        collection=os.environ.get("COLLECTION", "knowledge"),
        vector_size=int(os.environ.get("VECTOR_SIZE", "768")),
        search_default_limit=int(os.environ.get("SEARCH_DEFAULT_LIMIT", "5")),
        mcp_host=os.environ.get("MCP_HOST", "0.0.0.0"),
        mcp_port=int(os.environ.get("MCP_PORT", "3333")),
    )