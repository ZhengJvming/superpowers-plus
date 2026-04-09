"""Auto-trigger protocol integration."""

import json
import subprocess


def _init_repo(path):
    subprocess.run(["git", "init"], cwd=path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "t@t.com"], cwd=path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=path, check=True, capture_output=True)
    (path / "src").mkdir()
    (path / "src" / "payment.py").write_text("class Payment: pass\n")
    subprocess.run(["git", "add", "."], cwd=path, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=path, check=True, capture_output=True)


def test_auto_trigger_full_cycle(run_cli_with_workspace, tmp_path):
    repo = tmp_path
    _init_repo(repo)
    head_v1 = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo, capture_output=True, text=True, check=True
    ).stdout.strip()

    cli = run_cli_with_workspace(repo)
    cli("init", "--project", "demo", "--embedding", "skip", "--non-interactive")
    cli("config", "set", "--key", "scan.last_commit", "--value", head_v1)
    cli("config", "set", "--key", "scan.project_root", "--value", str(repo))

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
        "r",
        "--origin",
        "user_stated",
    )
    cli(
        "node",
        "create",
        "--id",
        "pay-leaf",
        "--name",
        "payment",
        "--type",
        "leaf",
        "--level",
        "1",
        "--description",
        "payment module",
        "--origin",
        "user_stated",
    )
    cli("edge", "add", "--kind", "hierarchy", "--from", "root", "--to", "pay-leaf")
    cli(
        "file-ref",
        "add",
        "--id",
        "fr-pay",
        "--node",
        "pay-leaf",
        "--path",
        "src/payment.py",
        "--lines",
        "*",
        "--role",
        "modify",
        "--content-hash",
        "original_hash",
    )

    (repo / "src" / "payment.py").write_text("class Payment:\n    def charge(self): ...\n")
    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "add charge method"], cwd=repo, check=True, capture_output=True)

    freshness = json.loads(cli("memory", "freshness").stdout)["data"]
    assert freshness["status"] == "stale"
    assert "src/payment.py" in freshness["changed_files"]

    refresh = json.loads(cli("memory", "refresh").stdout)["data"]
    assert refresh["marked_stale"] == 1
    assert "src/payment.py" in refresh["stale_paths"]

    ctx = json.loads(cli("memory", "context", "--node", "pay-leaf").stdout)["data"]
    assert len(ctx["file_refs"]) == 1
    file_ref = ctx["file_refs"][0]
    assert file_ref["status"] == "stale"
    assert "warning" in file_ref
    assert "stale" in file_ref["warning"].lower()
