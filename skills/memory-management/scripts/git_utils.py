"""Git helpers for freshness tracking."""

from __future__ import annotations

import hashlib
import subprocess
from collections import Counter, defaultdict
from pathlib import Path


def git_head_sha(project_root: Path) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=project_root,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def git_changed_files(project_root: Path, since_commit: str) -> list[str]:
    result = subprocess.run(
        ["git", "diff", "--name-only", since_commit, "HEAD"],
        cwd=project_root,
        capture_output=True,
        text=True,
        check=True,
    )
    return [line for line in result.stdout.strip().splitlines() if line]


def compute_file_hash(file_path: Path) -> str:
    digest = hashlib.sha256()
    with open(file_path, "rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_change_hotspots(project_root: Path, days: int = 90, top: int = 20) -> list[dict]:
    """Return files ranked by commit frequency within the given period."""
    result = subprocess.run(
        [
            "git",
            "log",
            f"--since={days} days ago",
            "--name-only",
            "--pretty=format:__COMMIT__|%ae",
        ],
        cwd=project_root,
        capture_output=True,
        text=True,
        check=True,
    )

    counts: Counter[str] = Counter()
    authors: dict[str, set[str]] = defaultdict(set)
    current_author: str | None = None

    for raw_line in result.stdout.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("__COMMIT__|"):
            current_author = line.split("|", 1)[1]
            continue
        counts[line] += 1
        if current_author:
            authors[line].add(current_author)

    ranked = counts.most_common(top)
    return [
        {
            "path": path,
            "commit_count": commit_count,
            "unique_authors": len(authors[path]),
        }
        for path, commit_count in ranked
    ]
