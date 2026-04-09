import json

import pytest


@pytest.fixture
def initialized(run_cli):
    run_cli("init", "--project", "demo", "--embedding", "skip", "--non-interactive")
    return run_cli


def test_validate_fails_branch_without_decision(initialized):
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
        "x",
        "--origin",
        "user_stated",
    )
    r = initialized("memory", "validate")
    payload = json.loads(r.stdout)["data"]
    assert payload["passed"] is False
    assert any(v["rule"] == "branch_requires_decision" for v in payload["violations"])


def test_validate_fails_leaf_without_interface(initialized):
    initialized(
        "node",
        "create",
        "--id",
        "l",
        "--name",
        "l",
        "--type",
        "leaf",
        "--level",
        "1",
        "--description",
        "x",
        "--origin",
        "user_stated",
    )
    r = initialized("memory", "validate")
    payload = json.loads(r.stdout)["data"]
    assert any(v["rule"] == "leaf_requires_interface" for v in payload["violations"])


def test_validate_passes_when_complete(initialized):
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
        "x",
        "--origin",
        "user_stated",
    )
    initialized(
        "decision",
        "store",
        "--id",
        "d1",
        "--node",
        "b",
        "--question",
        "q",
        "--options",
        "[]",
        "--chosen",
        "x",
        "--reasoning",
        "r",
    )
    initialized(
        "node",
        "create",
        "--id",
        "l",
        "--name",
        "l",
        "--type",
        "leaf",
        "--level",
        "2",
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
        "l",
        "--name",
        "api",
        "--description",
        "d",
        "--spec",
        "s",
    )
    r = initialized("memory", "validate")
    assert json.loads(r.stdout)["data"]["passed"] is True
