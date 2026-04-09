import json


def test_file_ref_add_and_list(run_cli):
    run_cli("init", "--project", "demo", "--embedding", "skip", "--non-interactive")
    run_cli(
        "node",
        "create",
        "--id",
        "leaf-1",
        "--name",
        "leaf",
        "--type",
        "leaf",
        "--level",
        "1",
        "--description",
        "a leaf",
        "--origin",
        "user_stated",
    )
    r = run_cli(
        "file-ref",
        "add",
        "--id",
        "fr-1",
        "--node",
        "leaf-1",
        "--path",
        "src/a.py",
        "--lines",
        "1-50",
        "--role",
        "modify",
        "--content-hash",
        "abc123",
    )
    assert json.loads(r.stdout)["ok"]
    r = run_cli("file-ref", "list", "--node", "leaf-1")
    refs = json.loads(r.stdout)["data"]["file_refs"]
    assert len(refs) == 1
    assert refs[0]["path"] == "src/a.py"
    assert refs[0]["status"] == "current"


def test_file_ref_check_reports_stale(run_cli):
    run_cli("init", "--project", "demo", "--embedding", "skip", "--non-interactive")
    run_cli(
        "node",
        "create",
        "--id",
        "leaf-1",
        "--name",
        "leaf",
        "--type",
        "leaf",
        "--level",
        "1",
        "--description",
        "a leaf",
        "--origin",
        "user_stated",
    )
    run_cli(
        "file-ref",
        "add",
        "--id",
        "fr-1",
        "--node",
        "leaf-1",
        "--path",
        "src/a.py",
        "--lines",
        "*",
        "--role",
        "modify",
        "--content-hash",
        "abc",
        "--status",
        "stale",
    )
    run_cli(
        "file-ref",
        "add",
        "--id",
        "fr-2",
        "--node",
        "leaf-1",
        "--path",
        "src/b.py",
        "--lines",
        "*",
        "--role",
        "read",
        "--content-hash",
        "def",
    )
    r = run_cli("file-ref", "check", "--node", "leaf-1")
    report = json.loads(r.stdout)["data"]
    assert report["total"] == 2
    assert report["stale"] == 1
    assert "src/a.py" in report["stale_paths"]
