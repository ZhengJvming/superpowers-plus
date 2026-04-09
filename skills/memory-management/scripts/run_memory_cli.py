#!/usr/bin/env python3
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Iterable

try:
    from .runtime import build_runtime_env, memory_cli_script_path, resolve_runtime_paths
except ImportError:  # pragma: no cover - direct script execution fallback
    from runtime import build_runtime_env, memory_cli_script_path, resolve_runtime_paths  # type: ignore[no-redef]


def _extract_workspace_root(argv: Iterable[str]) -> tuple[Path | None, list[str]]:
    args = list(argv)
    if not args:
        return None, []

    if args[0] == "--workspace-root":
        if len(args) < 2:
            raise SystemExit("--workspace-root requires a path")
        return Path(args[1]).expanduser().resolve(), args[2:]

    return None, args


def build_launcher_command(
    argv: list[str],
    *,
    cwd: Path | None = None,
    environ: dict[str, str] | None = None,
) -> tuple[list[str], dict[str, str]]:
    explicit_root, passthrough = _extract_workspace_root(argv)
    paths = resolve_runtime_paths(start=cwd or Path.cwd(), explicit_root=explicit_root)
    env = build_runtime_env(paths.workspace_root, base_env=environ)
    cmd = [
        "uv",
        "run",
        str(memory_cli_script_path()),
        "--workspace-root",
        str(paths.workspace_root),
        *passthrough,
    ]
    return cmd, env


def main(argv: list[str] | None = None) -> int:
    cmd, env = build_launcher_command(argv or sys.argv[1:], cwd=Path.cwd(), environ=dict(os.environ))
    result = subprocess.run(cmd, env=env)
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
