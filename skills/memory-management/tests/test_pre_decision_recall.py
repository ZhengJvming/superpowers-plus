import json


def test_pre_decision_recall_gate_inputs_available(run_cli):
    cli = run_cli
    cli("init", "--project", "demo", "--embedding", "skip", "--non-interactive")
    cli(
        "node",
        "create",
        "--id",
        "root",
        "--name",
        "root",
        "--type",
        "root",
        "--level",
        "0",
        "--description",
        "system",
        "--origin",
        "user_stated",
    )
    cli(
        "node",
        "create",
        "--id",
        "leaf-1",
        "--name",
        "payments",
        "--type",
        "leaf",
        "--level",
        "1",
        "--description",
        "payment flow",
        "--origin",
        "skill_inferred",
    )
    cli("edge", "add", "--kind", "hierarchy", "--from", "root", "--to", "leaf-1")
    cli(
        "decision",
        "store",
        "--id",
        "d1",
        "--node",
        "root",
        "--question",
        "How to split payments?",
        "--options",
        "[]",
        "--chosen",
        "service",
        "--reasoning",
        "Keep payment logic isolated",
        "--tradeoffs",
        "More explicit interfaces",
    )
    cli(
        "scratch",
        "write",
        "--key",
        "user-constraint",
        "--value",
        "Must not use Redis",
        "--category",
        "must_persist",
        "--ttl",
        "persist",
    )

    scratch = json.loads(cli("scratch", "list").stdout)["data"]["entries"]
    recall = json.loads(cli("memory", "recall", "--query", "payment logic", "--k", "3").stdout)["data"][
        "matches"
    ]
    ancestors = json.loads(cli("query", "ancestors", "--id", "leaf-1", "--summary").stdout)["data"][
        "nodes"
    ]

    assert scratch[0]["key"] == "user-constraint"
    assert recall[0]["node"]["id"] in {"root", "leaf-1"}
    assert ancestors[0]["id"] == "root"
