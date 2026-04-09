import subprocess
from pathlib import Path

from scripts.git_utils import compute_file_hash, git_changed_files, git_head_sha


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
