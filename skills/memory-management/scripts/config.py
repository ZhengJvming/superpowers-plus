from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib


SUPERPOWERS_DIR = Path(".superpowers")
PYRAMID_MEMORY_DIR = SUPERPOWERS_DIR / "pyramid-memory"


@dataclass
class Config:
    embedding_provider: str = "skip"
    db_path: str = str(PYRAMID_MEMORY_DIR / "data.cozo")
    default_project: Optional[str] = None
    initialized: bool = False
    display_tree_format: str = "ascii"
    scan_last_commit: Optional[str] = None
    scan_project_root: Optional[str] = None

    def expanded_db_path(self) -> str:
        return str(Path(self.db_path).expanduser().resolve())


def _walk_up(start: Path) -> Iterable[Path]:
    yield start
    yield from start.parents


def workspace_storage_dir(workspace_root: Path) -> Path:
    return workspace_root.resolve() / PYRAMID_MEMORY_DIR


def resolve_workspace_root(start: Path | None = None, explicit_root: Path | None = None) -> Path:
    if explicit_root is not None:
        return explicit_root.expanduser().resolve()

    current = (start or Path.cwd()).expanduser().resolve()
    if current.is_file():
        current = current.parent

    for candidate in _walk_up(current):
        if (candidate / PYRAMID_MEMORY_DIR / "config.toml").exists():
            return candidate

    for candidate in _walk_up(current):
        if (candidate / ".git").exists():
            return candidate

    return current


def default_db_path(workspace_root: Path | None = None, cwd: Path | None = None) -> Path:
    root = resolve_workspace_root(start=cwd, explicit_root=workspace_root)
    return workspace_storage_dir(root) / "data.cozo"


def load_config(path: Path) -> Config:
    path = path.expanduser().resolve()
    default_db = path.parent / "data.cozo"
    if not path.exists():
        return Config(db_path=str(default_db))

    with open(path, "rb") as f:
        data = tomllib.load(f)

    embedding = data.get("embedding", {})
    storage = data.get("storage", {})
    meta = data.get("meta", {})
    display = data.get("display", {})
    scan = data.get("scan", {})

    return Config(
        embedding_provider=embedding.get("provider", "skip"),
        db_path=storage.get("db_path", str(default_db)),
        default_project=meta.get("default_project"),
        initialized=meta.get("initialized", False),
        display_tree_format=display.get("tree_format", "ascii"),
        scan_last_commit=scan.get("last_commit"),
        scan_project_root=scan.get("project_root"),
    )


def save_config(path: Path, cfg: Config) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        "[embedding]",
        f'provider = "{cfg.embedding_provider}"',
        "",
        "[storage]",
        f'db_path = "{cfg.db_path}"',
        "",
        "[meta]",
        f"initialized = {'true' if cfg.initialized else 'false'}",
    ]
    if cfg.default_project:
        lines.append(f'default_project = "{cfg.default_project}"')
    lines.extend(
        [
            "",
            "[display]",
            f'tree_format = "{cfg.display_tree_format}"',
        ]
    )
    if cfg.scan_last_commit or cfg.scan_project_root:
        lines.extend(["", "[scan]"])
        if cfg.scan_last_commit:
            lines.append(f'last_commit = "{cfg.scan_last_commit}"')
        if cfg.scan_project_root:
            lines.append(f'project_root = "{cfg.scan_project_root}"')

    path.write_text("\n".join(lines) + "\n")


def default_config_path(workspace_root: Path | None = None, cwd: Path | None = None) -> Path:
    root = resolve_workspace_root(start=cwd, explicit_root=workspace_root)
    return workspace_storage_dir(root) / "config.toml"
