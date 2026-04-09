import json

import pytest


@pytest.fixture
def initialized(run_cli):
    run_cli("init", "--project", "demo", "--embedding", "skip", "--non-interactive")
    return run_cli


def test_check_leaf_criteria_returns_all_5(initialized):
    initialized(
        "node",
        "create",
        "--id",
        "n1",
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
    r = initialized("memory", "check-leaf-criteria", "--node", "n1")
    payload = json.loads(r.stdout)
    assert len(payload["data"]["criteria"]) == 5
    names = {c["criterion"] for c in payload["data"]["criteria"]}
    assert names == {
        "single_responsibility",
        "interface_clarity",
        "independent_testability",
        "token_budget",
        "closed_dependencies",
    }
