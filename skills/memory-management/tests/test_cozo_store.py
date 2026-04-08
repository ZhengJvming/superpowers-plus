import pytest

from scripts.cozo_store import CozoStore
from scripts.models import Node


@pytest.fixture
def store(tmp_path):
    return CozoStore(db_path=str(tmp_path / "data.cozo"))


def make_node(id: str, **overrides):
    base = dict(
        id=id,
        project="demo",
        name=id,
        node_type="branch",
        level=1,
        description=f"node {id}",
        status="draft",
        origin="user_stated",
        tokens_estimate=0,
        created_at="2026-04-07T00:00:00Z",
        updated_at="2026-04-07T00:00:00Z",
    )
    base.update(overrides)
    return Node(**base)


def test_schema_bringup_idempotent(store):
    store.ensure_schema()
    store.ensure_schema()


def test_create_and_get_node(store):
    store.ensure_schema()
    store.create_node(make_node("n1"))
    got = store.get_node("demo", "n1")
    assert got.id == "n1"
    assert got.origin == "user_stated"


def test_create_duplicate_raises(store):
    store.ensure_schema()
    store.create_node(make_node("n1"))
    with pytest.raises(Exception):
        store.create_node(make_node("n1"))

def test_update_node_status(store):
    store.ensure_schema()
    store.create_node(make_node("n1"))
    store.update_node("demo", "n1", status="confirmed")
    assert store.get_node("demo", "n1").status == "confirmed"


def test_list_nodes_filter_by_status(store):
    store.ensure_schema()
    store.create_node(make_node("a", status="draft"))
    store.create_node(make_node("b", status="leaf"))
    drafts = store.list_nodes("demo", status="draft")
    assert [n.id for n in drafts] == ["a"]


def test_delete_node(store):
    store.ensure_schema()
    store.create_node(make_node("n1"))
    store.delete_node("demo", "n1")
    from scripts.store import NodeNotFound

    with pytest.raises(NodeNotFound):
        store.get_node("demo", "n1")
