import json

import pytest


@pytest.fixture
def initialized(run_cli):
    run_cli("init", "--project", "demo", "--embedding", "skip", "--non-interactive")
    return run_cli


def test_context_assembles_full_package(initialized):
    initialized(
        "node",
        "create",
        "--id",
        "root",
        "--name",
        "r",
        "--type",
        "root",
        "--level",
        "0",
        "--description",
        "the root",
        "--origin",
        "user_stated",
    )
    initialized(
        "node",
        "create",
        "--id",
        "leaf",
        "--name",
        "l",
        "--type",
        "leaf",
        "--level",
        "1",
        "--description",
        "the leaf",
        "--origin",
        "skill_inferred",
    )
    initialized("edge", "add", "--kind", "hierarchy", "--from", "root", "--to", "leaf")
    initialized(
        "decision",
        "store",
        "--id",
        "d1",
        "--node",
        "root",
        "--question",
        "q?",
        "--options",
        "[]",
        "--chosen",
        "x",
        "--reasoning",
        "r",
        "--tradeoffs",
        "t",
    )
    initialized(
        "interface",
        "add",
        "--id",
        "i1",
        "--node",
        "leaf",
        "--name",
        "api",
        "--description",
        "d",
        "--spec",
        "GET /x",
    )

    r = initialized("memory", "context", "--node", "leaf")
    pkg = json.loads(r.stdout)["data"]
    assert pkg["node"]["id"] == "leaf"
    assert any(a["id"] == "root" for a in pkg["ancestors"])
    assert pkg["decisions"][0]["chosen"] == "x"
    assert pkg["interfaces"][0]["name"] == "api"
    assert pkg["tokens_estimate"] > 0
