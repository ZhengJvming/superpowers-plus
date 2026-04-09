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


def test_create_and_get_node():
    s = InMemoryStore()
    n = make_node("n1")
    s.create_node(n)
    got = s.get_node("demo", "n1")
    assert got.name == "n1"


def test_list_nodes_filters_by_project():
    s = InMemoryStore()
    s.create_node(make_node("a"))
    s.create_node(make_node("b", project="other"))
    nodes = s.list_nodes("demo")
    assert len(nodes) == 1 and nodes[0].id == "a"


def test_add_hierarchy_edge_and_query_children():
    s = InMemoryStore()
    s.create_node(make_node("p", node_type="root", level=0))
    s.create_node(make_node("c1", level=1))
    s.create_node(make_node("c2", level=1))
    s.add_edge(Edge(kind="hierarchy", from_id="p", to_id="c1", order_idx=0))
    s.add_edge(Edge(kind="hierarchy", from_id="p", to_id="c2", order_idx=1))
    children = s.query_children("demo", "p")
    assert [c.id for c in children] == ["c1", "c2"]


def test_recall_bm25_matches_description():
    s = InMemoryStore()
    s.create_node(make_node("a", description="implement OAuth login flow"))
    s.create_node(make_node("b", description="render dashboard charts"))
    results = s.recall("demo", query="oauth", k=5, semantic=False)
    assert len(results) >= 1
    assert results[0].node.id == "a"
    assert results[0].match_type == "bm25"


def test_check_leaf_criteria_passes_when_complete():
    s = InMemoryStore()
    s.create_node(make_node("leaf", node_type="leaf"))
    s.add_interface(
        Interface(
            id="i1",
            node_id="leaf",
            name="api",
            description="endpoint",
            spec="GET /x returns {y: int}",
            created_at="2026-04-07T00:00:00Z",
        )
    )
    report = s.check_leaf_criteria("demo", "leaf")
    assert report["mechanical_checks_pass"] is True
    c2 = next(c for c in report["criteria"] if c["criterion"] == "interface_clarity")
    assert c2["passes"] is True


def test_check_leaf_criteria_fails_no_interface():
    s = InMemoryStore()
    s.create_node(make_node("leaf", node_type="leaf"))
    report = s.check_leaf_criteria("demo", "leaf")
    assert report["mechanical_checks_pass"] is False
    c2 = next(c for c in report["criteria"] if c["criterion"] == "interface_clarity")
    assert c2["passes"] is False


def test_check_leaf_criteria_fails_open_dep():
    s = InMemoryStore()
    s.create_node(make_node("leaf", node_type="leaf"))
    s.create_node(make_node("dep", node_type="branch", status="draft"))
    s.add_edge(Edge(kind="dependency", from_id="leaf", to_id="dep"))
    s.add_interface(
        Interface(
            id="i1",
            node_id="leaf",
            name="x",
            description="x",
            spec="x" * 25,
            created_at="2026-04-07T00:00:00Z",
        )
    )
    report = s.check_leaf_criteria("demo", "leaf")
    c5 = next(c for c in report["criteria"] if c["criterion"] == "closed_dependencies")
    assert c5["passes"] is False
    assert "dep" in c5["reason"]
