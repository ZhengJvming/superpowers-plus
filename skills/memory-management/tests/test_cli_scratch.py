import json


def test_scratch_write_and_list(run_cli):
    run_cli("init", "--project", "demo", "--embedding", "skip", "--non-interactive")
    r = run_cli(
        "scratch",
        "write",
        "--key",
        "api-limit",
        "--value",
        "Rate limit is 100/min",
        "--category",
        "must_persist",
        "--ttl",
        "persist",
    )
    assert json.loads(r.stdout)["ok"]

    r = run_cli("scratch", "list")
    entries = json.loads(r.stdout)["data"]["entries"]
    assert len(entries) == 1
    assert entries[0]["key"] == "api-limit"
    assert entries[0]["category"] == "must_persist"


def test_scratch_write_defaults(run_cli):
    run_cli("init", "--project", "demo", "--embedding", "skip", "--non-interactive")
    run_cli("scratch", "write", "--key", "temp", "--value", "some finding")
    r = run_cli("scratch", "list")
    entry = json.loads(r.stdout)["data"]["entries"][0]
    assert entry["category"] == "session_keep"
    assert entry["ttl"] == "session"


def test_scratch_list_by_category(run_cli):
    run_cli("init", "--project", "demo", "--embedding", "skip", "--non-interactive")
    run_cli("scratch", "write", "--key", "a", "--value", "x", "--category", "session_keep")
    run_cli("scratch", "write", "--key", "b", "--value", "y", "--category", "must_persist")
    r = run_cli("scratch", "list", "--category", "must_persist")
    entries = json.loads(r.stdout)["data"]["entries"]
    assert len(entries) == 1
    assert entries[0]["key"] == "b"


def test_scratch_promote_to_decision(run_cli):
    run_cli("init", "--project", "demo", "--embedding", "skip", "--non-interactive")
    run_cli(
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
        "r",
        "--origin",
        "user_stated",
    )
    run_cli(
        "scratch",
        "write",
        "--key",
        "no-redis",
        "--value",
        "User said: must not use Redis, use in-memory cache instead",
        "--category",
        "must_persist",
        "--ttl",
        "persist",
    )

    r = run_cli("scratch", "promote", "--key", "no-redis", "--node", "root", "--as", "decision")
    assert json.loads(r.stdout)["ok"]
    data = json.loads(r.stdout)["data"]
    assert data["promoted_as"] == "decision"

    r2 = run_cli("decision", "list", "--node", "root")
    decisions = json.loads(r2.stdout)["data"]["decisions"]
    assert any("Redis" in d["reasoning"] for d in decisions)

    r3 = run_cli("scratch", "list")
    entries = json.loads(r3.stdout)["data"]["entries"]
    assert all(e["key"] != "no-redis" for e in entries)


def test_scratch_promote_to_interface(run_cli):
    run_cli("init", "--project", "demo", "--embedding", "skip", "--non-interactive")
    run_cli(
        "node",
        "create",
        "--id",
        "leaf-1",
        "--name",
        "api",
        "--type",
        "leaf",
        "--level",
        "1",
        "--description",
        "payment api",
        "--origin",
        "user_stated",
    )
    run_cli(
        "scratch",
        "write",
        "--key",
        "pay-api-spec",
        "--value",
        "POST /pay {amount, currency} -> {tx_id, status}",
        "--category",
        "must_persist",
    )

    r = run_cli("scratch", "promote", "--key", "pay-api-spec", "--node", "leaf-1", "--as", "interface")
    assert json.loads(r.stdout)["ok"]

    r2 = run_cli("interface", "list", "--node", "leaf-1")
    interfaces = json.loads(r2.stdout)["data"]["interfaces"]
    assert len(interfaces) >= 1


def test_scratch_clear_session_only(run_cli):
    run_cli("init", "--project", "demo", "--embedding", "skip", "--non-interactive")
    run_cli("scratch", "write", "--key", "s1", "--value", "x", "--ttl", "session")
    run_cli("scratch", "write", "--key", "p1", "--value", "y", "--ttl", "persist")
    r = run_cli("scratch", "clear", "--ttl", "session")
    assert json.loads(r.stdout)["ok"]
    r2 = run_cli("scratch", "list")
    entries = json.loads(r2.stdout)["data"]["entries"]
    assert len(entries) == 1
    assert entries[0]["key"] == "p1"


def test_scratch_clear_all(run_cli):
    run_cli("init", "--project", "demo", "--embedding", "skip", "--non-interactive")
    run_cli("scratch", "write", "--key", "a", "--value", "x")
    run_cli("scratch", "write", "--key", "b", "--value", "y")
    run_cli("scratch", "clear")
    r = run_cli("scratch", "list")
    assert json.loads(r.stdout)["data"]["count"] == 0
