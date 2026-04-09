import pytest

from scripts.cozo_store import CozoStore
from scripts.models import FileRef, Node
from scripts.store import InMemoryStore


@pytest.fixture(params=["memory", "cozo"])
def store_with_node(request, tmp_path):
    if request.param == "memory":
        store = InMemoryStore()
    else:
        store = CozoStore(db_path=str(tmp_path / "test.cozo"), embedding_provider=None)
        store.ensure_schema()
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
    return store


def test_add_and_list_file_refs(store_with_node):
    store = store_with_node
    file_ref = FileRef(
        id="fr-1",
        node_id="leaf-1",
        path="src/a.py",
        lines="1-50",
        role="modify",
        content_hash="abc",
        scanned_at="t",
        status="current",
    )
    store.add_file_ref(file_ref)
    refs = store.list_file_refs("demo", "leaf-1")
    assert len(refs) == 1
    assert refs[0].path == "src/a.py"


def test_update_file_ref_status(store_with_node):
    store = store_with_node
    file_ref = FileRef(
        id="fr-1",
        node_id="leaf-1",
        path="src/a.py",
        lines="*",
        role="read",
        content_hash="abc",
        scanned_at="t",
        status="current",
    )
    store.add_file_ref(file_ref)
    store.update_file_ref("fr-1", status="stale", content_hash="def")
    refs = store.list_file_refs("demo", "leaf-1")
    assert refs[0].status == "stale"
    assert refs[0].content_hash == "def"


def test_delete_file_ref(store_with_node):
    store = store_with_node
    file_ref = FileRef(
        id="fr-1",
        node_id="leaf-1",
        path="src/a.py",
        lines="*",
        role="read",
        content_hash="abc",
        scanned_at="t",
        status="current",
    )
    store.add_file_ref(file_ref)
    store.delete_file_ref("fr-1")
    assert store.list_file_refs("demo", "leaf-1") == []


def test_check_file_refs_returns_stale(store_with_node):
    store = store_with_node
    store.add_file_ref(
        FileRef(
            id="fr-1",
            node_id="leaf-1",
            path="src/a.py",
            lines="*",
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
            content_hash="abc",
            scanned_at="t",
            status="stale",
        )
    )
    report = store.check_file_refs("demo", "leaf-1")
    assert report["total"] == 2
    assert report["stale"] == 1
    assert report["stale_paths"] == ["src/b.py"]
