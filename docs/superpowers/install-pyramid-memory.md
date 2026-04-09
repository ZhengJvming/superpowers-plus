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

## One-Time Initialization

After `superpowers-plus` is installed for your harness, initialize the shared store once:

```bash
uv run <path-to-superpowers-plus>/skills/memory-management/scripts/memory_cli.py \
  init --project <project-name> --embedding skip --non-interactive
```

This creates:
- `~/.pyramid-memory/config.toml`
- `~/.pyramid-memory/data.cozo`

## Harness Notes

### Claude Code

Skills are typically loaded from `~/.claude/plugins/superpowers-plus/skills/`.

### Codex CLI

Skills are typically loaded from `~/.codex/skills/superpowers-plus/skills/` or a symlinked equivalent.

### Codex App

The app sandbox can restrict network and filesystem access. Recommended configuration:

```bash
uv run <path>/memory_cli.py init --project <project-name> --embedding skip --non-interactive
```

Use `skip` unless `fastembed` is already cached outside the sandbox.

### OpenCode

Make sure `uv` is in the shell `PATH` inherited by OpenCode.

### Cursor / Windsurf

These do not have strong native skill loading. Reuse the markdown instructions manually and invoke the CLI directly.

### Gemini CLI / Copilot CLI

Use the harness-specific skill loading path, but the CLI invocation stays the same.

## Verification

After init:

```bash
uv run <path>/memory_cli.py memory doctor
```

Expected:

```json
{"ok": true, "data": {"initialized": true, "db_ok": true, "embedding_provider": "skip", "embedding_ok": true, "notes": []}}
```

## Uninstall

```bash
rm -rf ~/.pyramid-memory/
```

This deletes memory for all projects on the machine. Export first if needed.
