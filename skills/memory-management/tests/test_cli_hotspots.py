import json
import subprocess
from pathlib import Path


def _init_repo(path: Path) -> Path:
    subprocess.run(["git", "init"], cwd=path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "t@t.com"], cwd=path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=path, check=True, capture_output=True)
    return path


def test_memory_hotspots_reports_top_changed_files(run_cli, tmp_path):
    repo = _init_repo(tmp_path)
    (repo / "hot.py").write_text("print('init')\n")
    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=repo, check=True, capture_output=True)

    for i in range(3):
        (repo / "hot.py").write_text(f"print({i})\n")
        subprocess.run(["git", "add", "hot.py"], cwd=repo, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", f"hot-{i}"], cwd=repo, check=True, capture_output=True)

    for i in range(2):
        (repo / "warm.py").write_text(f"warm = {i}\n")
        subprocess.run(["git", "add", "warm.py"], cwd=repo, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", f"warm-{i}"], cwd=repo, check=True, capture_output=True)

    run_cli(
        "init",
        "--project",
        "demo",
        "--embedding",
        "skip",
        "--non-interactive",
        cwd=repo,
    )
    run_cli("config", "set", "--key", "scan.project_root", "--value", str(repo), cwd=repo)

    response = run_cli("memory", "hotspots", "--days", "365", "--top", "2", cwd=repo)
    payload = json.loads(response.stdout)
    assert [row["path"] for row in payload["data"]["hotspots"]] == ["hot.py", "warm.py"]
    assert payload["data"]["hotspots"][0]["commit_count"] == 4
