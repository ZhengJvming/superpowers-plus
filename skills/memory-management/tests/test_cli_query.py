import json

import pytest


@pytest.fixture
def initialized(run_cli):
    run_cli("init", "--project", "demo", "--embedding", "skip", "--non-interactive")
    return run_cli


def _seed_pyramid(cli):
    cli(
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
    cli(
        "node",
        "create",
        "--id",
        "a",
        "--name",
        "a",
        "--type",
        "branch",
        "--level",
        "1",
        "--description",
        "a",
        "--origin",
        "user_stated",
    )
    cli(
        "node",
        "create",
        "--id",
        "b",
        "--name",
        "b",
        "--type",
        "leaf",
        "--level",
        "2",
        "--description",
        "b",
        "--origin",
        "skill_inferred",
    )
    cli("edge", "add", "--kind", "hierarchy", "--from", "root", "--to", "a")
    cli("edge", "add", "--kind", "hierarchy", "--from", "a", "--to", "b")


def test_query_children(initialized):
    _seed_pyramid(initialized)
    r = initialized("query", "children", "--id", "root")
    payload = json.loads(r.stdout)
    assert [n["id"] for n in payload["data"]["nodes"]] == ["a"]


def test_query_ancestors(initialized):
    _seed_pyramid(initialized)
    r = initialized("query", "ancestors", "--id", "b")
    payload = json.loads(r.stdout)
    assert [n["id"] for n in payload["data"]["nodes"]] == ["a", "root"]


def test_query_ancestors_summary(initialized):
    _seed_pyramid(initialized)
    r = initialized("query", "ancestors", "--id", "b", "--summary")
    nodes = json.loads(r.stdout)["data"]["nodes"]
    assert len(nodes) == 2
    for n in nodes:
        assert set(n.keys()) == {"id", "name", "description", "status", "level", "node_type"}


def test_query_subtree(initialized):
    _seed_pyramid(initialized)
    r = initialized("query", "subtree", "--root", "root")
    ids = sorted(n["id"] for n in json.loads(r.stdout)["data"]["nodes"])
    assert ids == ["a", "b", "root"]


def test_query_cycles_empty(initialized):
    _seed_pyramid(initialized)
    r = initialized("query", "cycles")
    assert json.loads(r.stdout)["data"]["cycles"] == []


def test_query_deps_of(initialized):
    _seed_pyramid(initialized)
    initialized(
        "node",
        "create",
        "--id",
        "c",
        "--name",
        "c",
        "--type",
        "leaf",
        "--level",
        "2",
        "--description",
        "c",
        "--origin",
        "skill_inferred",
    )
    initialized("edge", "add", "--kind", "dependency", "--from", "a", "--to", "b")
    initialized("edge", "add", "--kind", "dependency", "--from", "c", "--to", "b")
    r = initialized("query", "deps-of", "--id", "b")
    ids = {n["id"] for n in json.loads(r.stdout)["data"]["nodes"]}
    assert ids == {"a", "c"}


def test_query_impact_downstream(initialized):
    _seed_pyramid(initialized)
    initialized(
        "node",
        "create",
        "--id",
        "c",
        "--name",
        "c",
        "--type",
        "leaf",
        "--level",
        "2",
        "--description",
        "c",
        "--origin",
        "skill_inferred",
    )
    initialized("edge", "add", "--kind", "dependency", "--from", "a", "--to", "b")
    initialized("edge", "add", "--kind", "dependency", "--from", "b", "--to", "c")
    r = initialized("query", "impact", "--id", "a", "--direction", "downstream")
    ids = {n["id"] for n in json.loads(r.stdout)["data"]["nodes"]}
    assert ids == {"b", "c"}


def test_query_impact_upstream(initialized):
    _seed_pyramid(initialized)
    initialized("edge", "add", "--kind", "dependency", "--from", "a", "--to", "b")
    r = initialized("query", "impact", "--id", "b", "--direction", "upstream")
    ids = [n["id"] for n in json.loads(r.stdout)["data"]["nodes"]]
    assert ids == ["a"]
