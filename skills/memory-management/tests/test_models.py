from scripts.models import ContextPackage, Decision, Edge, Interface, Node, ScoredNode


def test_node_to_dict_roundtrip():
    n = Node(
        id="n1",
        project="demo",
        name="root",
        node_type="root",
        level=0,
        description="root node",
        status="draft",
        origin="user_stated",
        tokens_estimate=100,
        created_at="2026-04-07T00:00:00Z",
        updated_at="2026-04-07T00:00:00Z",
    )
    d = n.to_dict()
    assert d["id"] == "n1"
    assert d["origin"] == "user_stated"
    n2 = Node.from_dict(d)
    assert n2 == n


def test_edge_kinds():
    e1 = Edge(kind="hierarchy", from_id="a", to_id="b", order_idx=0)
    e2 = Edge(kind="dependency", from_id="b", to_id="c", dep_type="requires")
    assert e1.kind == "hierarchy"
    assert e2.dep_type == "requires"


def test_context_package_token_count():
    pkg = ContextPackage(
        node={"id": "leaf"},
        ancestors=[],
        decisions=[],
        interfaces=[],
        deps=[],
        tokens_estimate=4200,
    )
    assert pkg.tokens_estimate == 4200
