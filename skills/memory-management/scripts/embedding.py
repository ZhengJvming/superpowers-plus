from __future__ import annotations

import json
import os
from typing import Optional, Protocol
from urllib import error as urllib_error
from urllib import request as urllib_request


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
        self.model = model

    def embed(self, texts: list[str]) -> list[Optional[list[float]]]:
        vectors = list(self._embedder.embed(texts))
        return [v.tolist() for v in vectors]


class OpenAICompatibleProvider:
    name = "openai_compatible"
    _MAX_BATCH = 2048

    def __init__(self, model: str, dim: int, api_base: str, api_key_env: str):
        if not model:
            raise ValueError("openai_compatible requires model")
        if not api_base:
            raise ValueError("openai_compatible requires api_base")
        if not api_key_env:
            raise ValueError("openai_compatible requires api_key_env")
        self.model = model
        self.dim = int(dim)
        self.api_base = api_base.rstrip("/")
        self.api_key_env = api_key_env
        self._api_key = os.environ.get(api_key_env, "")
        if not self._api_key:
            raise ValueError(f"missing API key in env var: {api_key_env}")

    def _embed_batch(self, texts: list[str]) -> list[Optional[list[float]]]:
        payload = {"input": texts, "model": self.model, "dimensions": self.dim}
        body = json.dumps(payload).encode("utf-8")
        request = urllib_request.Request(
            f"{self.api_base}/embeddings",
            data=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._api_key}",
            },
            method="POST",
        )
        try:
            with urllib_request.urlopen(request, timeout=30) as response:
                parsed = json.loads(response.read().decode("utf-8"))
        except (urllib_error.HTTPError, urllib_error.URLError, TimeoutError, ValueError):
            return [None for _ in texts]

        rows = sorted(parsed.get("data", []), key=lambda row: row.get("index", 0))
        vectors: list[Optional[list[float]]] = [None for _ in texts]
        for row in rows:
            idx = int(row.get("index", 0))
            if idx < 0 or idx >= len(texts):
                continue
            raw = row.get("embedding")
            if not isinstance(raw, list):
                continue
            vector = [float(x) for x in raw]
            if self.dim > 0 and len(vector) > self.dim:
                vector = vector[: self.dim]
            vectors[idx] = vector
        return vectors

    def embed(self, texts: list[str]) -> list[Optional[list[float]]]:
        outputs: list[Optional[list[float]]] = []
        for start in range(0, len(texts), self._MAX_BATCH):
            batch = texts[start : start + self._MAX_BATCH]
            outputs.extend(self._embed_batch(batch))
        return outputs


def get_provider(name: str, **kwargs) -> EmbeddingProvider:
    if name == "skip":
        return SkipProvider()
    if name == "fastembed":
        return FastembedProvider(model=kwargs.get("model") or "BAAI/bge-small-en-v1.5")
    if name == "openai_compatible":
        return OpenAICompatibleProvider(
            model=kwargs.get("model", ""),
            dim=int(kwargs.get("dim", 384)),
            api_base=kwargs.get("api_base", ""),
            api_key_env=kwargs.get("api_key_env", ""),
        )
    raise ValueError(f"unknown embedding provider: {name}")
