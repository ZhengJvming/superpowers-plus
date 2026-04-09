"""AC #7: 5 independence criteria are mechanically enforced at leaf transition."""

import json

import pytest


@pytest.fixture
def initialized(run_cli):
    run_cli("init", "--project", "ac7", "--embedding", "skip", "--non-interactive")
    return run_cli


def test_cannot_mark_leaf_without_criteria_confirmed(initialized):
    initialized(
        "node",
        "create",
        "--id",
        "x",
        "--name",
        "x",
        "--type",
        "leaf",
        "--level",
        "1",
        "--description",
        "x",
        "--origin",
        "user_stated",
    )
    r = initialized("node", "update", "--id", "x", "--status", "leaf")
    assert json.loads(r.stdout)["error"]["code"] == "criteria_not_confirmed"


def test_cannot_mark_leaf_without_interface(initialized):
    initialized(
        "node",
        "create",
        "--id",
        "x",
        "--name",
        "x",
        "--type",
        "leaf",
        "--level",
        "1",
        "--description",
        "x",
        "--origin",
        "user_stated",
    )
    r = initialized("node", "update", "--id", "x", "--status", "leaf", "--criteria-confirmed")
    payload = json.loads(r.stdout)
    assert payload["error"]["code"] == "criteria_failed"
    assert "interface" in payload["error"]["message"].lower()


def test_cannot_mark_leaf_with_open_dep(initialized):
    initialized(
        "node",
        "create",
        "--id",
        "x",
        "--name",
        "x",
        "--type",
        "leaf",
        "--level",
        "1",
        "--description",
        "x",
        "--origin",
        "user_stated",
    )
    initialized(
        "interface",
        "add",
        "--id",
        "i1",
        "--node",
        "x",
        "--name",
        "api",
        "--description",
        "d",
        "--spec",
        "GET /x returns {y: int}",
    )
    initialized(
        "node",
        "create",
        "--id",
        "dep",
        "--name",
        "dep",
        "--type",
        "branch",
        "--level",
        "1",
        "--description",
        "dep",
        "--origin",
        "user_stated",
    )
    initialized("edge", "add", "--kind", "dependency", "--from", "x", "--to", "dep")
    r = initialized("node", "update", "--id", "x", "--status", "leaf", "--criteria-confirmed")
    payload = json.loads(r.stdout)
    assert payload["error"]["code"] == "criteria_failed"
    assert "dep" in payload["error"]["message"].lower()


def test_can_mark_leaf_when_all_pass(initialized):
    initialized(
        "node",
        "create",
        "--id",
        "x",
        "--name",
        "x",
        "--type",
        "leaf",
        "--level",
        "1",
        "--description",
        "x",
        "--origin",
        "user_stated",
    )
    initialized(
        "interface",
        "add",
        "--id",
        "i1",
        "--node",
        "x",
        "--name",
        "api",
        "--description",
        "d",
        "--spec",
        "GET /x returns {y: int}",
    )
    r = initialized("node", "update", "--id", "x", "--status", "leaf", "--criteria-confirmed")
    payload = json.loads(r.stdout)
    assert payload["ok"] is True
    assert payload["data"]["status"] == "leaf"
