import pytest

from scripts.models import Edge, FileRef, Node
from scripts.store import InMemoryStore


@pytest.fixture
def store_with_refs():
    store = InMemoryStore()
    store.create_node(
        Node(
            id="root",
            project="demo",
            name="root",
            node_type="root",
            level=0,
            description="r",
            status="done",
            origin="user_stated",
            tokens_estimate=0,
            created_at="t",
            updated_at="t",
        )
    )
    store.create_node(
        Node(
            id="leaf-1",
            project="demo",
            name="leaf",
            node_type="leaf",
            level=1,
            description="a leaf",
            status="leaf",
            origin="user_stated",
            tokens_estimate=0,
            created_at="t",
            updated_at="t",
        )
    )
    store.add_edge(Edge(kind="hierarchy", from_id="root", to_id="leaf-1"))
    store.add_file_ref(
        FileRef(
            id="fr-1",
            node_id="leaf-1",
            path="src/a.py",
            lines="1-50",
            role="modify",
            content_hash="abc",
            scanned_at="t",
            status="current",
        )
    )
    store.add_file_ref(
        FileRef(
            id="fr-2",
            node_id="leaf-1",
            path="src/b.py",
            lines="*",
            role="read",
            content_hash="def",
            scanned_at="t",
            status="stale",
        )
    )
    return store


def test_assemble_context_includes_file_refs(store_with_refs):
    pkg = store_with_refs.assemble_context("demo", "leaf-1")
    assert len(pkg.file_refs) == 2
    stale = [ref for ref in pkg.file_refs if ref.get("status") == "stale"]
    assert len(stale) == 1
    assert stale[0]["path"] == "src/b.py"


def test_assemble_context_tokens_include_file_ref_chars(store_with_refs):
    pkg = store_with_refs.assemble_context("demo", "leaf-1")
    assert pkg.tokens_estimate > 0


def test_assemble_context_stale_ref_has_warning(store_with_refs):
    pkg = store_with_refs.assemble_context("demo", "leaf-1")
    stale_ref = [ref for ref in pkg.file_refs if ref["path"] == "src/b.py"][0]
    assert "warning" in stale_ref
    assert "stale" in stale_ref["warning"].lower()
