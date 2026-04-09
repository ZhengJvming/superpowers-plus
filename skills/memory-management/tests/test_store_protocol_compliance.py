import pytest

from scripts.cozo_store import CozoStore
from scripts.models import Decision, Edge, Interface, Node
from scripts.store import InMemoryStore


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


@pytest.fixture(params=["in_memory", "cozo"])
def store(request, tmp_path):
    if request.param == "in_memory":
        return InMemoryStore()

    s = CozoStore(db_path=str(tmp_path / "data.cozo"))
    s.ensure_schema()
    return s


def test_full_lifecycle_via_protocol(store):
    store.create_node(make_node("root", node_type="root", level=0))
    store.create_node(make_node("leaf", node_type="leaf", level=1))
    store.add_edge(Edge(kind="hierarchy", from_id="root", to_id="leaf"))
    store.store_decision(
        Decision(
            id="d1",
            node_id="root",
            question="q",
            options="[]",
            chosen="x",
            reasoning="r",
            tradeoffs="t",
            created_at="2026-04-07T00:00:00Z",
        )
    )
    store.add_interface(
        Interface(
            id="i1",
            node_id="leaf",
            name="api",
            description="d",
            spec="s",
            created_at="2026-04-07T00:00:00Z",
        )
    )

    pkg = store.assemble_context("demo", "leaf")
    assert pkg.node["id"] == "leaf"
    assert pkg.ancestors[0]["id"] == "root"
    assert pkg.decisions[0]["chosen"] == "x"
    assert pkg.interfaces[0]["name"] == "api"

    val = store.validate("demo")
    assert val["passed"] is True

    stats = store.stats("demo")
    assert stats["total_nodes"] == 2
