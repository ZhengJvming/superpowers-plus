import subprocess
from pathlib import Path

from scripts.git_utils import compute_file_hash, git_change_hotspots, git_changed_files, git_head_sha


def _init_repo(tmp_path: Path) -> Path:
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "t@t.com"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=tmp_path, check=True, capture_output=True)
    (tmp_path / "a.py").write_text("print('hello')\n")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=tmp_path, check=True, capture_output=True)
    return tmp_path


def test_git_head_sha(tmp_path):
    repo = _init_repo(tmp_path)
    sha = git_head_sha(repo)
    assert len(sha) == 40


def test_git_changed_files_after_edit(tmp_path):
    repo = _init_repo(tmp_path)
    first_sha = git_head_sha(repo)
    (repo / "a.py").write_text("print('changed')\n")
    (repo / "b.py").write_text("new file\n")
    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "edit"], cwd=repo, check=True, capture_output=True)
    changed = git_changed_files(repo, first_sha)
    assert "a.py" in changed
    assert "b.py" in changed


def test_git_changed_files_same_commit(tmp_path):
    repo = _init_repo(tmp_path)
    sha = git_head_sha(repo)
    changed = git_changed_files(repo, sha)
    assert changed == []


def test_compute_file_hash(tmp_path):
    file_one = tmp_path / "x.txt"
    file_one.write_text("hello")
    hash_value = compute_file_hash(file_one)
    assert len(hash_value) == 64
    file_two = tmp_path / "y.txt"
    file_two.write_text("hello")
    assert compute_file_hash(file_two) == hash_value


def test_git_change_hotspots_ranks_by_commit_frequency(tmp_path):
    repo = _init_repo(tmp_path)
    for i in range(3):
        (repo / "hot.py").write_text(f"print({i})\n")
        subprocess.run(["git", "add", "hot.py"], cwd=repo, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", f"hot-{i}"], cwd=repo, check=True, capture_output=True)

    for i in range(2):
        (repo / "warm.py").write_text(f"warm = {i}\n")
        subprocess.run(["git", "add", "warm.py"], cwd=repo, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", f"warm-{i}"], cwd=repo, check=True, capture_output=True)

    hotspots = git_change_hotspots(repo, days=365, top=2)
    assert [row["path"] for row in hotspots] == ["hot.py", "warm.py"]
    assert hotspots[0]["commit_count"] == 3
    assert hotspots[0]["unique_authors"] == 1
    assert hotspots[1]["commit_count"] == 2
