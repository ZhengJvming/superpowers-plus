from scripts.models import Node
from scripts.tree_renderer import render_ascii, render_mermaid


def _make_node(node_id, name, node_type, level, status="draft"):
    return Node(
        id=node_id,
        project="demo",
        name=name,
        node_type=node_type,
        level=level,
        description=f"{name} desc",
        status=status,
        origin="user_stated",
        tokens_estimate=0,
        created_at="t",
        updated_at="t",
    )


def _sample_tree():
    nodes = {
        "root": _make_node("root", "system", "root", 0, "done"),
        "auth": _make_node("auth", "auth", "branch", 1, "done"),
        "payment": _make_node("payment", "payment", "branch", 1, "draft"),
        "login": _make_node("login", "login", "leaf", 2, "done"),
        "register": _make_node("register", "register", "leaf", 2, "in_progress"),
    }
    children = {
        "root": ["auth", "payment"],
        "auth": ["login", "register"],
        "payment": [],
        "login": [],
        "register": [],
    }
    return nodes, children


def test_ascii_basic_structure():
    nodes, children = _sample_tree()
    output = render_ascii("root", nodes, children)
    assert "system" in output
    assert "auth" in output
    assert "login" in output
    assert "├" in output or "└" in output


def test_ascii_shows_status():
    nodes, children = _sample_tree()
    output = render_ascii("root", nodes, children)
    assert "done" in output
    assert "draft" in output


def test_ascii_leaf_done_has_checkmark():
    nodes, children = _sample_tree()
    output = render_ascii("root", nodes, children)
    login_line = [line for line in output.strip().splitlines() if "login" in line][0]
    assert "✓" in login_line


def test_mermaid_valid_syntax():
    nodes, children = _sample_tree()
    output = render_mermaid("root", nodes, children)
    assert output.startswith("graph TD")
    assert "-->" in output


def test_mermaid_has_class_defs():
    nodes, children = _sample_tree()
    output = render_mermaid("root", nodes, children)
    assert "classDef" in output


def test_mermaid_includes_all_nodes():
    nodes, children = _sample_tree()
    output = render_mermaid("root", nodes, children)
    for name in ["system", "auth", "payment", "login", "register"]:
        assert name in output


def test_mermaid_node_types_styled():
    nodes, children = _sample_tree()
    nodes["existing"] = _make_node("existing", "legacy", "existing_module", 1, "done")
    children["root"].append("existing")
    children["existing"] = []
    output = render_mermaid("root", nodes, children)
    assert "legacy" in output


def test_mermaid_with_deps():
    nodes, children = _sample_tree()
    dep_edges = [("login", "register")]
    output = render_mermaid("root", nodes, children, dep_edges=dep_edges)
    assert "-.->" in output
