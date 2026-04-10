import json
import socket
from urllib.error import HTTPError, URLError

import pytest

from scripts.embedding import OpenAICompatibleProvider, SkipProvider, get_provider


class _DummyHTTPResponse:
    def __init__(self, payload: dict):
        self._payload = json.dumps(payload).encode("utf-8")

    def read(self) -> bytes:
        return self._payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def test_skip_provider_returns_none():
    p = SkipProvider()
    assert p.embed(["hello"]) == [None]
    assert p.dim == 0
    assert p.name == "skip"


def test_get_provider_skip():
    p = get_provider("skip")
    assert isinstance(p, SkipProvider)


@pytest.mark.skipif_fastembed_unavailable
def test_fastembed_provider_returns_vector():
    from scripts.embedding import FastembedProvider

    p = FastembedProvider()
    vecs = p.embed(["hello world"])
    assert len(vecs) == 1
    assert len(vecs[0]) == p.dim
    assert all(isinstance(x, float) for x in vecs[0])


def test_openai_provider_reads_key_from_env(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "abc123")
    p = OpenAICompatibleProvider(
        model="text-embedding-3-small",
        dim=384,
        api_base="https://api.openai.com/v1",
        api_key_env="OPENAI_API_KEY",
    )
    assert p.name == "openai_compatible"
    assert p.dim == 384
    assert p._api_key == "abc123"


def test_openai_provider_sends_dimensions(monkeypatch):
    captured = {}

    def _fake_urlopen(request, timeout=0):
        captured["url"] = request.full_url
        captured["headers"] = dict(request.header_items())
        captured["body"] = json.loads(request.data.decode("utf-8"))
        captured["timeout"] = timeout
        return _DummyHTTPResponse(
            {"data": [{"index": 0, "embedding": [0.1, 0.2, 0.3]}, {"index": 1, "embedding": [0.4, 0.5, 0.6]}]}
        )

    monkeypatch.setenv("OPENAI_API_KEY", "k")
    monkeypatch.setattr("scripts.embedding.urllib_request.urlopen", _fake_urlopen)
    provider = OpenAICompatibleProvider(
        model="text-embedding-3-small",
        dim=384,
        api_base="https://api.openai.com/v1/",
        api_key_env="OPENAI_API_KEY",
    )
    vectors = provider.embed(["hello", "world"])
    assert captured["url"] == "https://api.openai.com/v1/embeddings"
    assert captured["body"]["model"] == "text-embedding-3-small"
    assert captured["body"]["dimensions"] == 384
    assert captured["body"]["input"] == ["hello", "world"]
    assert captured["timeout"] == 30
    assert "Authorization" in captured["headers"]
    assert vectors == [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]


def test_openai_provider_graceful_on_http_error(monkeypatch):
    def _raise_http(*_args, **_kwargs):
        raise HTTPError(
            url="https://api.openai.com/v1/embeddings",
            code=500,
            msg="boom",
            hdrs=None,
            fp=None,
        )

    monkeypatch.setattr("scripts.embedding.urllib_request.urlopen", _raise_http)
    provider = OpenAICompatibleProvider(
        model="text-embedding-3-small",
        dim=384,
        api_base="https://api.openai.com/v1",
        api_key_env="OPENAI_API_KEY",
    )
    assert provider.embed(["x", "y"]) == [None, None]


def test_openai_provider_graceful_on_timeout(monkeypatch):
    def _raise_timeout(*_args, **_kwargs):
        raise URLError(socket.timeout("timed out"))

    monkeypatch.setattr("scripts.embedding.urllib_request.urlopen", _raise_timeout)
    provider = OpenAICompatibleProvider(
        model="text-embedding-3-small",
        dim=384,
        api_base="https://api.openai.com/v1",
        api_key_env="OPENAI_API_KEY",
    )
    assert provider.embed(["x"]) == [None]


def test_openai_provider_truncates_vectors(monkeypatch):
    def _fake_urlopen(_request, timeout=0):
        _ = timeout
        return _DummyHTTPResponse({"data": [{"index": 0, "embedding": [float(i) for i in range(1536)]}]})

    monkeypatch.setattr("scripts.embedding.urllib_request.urlopen", _fake_urlopen)
    provider = OpenAICompatibleProvider(
        model="text-embedding-3-small",
        dim=384,
        api_base="https://api.openai.com/v1",
        api_key_env="OPENAI_API_KEY",
    )
    out = provider.embed(["x"])
    assert len(out[0]) == 384
    assert out[0][0] == 0.0
    assert out[0][-1] == 383.0


def test_openai_provider_batches_large_input(monkeypatch):
    calls = []

    def _fake_urlopen(request, timeout=0):
        _ = timeout
        body = json.loads(request.data.decode("utf-8"))
        calls.append(len(body["input"]))
        return _DummyHTTPResponse(
            {
                "data": [
                    {"index": i, "embedding": [float(i), float(i) + 0.5]}
                    for i in range(len(body["input"]))
                ]
            }
        )

    monkeypatch.setattr("scripts.embedding.urllib_request.urlopen", _fake_urlopen)
    provider = OpenAICompatibleProvider(
        model="text-embedding-3-small",
        dim=384,
        api_base="https://api.openai.com/v1",
        api_key_env="OPENAI_API_KEY",
    )
    texts = [f"t-{i}" for i in range(4097)]
    out = provider.embed(texts)
    assert calls == [2048, 2048, 1]
    assert len(out) == 4097
    assert out[0] == [0.0, 0.5]
    assert out[-1] == [0.0, 0.5]
