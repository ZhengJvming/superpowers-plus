# Pyramid Memory Skills Installation Guide

These instructions install the two M2 skills:
- `pyramid-decomposition`
- `memory-management`

Both rely on the embedded Python CLI at `skills/memory-management/scripts/memory_cli.py`.

## Hard Dependency: `uv`

Install:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Verify:

```bash
uv --version
```

## Standard `uv` Environment

Use workspace-local cache plus the Tsinghua mirror for every `uv` invocation in this guide:

```bash
UV_CACHE_DIR="$PWD/.superpowers/uv-cache" \
UV_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple \
UV_INDEX_STRATEGY=unsafe-best-match \
uv run ...
```

This avoids sandbox failures caused by default user-level cache directories such as `~/.cache/uv`.

## One-Time Initialization

After `superpowers-plus` is installed for your harness, initialize the shared store once:

```bash
UV_CACHE_DIR="$PWD/.superpowers/uv-cache" \
UV_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple \
UV_INDEX_STRATEGY=unsafe-best-match \
uv run <path-to-superpowers-plus>/skills/memory-management/scripts/memory_cli.py \
  init --project <project-name> --embedding skip --non-interactive
```

This creates:
- `<workspace-root>/.superpowers/pyramid-memory/config.toml`
- `<workspace-root>/.superpowers/pyramid-memory/data.cozo`

The CLI discovers `<workspace-root>` by walking up from the current directory:
1. nearest existing `.superpowers/pyramid-memory/config.toml`
2. otherwise the nearest Git root
3. otherwise the current directory

To target a different repository explicitly, pass `--workspace-root <path>`.

## Harness Notes

### Claude Code

Skills are typically loaded from `~/.claude/plugins/superpowers-plus/skills/`.

### Codex CLI

Skills are typically loaded from `~/.codex/skills/superpowers-plus/skills/` or a symlinked equivalent.

### Codex App

The app sandbox can restrict network and filesystem access. Recommended configuration:

```bash
UV_CACHE_DIR="$PWD/.superpowers/uv-cache" \
UV_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple \
UV_INDEX_STRATEGY=unsafe-best-match \
uv run <path>/memory_cli.py init --project <project-name> --embedding skip --non-interactive
```

Use `skip` unless `fastembed` is already cached inside the sandbox-visible workspace.

### OpenCode

Make sure `uv` is in the shell `PATH` inherited by OpenCode.

### Cursor / Windsurf

These do not have strong native skill loading. Reuse the markdown instructions manually and invoke the CLI directly.

### Gemini CLI / Copilot CLI

Use the harness-specific skill loading path, but the CLI invocation stays the same.

## Verification

After init:

```bash
UV_CACHE_DIR="$PWD/.superpowers/uv-cache" \
UV_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple \
UV_INDEX_STRATEGY=unsafe-best-match \
uv run <path>/memory_cli.py memory doctor
```

Expected:

```json
{"ok": true, "data": {"initialized": true, "db_ok": true, "embedding_provider": "skip", "embedding_ok": true, "notes": []}}
```

## Uninstall

```bash
rm -rf <workspace-root>/.superpowers/pyramid-memory/
```

This deletes memory for the current workspace. Export first if needed.
