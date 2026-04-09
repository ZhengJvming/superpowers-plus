import pytest

from scripts.cozo_store import CozoStore
from scripts.models import Edge, Node
from scripts.store import InMemoryStore


def make_node(id: str, **overrides):
    base = dict(
        id=id,
        project="demo",
        name=id,
        node_type="leaf",
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


@pytest.fixture(params=["in_memory", "cozo"])
def store(request, tmp_path):
    if request.param == "in_memory":
        return InMemoryStore()
    s = CozoStore(db_path=str(tmp_path / "data.cozo"))
    s.ensure_schema()
    return s


def _seed_graph(store):
    for node_id in ("a", "b", "c", "d", "e"):
        store.create_node(make_node(node_id))
    store.add_edge(Edge(kind="dependency", from_id="a", to_id="b"))
    store.add_edge(Edge(kind="dependency", from_id="b", to_id="c"))
    store.add_edge(Edge(kind="dependency", from_id="a", to_id="d"))
    store.add_edge(Edge(kind="dependency", from_id="e", to_id="b"))


def test_query_reverse_deps(store):
    _seed_graph(store)
    reverse = store.query_reverse_deps("demo", "b")
    assert {node.id for node in reverse} == {"a", "e"}


def test_query_impact_closure_downstream(store):
    _seed_graph(store)
    impacted = store.query_impact_closure("demo", "a", direction="downstream")
    assert {node.id for node in impacted} == {"b", "c", "d"}


def test_query_impact_closure_upstream(store):
    _seed_graph(store)
    impacted = store.query_impact_closure("demo", "c", direction="upstream")
    assert {node.id for node in impacted} == {"a", "b", "e"}


def test_query_impact_closure_handles_cycles(store):
    _seed_graph(store)
    store.add_edge(Edge(kind="dependency", from_id="c", to_id="a"))
    impacted = store.query_impact_closure("demo", "a", direction="downstream")
    assert {node.id for node in impacted} == {"b", "c", "d"}
