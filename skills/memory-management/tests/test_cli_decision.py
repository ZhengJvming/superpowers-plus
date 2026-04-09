import json

import pytest


@pytest.fixture
def initialized(run_cli):
    run_cli("init", "--project", "demo", "--embedding", "skip", "--non-interactive")
    return run_cli


def test_decision_store_and_list(initialized):
    initialized(
        "node",
        "create",
        "--id",
        "n1",
        "--name",
        "n1",
        "--type",
        "branch",
        "--level",
        "1",
        "--description",
        "x",
        "--origin",
        "user_stated",
    )
    r = initialized(
        "decision",
        "store",
        "--id",
        "d1",
        "--node",
        "n1",
        "--question",
        "auth?",
        "--options",
        '["jwt","session"]',
        "--chosen",
        "jwt",
        "--reasoning",
        "stateless",
        "--tradeoffs",
        "revoke harder",
    )
    assert json.loads(r.stdout)["ok"]

    r2 = initialized("decision", "list", "--node", "n1")
    decisions = json.loads(r2.stdout)["data"]["decisions"]
    assert len(decisions) == 1 and decisions[0]["chosen"] == "jwt"
