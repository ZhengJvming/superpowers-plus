import json


def _seed_tree(cli):
    cli("init", "--project", "demo", "--embedding", "skip", "--non-interactive")
    cli(
        "node",
        "create",
        "--id",
        "root",
        "--name",
        "system",
        "--type",
        "root",
        "--level",
        "0",
        "--description",
        "top",
        "--origin",
        "user_stated",
    )
    cli(
        "node",
        "create",
        "--id",
        "auth",
        "--name",
        "auth",
        "--type",
        "branch",
        "--level",
        "1",
        "--description",
        "auth module",
        "--origin",
        "user_stated",
    )
    cli(
        "node",
        "create",
        "--id",
        "login",
        "--name",
        "login",
        "--type",
        "leaf",
        "--level",
        "2",
        "--description",
        "login page",
        "--origin",
        "skill_inferred",
    )
    cli("edge", "add", "--kind", "hierarchy", "--from", "root", "--to", "auth")
    cli("edge", "add", "--kind", "hierarchy", "--from", "auth", "--to", "login")


def test_tree_ascii_default(run_cli):
    _seed_tree(run_cli)
    r = run_cli("memory", "tree")
    out = json.loads(r.stdout)
    assert out["ok"]
    assert "system" in out["data"]["tree"]
    assert "auth" in out["data"]["tree"]
    assert "login" in out["data"]["tree"]
    assert out["data"]["format"] == "ascii"


def test_tree_mermaid_explicit(run_cli):
    _seed_tree(run_cli)
    r = run_cli("memory", "tree", "--format", "mermaid")
    out = json.loads(r.stdout)
    assert "graph TD" in out["data"]["tree"]
    assert out["data"]["format"] == "mermaid"


def test_tree_subtree_from_root(run_cli):
    _seed_tree(run_cli)
    r = run_cli("memory", "tree", "--root", "auth")
    tree = json.loads(r.stdout)["data"]["tree"]
    assert "auth" in tree
    assert "login" in tree
    assert "system" not in tree


def test_tree_mermaid_with_deps(run_cli):
    _seed_tree(run_cli)
    cli = run_cli
    cli(
        "node",
        "create",
        "--id",
        "pay",
        "--name",
        "payment",
        "--type",
        "leaf",
        "--level",
        "1",
        "--description",
        "pay",
        "--origin",
        "user_stated",
    )
    cli("edge", "add", "--kind", "hierarchy", "--from", "root", "--to", "pay")
    cli("edge", "add", "--kind", "dependency", "--from", "login", "--to", "pay")
    r = cli("memory", "tree", "--format", "mermaid", "--show-deps")
    tree = json.loads(r.stdout)["data"]["tree"]
    assert "-.->|depends|" in tree


def test_tree_respects_config_default(run_cli):
    _seed_tree(run_cli)
    run_cli("config", "set", "--key", "display.tree_format", "--value", "mermaid")
    r = run_cli("memory", "tree")
    out = json.loads(r.stdout)
    assert out["data"]["format"] == "mermaid"
