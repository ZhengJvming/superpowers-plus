"""AC #8: leaf context packages stay isolated except for explicit shared ancestors and public dependency contracts."""

import json

import pytest


@pytest.fixture
def initialized(run_cli):
    run_cli("init", "--project", "ac8", "--embedding", "skip", "--non-interactive")
    return run_cli


def test_two_independent_leaves_have_disjoint_packages(initialized):
    initialized(
        "node",
        "create",
        "--id",
        "root",
        "--name",
        "root",
        "--type",
        "root",
        "--level",
        "0",
        "--description",
        "root",
        "--origin",
        "user_stated",
    )
    for branch, leaf in [("b1", "l1"), ("b2", "l2")]:
        initialized(
            "node",
            "create",
            "--id",
            branch,
            "--name",
            branch,
            "--type",
            "branch",
            "--level",
            "1",
            "--description",
            branch,
            "--origin",
            "user_stated",
        )
        initialized(
            "decision",
            "store",
            "--id",
            f"d-{branch}",
            "--node",
            branch,
            "--question",
            "q",
            "--options",
            "[]",
            "--chosen",
            "x",
            "--reasoning",
            "r",
        )
        initialized("edge", "add", "--kind", "hierarchy", "--from", "root", "--to", branch)
        initialized(
            "node",
            "create",
            "--id",
            leaf,
            "--name",
            leaf,
            "--type",
            "leaf",
            "--level",
            "2",
            "--description",
            f"{leaf} description",
            "--origin",
            "user_stated",
        )
        initialized(
            "interface",
            "add",
            "--id",
            f"i-{leaf}",
            "--node",
            leaf,
            "--name",
            "api",
            "--description",
            "d",
            "--spec",
            "GET /x returns {y: int}",
        )
        initialized("edge", "add", "--kind", "hierarchy", "--from", branch, "--to", leaf)

    p1 = json.loads(initialized("memory", "context", "--node", "l1").stdout)["data"]
    p2 = json.loads(initialized("memory", "context", "--node", "l2").stdout)["data"]

    assert p1["node"]["id"] == "l1"
    assert p2["node"]["id"] == "l2"

    p1_str = json.dumps(p1)
    p2_str = json.dumps(p2)
    assert "l2" not in p1_str
    assert "l1" not in p2_str

    a1_ids = {a["id"] for a in p1["ancestors"]}
    a2_ids = {a["id"] for a in p2["ancestors"]}
    assert a1_ids & a2_ids == {"root"}


def test_leaf_depending_on_another_sees_only_interfaces(initialized):
    initialized(
        "node",
        "create",
        "--id",
        "l1",
        "--name",
        "l1",
        "--type",
        "leaf",
        "--level",
        "1",
        "--description",
        "l1 work",
        "--origin",
        "user_stated",
    )
    initialized(
        "node",
        "create",
        "--id",
        "l2",
        "--name",
        "l2",
        "--type",
        "leaf",
        "--level",
        "1",
        "--description",
        "l2 SECRET internal description",
        "--origin",
        "user_stated",
    )
    initialized(
        "interface",
        "add",
        "--id",
        "i-l2",
        "--node",
        "l2",
        "--name",
        "PublicAPI",
        "--description",
        "public",
        "--spec",
        "GET /l2 returns {public: bool}",
    )
    initialized(
        "interface",
        "add",
        "--id",
        "i-l1",
        "--node",
        "l1",
        "--name",
        "L1API",
        "--description",
        "p",
        "--spec",
        "GET /l1 returns {ok: bool}",
    )
    initialized("edge", "add", "--kind", "dependency", "--from", "l1", "--to", "l2")
    p1 = json.loads(initialized("memory", "context", "--node", "l1").stdout)["data"]

    iface_specs = " ".join(i["spec"] for i in p1["interfaces"])
    assert "GET /l2 returns" in iface_specs
    assert "SECRET" not in json.dumps(p1["interfaces"])

    dep_blob = json.dumps(p1["deps"])
    assert "SECRET" not in dep_blob
