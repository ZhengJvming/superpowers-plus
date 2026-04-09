# Pyramid Memory Skills Installation Guide

This installs the two pyramid skills:
- `pyramid-decomposition`
- `memory-management`

Use the launcher, not the raw CLI:

```bash
python3 <skills-root>/memory-management/scripts/run_memory_cli.py ...
```

The launcher already does the two things that matter in sandboxed harnesses:
- pins `UV_CACHE_DIR` to `<workspace-root>/.superpowers/uv-cache/`
- defaults `UV_INDEX_URL` to the Tsinghua mirror, then retries with Aliyun and finally official PyPI if the mirror is blocked

You should not need to type a long `UV_CACHE_DIR=... uv run ...` prefix during normal use.

If you want to force a specific source, set `UV_INDEX_URL` explicitly before running the launcher.

## Hard Dependency: `uv`

Install:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Verify:

```bash
uv --version
```

## Skill Root

`<skills-root>` means the installed `superpowers-plus/skills` directory for your harness.

Typical locations:
- Claude Code: `~/.claude/plugins/superpowers-plus/skills/`
- Codex CLI: `~/.codex/skills/superpowers-plus/skills/`
- Codex App: `~/.codex/skills/superpowers-plus/skills/`

If you install or update the symlink, start a new agent session before testing. Skill discovery usually happens at session start, not continuously.

## One-Time Initialization

From the target workspace, run:

```bash
python3 <skills-root>/memory-management/scripts/run_memory_cli.py \
  init --project <project-name> --embedding skip --non-interactive
```

This creates:
- `<workspace-root>/.superpowers/pyramid-memory/config.toml`
- `<workspace-root>/.superpowers/pyramid-memory/data.cozo`
- `<workspace-root>/.superpowers/uv-cache/`

Workspace root is discovered by walking up from the current directory:
1. nearest existing `.superpowers/pyramid-memory/config.toml`
2. otherwise the nearest Git root
3. otherwise the current directory

To target a different repository explicitly:

```bash
python3 <skills-root>/memory-management/scripts/run_memory_cli.py \
  --workspace-root /abs/path/to/repo \
  init --project <project-name> --embedding skip --non-interactive
```

Use `skip` unless `fastembed` is already available and you explicitly want semantic recall enabled.

## `.gitignore`

Do not commit runtime state. Add this in each target workspace:

```bash
printf '\n.superpowers/\n' >> .gitignore
```

`pyramid-memory` stores the database and config there, and the launcher also puts the `uv` cache there.

## Verification

After init:

```bash
python3 <skills-root>/memory-management/scripts/run_memory_cli.py memory doctor
```

Expected:

```json
{"ok": true, "data": {"initialized": true, "db_ok": true, "embedding_provider": "skip", "embedding_ok": true, "notes": []}}
```

## Fresh Workspace Smoke Test

Use a clean repo, not the `superpowers-plus` source checkout:

```bash
mkdir -p /tmp/pyramid-skill-smoke
cd /tmp/pyramid-skill-smoke
git init
printf '\n.superpowers/\n' >> .gitignore
python3 <skills-root>/memory-management/scripts/run_memory_cli.py \
  init --project smoke --embedding skip --non-interactive
python3 <skills-root>/memory-management/scripts/run_memory_cli.py memory doctor
find .superpowers -maxdepth 3 -type f | sort
```

Pass criteria:
- `.superpowers/pyramid-memory/config.toml` exists
- `.superpowers/pyramid-memory/data.cozo` exists
- `.superpowers/uv-cache/` exists
- no write happens to `~/.pyramid-memory/`

## Harness Notes

### Codex App

The launcher is the recommended entrypoint. It keeps both memory state and the `uv` cache inside the current workspace, which avoids common sandbox failures.

### OpenCode

Make sure `uv` is in the shell `PATH` inherited by OpenCode.

### Cursor / Windsurf

These do not have strong native skill loading. Reuse the markdown instructions manually and invoke the launcher directly.

### Gemini CLI / Copilot CLI

Use the harness-specific skill loading path, but keep the same launcher invocation.

## Uninstall

```bash
rm -rf <workspace-root>/.superpowers/
```

This deletes pyramid memory and the workspace-local `uv` cache for the current workspace. Export first if needed.
