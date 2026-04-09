import json

import pytest


@pytest.fixture
def initialized(run_cli):
    run_cli("init", "--project", "demo", "--embedding", "skip", "--non-interactive")
    return run_cli


def test_interface_add_and_list(initialized):
    initialized(
        "node",
        "create",
        "--id",
        "n1",
        "--name",
        "n1",
        "--type",
        "leaf",
        "--level",
        "1",
        "--description",
        "x",
        "--origin",
        "user_stated",
    )
    r = initialized(
        "interface",
        "add",
        "--id",
        "i1",
        "--node",
        "n1",
        "--name",
        "login",
        "--description",
        "auth endpoint",
        "--spec",
        "POST /login (email,pwd)->token",
    )
    assert json.loads(r.stdout)["ok"]

    r2 = initialized("interface", "list", "--node", "n1")
    ifaces = json.loads(r2.stdout)["data"]["interfaces"]
    assert len(ifaces) == 1 and ifaces[0]["name"] == "login"
