import json


def test_recompute_tokens_updates_estimate(run_cli):
    run_cli("init", "--project", "demo", "--embedding", "skip", "--non-interactive")
    run_cli(
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
        "root",
        "--origin",
        "user_stated",
        "--tokens-estimate",
        "0",
    )
    run_cli(
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
        "a detailed leaf description with many words",
        "--origin",
        "user_stated",
        "--tokens-estimate",
        "0",
    )
    run_cli("edge", "add", "--kind", "hierarchy", "--from", "root", "--to", "leaf")
    run_cli(
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
        "long reasoning text here for token count",
        "--tradeoffs",
        "some tradeoffs",
    )
    run_cli(
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
        "GET /x returns {id, name, status, created_at}",
    )
    r = run_cli("memory", "recompute-tokens", "--node", "leaf")
    payload = json.loads(r.stdout)
    assert payload["ok"]
    assert payload["data"]["tokens_estimate"] > 0
    r2 = run_cli("node", "get", "--id", "leaf")
    assert json.loads(r2.stdout)["data"]["tokens_estimate"] > 0
