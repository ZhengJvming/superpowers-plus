from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

try:
    from .config import (
        default_config_path,
        default_db_path,
        resolve_workspace_root,
        workspace_storage_dir,
        workspace_superpowers_dir,
        workspace_uv_cache_dir,
    )
except ImportError:  # pragma: no cover - direct script execution fallback
    from config import (  # type: ignore[no-redef]
        default_config_path,
        default_db_path,
        resolve_workspace_root,
        workspace_storage_dir,
        workspace_superpowers_dir,
        workspace_uv_cache_dir,
    )

DEFAULT_INDEX_URL = "https://pypi.tuna.tsinghua.edu.cn/simple"
DEFAULT_INDEX_STRATEGY = "unsafe-best-match"


@dataclass(frozen=True)
class RuntimePaths:
    workspace_root: Path
    superpowers_dir: Path
    memory_dir: Path
    uv_cache_dir: Path
    config_path: Path
    db_path: Path


def resolve_runtime_paths(start: Path | None = None, explicit_root: Path | None = None) -> RuntimePaths:
    workspace_root = resolve_workspace_root(start=start, explicit_root=explicit_root)
    return RuntimePaths(
        workspace_root=workspace_root,
        superpowers_dir=workspace_superpowers_dir(workspace_root),
        memory_dir=workspace_storage_dir(workspace_root),
        uv_cache_dir=workspace_uv_cache_dir(workspace_root),
        config_path=default_config_path(workspace_root=workspace_root),
        db_path=default_db_path(workspace_root=workspace_root),
    )


def build_runtime_env(
    workspace_root: Path,
    base_env: Mapping[str, str] | None = None,
) -> dict[str, str]:
    env = dict(base_env or os.environ)
    env.setdefault("UV_INDEX_URL", DEFAULT_INDEX_URL)
    env.setdefault("UV_INDEX_STRATEGY", DEFAULT_INDEX_STRATEGY)
    env["UV_CACHE_DIR"] = str(workspace_uv_cache_dir(workspace_root))
    return env


def memory_cli_script_path() -> Path:
    return Path(__file__).resolve().with_name("memory_cli.py")
