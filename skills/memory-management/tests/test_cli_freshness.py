import json
import subprocess
from pathlib import Path


def _init_git_repo(path: Path):
    subprocess.run(["git", "init"], cwd=path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "t@t.com"], cwd=path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=path, check=True, capture_output=True)
    (path / "a.py").write_text("x = 1\n")
    subprocess.run(["git", "add", "."], cwd=path, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=path, check=True, capture_output=True)


def test_memory_freshness_no_changes(run_cli_with_workspace, tmp_path):
    _init_git_repo(tmp_path)
    cli = run_cli_with_workspace(tmp_path)
    cli("init", "--project", "demo", "--embedding", "skip", "--non-interactive")
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=tmp_path, capture_output=True, text=True, check=True
    ).stdout.strip()
    cli("config", "set", "--key", "scan.last_commit", "--value", head)
    cli("config", "set", "--key", "scan.project_root", "--value", str(tmp_path))
    r = cli("memory", "freshness")
    data = json.loads(r.stdout)["data"]
    assert data["status"] == "fresh"
    assert data["changed_files"] == []


def test_memory_freshness_with_changes(run_cli_with_workspace, tmp_path):
    _init_git_repo(tmp_path)
    head_before = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=tmp_path, capture_output=True, text=True, check=True
    ).stdout.strip()

    cli = run_cli_with_workspace(tmp_path)
    cli("init", "--project", "demo", "--embedding", "skip", "--non-interactive")
    cli("config", "set", "--key", "scan.last_commit", "--value", head_before)
    cli("config", "set", "--key", "scan.project_root", "--value", str(tmp_path))

    (tmp_path / "a.py").write_text("x = 2\n")
    (tmp_path / "b.py").write_text("new\n")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "edit"], cwd=tmp_path, check=True, capture_output=True)

    r = cli("memory", "freshness")
    data = json.loads(r.stdout)["data"]
    assert data["status"] == "stale"
    assert "a.py" in data["changed_files"]
    assert "b.py" in data["changed_files"]


def test_memory_freshness_no_scan_config(run_cli):
    run_cli("init", "--project", "demo", "--embedding", "skip", "--non-interactive")
    r = run_cli("memory", "freshness")
    data = json.loads(r.stdout)["data"]
    assert data["status"] == "unknown"
