from scripts.models import ContextPackage, Decision, Edge, FileRef, Interface, Node, ScratchEntry, ScoredNode


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


def test_file_ref_dataclass():
    fr = FileRef(
        id="fr-1",
        node_id="leaf-1",
        path="src/payment/service.py",
        lines="45-120",
        role="modify",
        content_hash="abc123",
        scanned_at="2026-04-09T00:00:00Z",
        status="current",
    )
    d = fr.to_dict()
    assert d["id"] == "fr-1"
    assert d["role"] == "modify"
    assert d["status"] == "current"
    fr2 = FileRef.from_dict(d)
    assert fr2 == fr


def test_context_package_includes_file_refs():
    pkg = ContextPackage(
        node={"id": "x"},
        ancestors=[],
        decisions=[],
        interfaces=[],
        deps=[],
        tokens_estimate=100,
        file_refs=[{"id": "fr-1", "path": "a.py", "status": "current"}],
    )
    d = pkg.to_dict()
    assert len(d["file_refs"]) == 1
    assert d["file_refs"][0]["path"] == "a.py"


def test_scratch_entry_dataclass():
    entry = ScratchEntry(
        key="api-rate-limit",
        value="Payment API rate limit is 100/min",
        category="must_persist",
        ttl="session",
        created_at="2026-04-09T10:00:00Z",
    )
    d = entry.to_dict()
    assert d["key"] == "api-rate-limit"
    assert d["category"] == "must_persist"
    assert ScratchEntry.from_dict(d) == entry


def test_scratch_entry_defaults():
    entry = ScratchEntry(
        key="temp",
        value="something",
        created_at="2026-04-09T10:00:00Z",
    )
    assert entry.category == "session_keep"
    assert entry.ttl == "session"
