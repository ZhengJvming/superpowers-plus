"""Drives the full lifecycle a human/LLM would exercise."""

import json


def test_full_pyramid_lifecycle(run_cli):
    cli = run_cli

    r = cli("init", "--project", "ecommerce", "--embedding", "skip", "--non-interactive")
    assert json.loads(r.stdout)["ok"]

    cli(
        "node",
        "create",
        "--id",
        "root",
        "--name",
        "ecommerce",
        "--type",
        "root",
        "--level",
        "0",
        "--description",
        "online store with cart, payment, inventory",
        "--origin",
        "user_stated",
    )
    cli(
        "node",
        "create",
        "--id",
        "cart",
        "--name",
        "cart",
        "--type",
        "branch",
        "--level",
        "1",
        "--description",
        "shopping cart",
        "--origin",
        "user_stated",
    )
    cli(
        "node",
        "create",
        "--id",
        "pay",
        "--name",
        "payment",
        "--type",
        "branch",
        "--level",
        "1",
        "--description",
        "payment processing",
        "--origin",
        "user_stated",
    )
    cli(
        "node",
        "create",
        "--id",
        "inv",
        "--name",
        "inventory",
        "--type",
        "branch",
        "--level",
        "1",
        "--description",
        "stock tracking",
        "--origin",
        "skill_inferred",
    )
    cli(
        "node",
        "create",
        "--id",
        "cart-add",
        "--name",
        "add-item",
        "--type",
        "leaf",
        "--level",
        "2",
        "--description",
        "add item to cart endpoint",
        "--origin",
        "skill_inferred",
    )

    for child in ["cart", "pay", "inv"]:
        cli("edge", "add", "--kind", "hierarchy", "--from", "root", "--to", child)
    cli("edge", "add", "--kind", "hierarchy", "--from", "cart", "--to", "cart-add")
    cli("edge", "add", "--kind", "dependency", "--from", "cart-add", "--to", "inv")

    for node_id in ["cart", "pay", "inv"]:
        cli(
            "decision",
            "store",
            "--id",
            f"d-{node_id}",
            "--node",
            node_id,
            "--question",
            f"why split {node_id}?",
            "--options",
            "[]",
            "--chosen",
            "isolation",
            "--reasoning",
            "single responsibility",
        )

    cli(
        "interface",
        "add",
        "--id",
        "i-cart-add",
        "--node",
        "cart-add",
        "--name",
        "AddItem",
        "--description",
        "add item to cart",
        "--spec",
        "POST /cart/items {sku, qty} -> {cart_id, total}",
    )

    r = cli("memory", "validate")
    assert json.loads(r.stdout)["data"]["passed"] is True

    r = cli("memory", "stats")
    stats = json.loads(r.stdout)["data"]
    assert stats["total_nodes"] == 5
    assert stats["skill_inferred_node_ratio"] >= 0.3

    r = cli("memory", "recall", "--query", "add cart")
    matches = json.loads(r.stdout)["data"]["matches"]
    assert any(m["node"]["id"] == "cart-add" for m in matches)

    r = cli("memory", "context", "--node", "cart-add")
    pkg = json.loads(r.stdout)["data"]
    assert pkg["node"]["id"] == "cart-add"
    assert any(a["id"] == "cart" for a in pkg["ancestors"])
    assert any(a["id"] == "root" for a in pkg["ancestors"])
    assert any(d["chosen"] == "isolation" for d in pkg["decisions"])
    assert any(i["name"] == "AddItem" for i in pkg["interfaces"])
    assert any(d["id"] == "inv" for d in pkg["deps"])
    assert pkg["tokens_estimate"] > 0

    r = cli("query", "cycles")
    assert json.loads(r.stdout)["data"]["cycles"] == []

    r = cli("memory", "export")
    export = json.loads(r.stdout)["data"]
    assert len(export["nodes"]) == 5
