import json

import pytest


@pytest.fixture
def initialized(run_cli):
    run_cli("init", "--project", "demo", "--embedding", "skip", "--non-interactive")
    return run_cli


def _create_node(cli, nid, ntype="branch", level=1):
    cli(
        "node",
        "create",
        "--id",
        nid,
        "--name",
        nid,
        "--type",
        ntype,
        "--level",
        str(level),
        "--description",
        nid,
        "--origin",
        "user_stated",
    )


def test_edge_add_hierarchy(initialized):
    _create_node(initialized, "p", "root", 0)
    _create_node(initialized, "c", "leaf", 1)
    r = initialized("edge", "add", "--kind", "hierarchy", "--from", "p", "--to", "c", "--order", "0")
    assert json.loads(r.stdout)["ok"]


def test_edge_remove(initialized):
    _create_node(initialized, "a")
    _create_node(initialized, "b")
    initialized("edge", "add", "--kind", "dependency", "--from", "a", "--to", "b")
    r = initialized("edge", "remove", "--kind", "dependency", "--from", "a", "--to", "b")
    assert json.loads(r.stdout)["ok"]
