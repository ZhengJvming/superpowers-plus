import pytest

from scripts.embedding import SkipProvider, get_provider


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
