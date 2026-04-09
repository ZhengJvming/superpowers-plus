import json

import pytest


@pytest.fixture
def initialized(run_cli):
    run_cli("init", "--project", "demo", "--embedding", "skip", "--non-interactive")
    return run_cli


def test_stats_inferred_ratio(initialized):
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
        "x",
        "--origin",
        "skill_inferred",
    )
    initialized(
        "node",
        "create",
        "--id",
        "c",
        "--name",
        "c",
        "--type",
        "branch",
        "--level",
        "1",
        "--description",
        "x",
        "--origin",
        "skill_inferred",
    )
    r = initialized("memory", "stats")
    s = json.loads(r.stdout)["data"]
    assert s["total_nodes"] == 3
    assert s["skill_inferred_nodes"] == 2
    assert abs(s["skill_inferred_node_ratio"] - 0.6667) < 0.001
