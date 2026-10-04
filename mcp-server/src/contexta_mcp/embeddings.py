"""Embedding adapter: speaks either Ollama's /api/embeddings or TEI's /embed."""

from __future__ import annotations

from typing import Literal

import httpx


class Embedder:
    """Minimal embedder that targets exactly one model on exactly one runner.

    Vectors from Ollama and TEI serving the same model weights are
    interchangeable under cosine distance (Qdrant normalizes internally).
    """

    def __init__(
        self,
        api: Literal["ollama", "tei"],
        url: str,
        model: str,
        timeout: float = 30.0,
    ) -> None:
        self._api = api
        self._url = url.rstrip("/")
        self._model = model
        self._client = httpx.AsyncClient(timeout=timeout)

    async def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        if self._api == "ollama":
            return await self._embed_ollama(texts)
        return await self._embed_tei(texts)

    async def _embed_ollama(self, texts: list[str]) -> list[list[float]]:
        # Ollama's /api/embeddings takes one prompt at a time.
        vectors: list[list[float]] = []
        for text in texts:
            resp = await self._client.post(
                f"{self._url}/api/embeddings",
                json={"model": self._model, "prompt": text},
            )
            resp.raise_for_status()
            vectors.append(resp.json()["embedding"])
        return vectors

    async def _embed_tei(self, texts: list[str]) -> list[list[float]]:
        resp = await self._client.post(
            f"{self._url}/embed",
            json={"inputs": texts},
        )
        resp.raise_for_status()
        return resp.json()

    async def aclose(self) -> None:
        await self._client.aclose()
