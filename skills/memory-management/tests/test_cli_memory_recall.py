import json

import pytest


@pytest.fixture
def initialized(run_cli):
    run_cli("init", "--project", "demo", "--embedding", "skip", "--non-interactive")
    return run_cli


@pytest.fixture
def initialized_fastembed(run_cli):
    run_cli("init", "--project", "demo", "--embedding", "fastembed", "--non-interactive")
    return run_cli


def test_recall_bm25_finds_match(initialized):
    initialized(
        "node",
        "create",
        "--id",
        "a",
        "--name",
        "auth-flow",
        "--type",
        "leaf",
        "--level",
        "1",
        "--description",
        "implement OAuth login flow",
        "--origin",
        "user_stated",
    )
    initialized(
        "node",
        "create",
        "--id",
        "b",
        "--name",
        "dashboard",
        "--type",
        "leaf",
        "--level",
        "1",
        "--description",
        "render charts",
        "--origin",
        "user_stated",
    )
    r = initialized("memory", "recall", "--query", "oauth", "--k", "3")
    payload = json.loads(r.stdout)
    matches = payload["data"]["matches"]
    assert matches and matches[0]["node"]["id"] == "a"
    assert matches[0]["match_type"] == "bm25"


@pytest.mark.skipif_fastembed_unavailable
def test_recall_semantic_finds_paraphrase(initialized_fastembed):
    cli = initialized_fastembed
    cli(
        "node",
        "create",
        "--id",
        "a",
        "--name",
        "auth",
        "--type",
        "leaf",
        "--level",
        "1",
        "--description",
        "user authentication via OAuth2",
        "--origin",
        "user_stated",
    )
    cli(
        "node",
        "create",
        "--id",
        "b",
        "--name",
        "viz",
        "--type",
        "leaf",
        "--level",
        "1",
        "--description",
        "draw bar charts",
        "--origin",
        "user_stated",
    )
    r = cli("memory", "recall", "--query", "login system", "--semantic", "--k", "3")
    matches = json.loads(r.stdout)["data"]["matches"]
    assert matches and matches[0]["node"]["id"] == "a"
    assert matches[0]["match_type"] == "semantic"
