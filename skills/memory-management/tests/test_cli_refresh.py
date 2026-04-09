import json
import subprocess
from pathlib import Path


def _init_git_repo(path: Path):
    subprocess.run(["git", "init"], cwd=path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "t@t.com"], cwd=path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=path, check=True, capture_output=True)
    (path / "src").mkdir()
    (path / "src" / "a.py").write_text("x = 1\n")
    subprocess.run(["git", "add", "."], cwd=path, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=path, check=True, capture_output=True)


def test_memory_refresh_marks_stale(run_cli_with_workspace, tmp_path):
    _init_git_repo(tmp_path)
    head_before = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=tmp_path, capture_output=True, text=True, check=True
    ).stdout.strip()

    cli = run_cli_with_workspace(tmp_path)
    cli("init", "--project", "demo", "--embedding", "skip", "--non-interactive")
    cli("config", "set", "--key", "scan.last_commit", "--value", head_before)
    cli("config", "set", "--key", "scan.project_root", "--value", str(tmp_path))
    cli(
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
        "d",
        "--origin",
        "user_stated",
    )
    cli(
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
        "old_hash",
    )

    (tmp_path / "src" / "a.py").write_text("x = 2\n")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "edit"], cwd=tmp_path, check=True, capture_output=True)

    r = cli("memory", "refresh")
    data = json.loads(r.stdout)["data"]
    assert data["marked_stale"] == 1
    assert "src/a.py" in data["stale_paths"]

    r2 = cli("file-ref", "check", "--node", "leaf-1")
    assert json.loads(r2.stdout)["data"]["stale"] == 1

    r3 = cli("config", "show")
    cfg_data = json.loads(r3.stdout)["data"]
    new_head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=tmp_path, capture_output=True, text=True, check=True
    ).stdout.strip()
    assert cfg_data.get("scan_last_commit") == new_head
