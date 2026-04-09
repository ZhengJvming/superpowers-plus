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
from scripts.models import Edge


def test_hierarchy_children_ordered(store):
    store.ensure_schema()
    store.create_node(make_node("p", node_type="root", level=0))
    store.create_node(make_node("c1", level=1))
    store.create_node(make_node("c2", level=1))
    store.add_edge(Edge(kind="hierarchy", from_id="p", to_id="c2", order_idx=1))
    store.add_edge(Edge(kind="hierarchy", from_id="p", to_id="c1", order_idx=0))
    children = store.query_children("demo", "p")
    assert [c.id for c in children] == ["c1", "c2"]


def test_query_ancestors(store):
    store.ensure_schema()
    store.create_node(make_node("a", level=0, node_type="root"))
    store.create_node(make_node("b", level=1))
    store.create_node(make_node("c", level=2))
    store.add_edge(Edge(kind="hierarchy", from_id="a", to_id="b"))
    store.add_edge(Edge(kind="hierarchy", from_id="b", to_id="c"))
    chain = store.query_ancestors("demo", "c")
    assert [n.id for n in chain] == ["b", "a"]


def test_query_deps_and_cycles(store):
    store.ensure_schema()
    store.create_node(make_node("a"))
    store.create_node(make_node("b"))
    store.create_node(make_node("c"))
    store.add_edge(Edge(kind="dependency", from_id="a", to_id="b"))
    store.add_edge(Edge(kind="dependency", from_id="b", to_id="c"))
    deps = store.query_deps("demo", "a")
    assert [d.id for d in deps] == ["b"]
    assert store.detect_cycles("demo") == []
    store.add_edge(Edge(kind="dependency", from_id="c", to_id="a"))
    cycles = store.detect_cycles("demo")
    assert len(cycles) == 1
from scripts.models import Decision, Interface


def test_store_and_list_decision(store):
    store.ensure_schema()
    store.create_node(make_node("n1"))
    store.store_decision(
        Decision(
            id="d1",
            node_id="n1",
            question="auth?",
            options='["jwt","session"]',
            chosen="jwt",
            reasoning="stateless",
            tradeoffs="revocation harder",
            created_at="2026-04-07T00:00:00Z",
        )
    )
    decisions = store.list_decisions("demo", "n1")
    assert len(decisions) == 1 and decisions[0].chosen == "jwt"


def test_add_and_list_interface(store):
    store.ensure_schema()
    store.create_node(make_node("n1"))
    store.add_interface(
        Interface(
            id="i1",
            node_id="n1",
            name="login",
            description="auth endpoint",
            spec="POST /login (email,pwd)->token",
            created_at="2026-04-07T00:00:00Z",
        )
    )
    ifaces = store.list_interfaces("demo", "n1")
    assert ifaces[0].name == "login"


def test_recall_bm25(store):
    store.ensure_schema()
    store.create_node(make_node("a", description="implement OAuth login"))
    store.create_node(make_node("b", description="render dashboard"))
    results = store.recall("demo", query="oauth", k=5, semantic=False)
    assert results and results[0].node.id == "a"


def test_assemble_context_includes_ancestors_and_decisions(store):
    store.ensure_schema()
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
            name="iface",
            description="d",
            spec="s",
            created_at="2026-04-07T00:00:00Z",
        )
    )
    pkg = store.assemble_context("demo", "leaf")
    assert pkg.node["id"] == "leaf"
    assert any(a["id"] == "root" for a in pkg.ancestors)
    assert pkg.decisions and pkg.decisions[0]["chosen"] == "x"
    assert pkg.interfaces and pkg.interfaces[0]["name"] == "iface"


def test_validate_branch_requires_decision(store):
    store.ensure_schema()
    store.create_node(make_node("b", node_type="branch"))
    result = store.validate("demo")
    assert not result["passed"]
    assert any(v["rule"] == "branch_requires_decision" for v in result["violations"])


def test_validate_leaf_requires_interface(store):
    store.ensure_schema()
    store.create_node(make_node("l", node_type="leaf"))
    result = store.validate("demo")
    assert any(v["rule"] == "leaf_requires_interface" for v in result["violations"])


def test_stats_inferred_ratio(store):
    store.ensure_schema()
    store.create_node(make_node("a", origin="user_stated"))
    store.create_node(make_node("b", origin="skill_inferred"))
    store.create_node(make_node("c", origin="skill_inferred"))
    s = store.stats("demo")
    assert s["total_nodes"] == 3
    assert s["skill_inferred_nodes"] == 2
    assert abs(s["skill_inferred_node_ratio"] - 0.6667) < 0.001


def test_cozo_check_leaf_criteria_full(store):
    store.ensure_schema()
    store.create_node(make_node("leaf", node_type="leaf"))
    store.add_interface(
        Interface(
            id="i1",
            node_id="leaf",
            name="api",
            description="d",
            spec="GET /resource returns {id, name, status}",
            created_at="2026-04-07T00:00:00Z",
        )
    )
    report = store.check_leaf_criteria("demo", "leaf")
    assert report["mechanical_checks_pass"] is True
    assert len(report["criteria"]) == 5
