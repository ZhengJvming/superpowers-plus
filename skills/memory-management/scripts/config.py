from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib


@dataclass
class Config:
    embedding_provider: str = "skip"
    db_path: str = "~/.pyramid-memory/data.cozo"
    default_project: Optional[str] = None
    initialized: bool = False

    def expanded_db_path(self) -> str:
        return str(Path(self.db_path).expanduser())


def load_config(path: Path) -> Config:
    if not path.exists():
        return Config()

    with open(path, "rb") as f:
        data = tomllib.load(f)

    embedding = data.get("embedding", {})
    storage = data.get("storage", {})
    meta = data.get("meta", {})

    return Config(
        embedding_provider=embedding.get("provider", "skip"),
        db_path=storage.get("db_path", "~/.pyramid-memory/data.cozo"),
        default_project=meta.get("default_project"),
        initialized=meta.get("initialized", False),
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

    path.write_text("\n".join(lines) + "\n")


def default_config_path() -> Path:
    return Path.home() / ".pyramid-memory" / "config.toml"
