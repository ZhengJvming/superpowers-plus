import json

import pytest


@pytest.fixture
def initialized(run_cli):
    run_cli("init", "--project", "demo", "--embedding", "skip", "--non-interactive")
    return run_cli


def test_node_create_and_get(initialized):
    r = initialized(
        "node",
        "create",
        "--id",
        "n1",
        "--name",
        "root",
        "--type",
        "root",
        "--level",
        "0",
        "--description",
        "the root",
        "--origin",
        "user_stated",
    )
    assert r.returncode == 0
    payload = json.loads(r.stdout)
    assert payload["ok"] and payload["data"]["id"] == "n1"

    r2 = initialized("node", "get", "--id", "n1")
    assert json.loads(r2.stdout)["data"]["name"] == "root"


def test_node_list_filter_by_status(initialized):
    initialized(
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
        "x",
        "--origin",
        "user_stated",
    )
    initialized(
        "node",
        "create",
        "--id",
        "b",
        "--name",
        "b",
        "--type",
        "branch",
        "--level",
        "1",
        "--description",
        "y",
        "--origin",
        "skill_inferred",
        "--status",
        "confirmed",
    )
    r = initialized("node", "list", "--status", "confirmed")
    rows = json.loads(r.stdout)["data"]["nodes"]
    assert len(rows) == 1 and rows[0]["id"] == "b"


def test_node_update_status(initialized):
    initialized(
        "node",
        "create",
        "--id",
        "n1",
        "--name",
        "x",
        "--type",
        "branch",
        "--level",
        "1",
        "--description",
        "x",
        "--origin",
        "user_stated",
    )
    r = initialized("node", "update", "--id", "n1", "--status", "confirmed")
    assert json.loads(r.stdout)["data"]["status"] == "confirmed"


def test_node_delete(initialized):
    initialized(
        "node",
        "create",
        "--id",
        "n1",
        "--name",
        "x",
        "--type",
        "branch",
        "--level",
        "1",
        "--description",
        "x",
        "--origin",
        "user_stated",
    )
    r = initialized("node", "delete", "--id", "n1")
    assert json.loads(r.stdout)["ok"]
