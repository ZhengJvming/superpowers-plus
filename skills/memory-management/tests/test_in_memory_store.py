from scripts.models import Decision, Edge, Node
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
