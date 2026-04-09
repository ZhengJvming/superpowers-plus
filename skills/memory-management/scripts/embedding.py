from __future__ import annotations

from typing import Optional, Protocol


class EmbeddingProvider(Protocol):
    name: str
    dim: int

    def embed(self, texts: list[str]) -> list[Optional[list[float]]]: ...


class SkipProvider:
    name = "skip"
    dim = 0

    def embed(self, texts: list[str]) -> list[Optional[list[float]]]:
        return [None for _ in texts]


class FastembedProvider:
    name = "fastembed"
    dim = 384

    def __init__(self, model: str = "BAAI/bge-small-en-v1.5"):
        from fastembed import TextEmbedding

        self._embedder = TextEmbedding(model_name=model)

    def embed(self, texts: list[str]) -> list[Optional[list[float]]]:
        vectors = list(self._embedder.embed(texts))
        return [v.tolist() for v in vectors]


def get_provider(name: str) -> EmbeddingProvider:
    if name == "skip":
        return SkipProvider()
    if name == "fastembed":
        return FastembedProvider()
    raise ValueError(f"unknown embedding provider: {name}")
