#!/usr/bin/env python3
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Callable, Iterable

try:
    from .runtime import (
        build_runtime_env,
        index_fallback_urls,
        memory_cli_script_path,
        resolve_runtime_paths,
    )
except ImportError:  # pragma: no cover - direct script execution fallback
    from runtime import (  # type: ignore[no-redef]
        build_runtime_env,
        index_fallback_urls,
        memory_cli_script_path,
        resolve_runtime_paths,
    )


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


def should_retry_with_next_index(returncode: int, stderr: str) -> bool:
    if returncode == 0:
        return False
    lowered = stderr.lower()
    return (
        "403 forbidden" in lowered
        or "failed to unzip wheel" in lowered
        or "timed out" in lowered
        or "connection reset" in lowered
    )


def run_with_fallback(
    cmd: list[str],
    env: dict[str, str],
    *,
    base_environ: dict[str, str] | None = None,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> tuple[int, str, str]:
    urls = index_fallback_urls(base_environ)
    last = subprocess.CompletedProcess(cmd, 1, stdout="", stderr="")

    for idx, url in enumerate(urls):
        attempt_env = dict(env)
        attempt_env["UV_INDEX_URL"] = url
        result = runner(cmd, env=attempt_env, capture_output=True, text=True, check=False)
        last = result
        if result.returncode == 0:
            return result.returncode, result.stdout, result.stderr
        if idx == len(urls) - 1 or not should_retry_with_next_index(result.returncode, result.stderr):
            break
        next_url = urls[idx + 1]
        print(
            f"pyramid launcher: uv failed via {url}; retrying with {next_url}",
            file=sys.stderr,
        )

    return last.returncode, last.stdout, last.stderr


def main(argv: list[str] | None = None) -> int:
    base_environ = dict(os.environ)
    cmd, env = build_launcher_command(argv or sys.argv[1:], cwd=Path.cwd(), environ=base_environ)
    code, stdout, stderr = run_with_fallback(cmd, env, base_environ=base_environ)
    if stdout:
        print(stdout, end="")
    if stderr:
        print(stderr, end="", file=sys.stderr)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
