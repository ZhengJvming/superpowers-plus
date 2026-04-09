---
name: memory-management
description: Use when storing, querying, or exporting pyramid decomposition state across sessions, or when another skill needs a bounded context package for a single leaf
---

# Memory Management

Persistent graph + decision memory for pyramid decomposition. Backed by `<workspace-root>/.superpowers/pyramid-memory/` and accessed through `skills/memory-management/scripts/memory_cli.py`.

## When to Use

Use this skill when:
- `pyramid-decomposition` needs to create nodes, edges, decisions, or interfaces
- a planning or implementation skill needs the context package for one leaf
- the user asks what was previously decided, what the current pyramid looks like, or why a leaf is blocked

Do not use it to decompose requirements or write code. It stores and retrieves the decomposition graph only.

## Prerequisites

1. `uv` must be installed.
2. Run all `uv` commands in this skill with workspace-local cache and the Tsinghua mirror:

```bash
UV_CACHE_DIR="$PWD/.superpowers/uv-cache" \
UV_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple \
UV_INDEX_STRATEGY=unsafe-best-match \
uv run ...
```

3. The store must be initialized once:

```bash
UV_CACHE_DIR="$PWD/.superpowers/uv-cache" \
UV_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple \
UV_INDEX_STRATEGY=unsafe-best-match \
uv run skills/memory-management/scripts/memory_cli.py init --project <project-name> --embedding skip --non-interactive
```

By default the CLI resolves the workspace root from the current directory and stores data under `.superpowers/pyramid-memory/`. If you need to target a different repository root, pass `--workspace-root <path>`.

## Session Start

Run this once per session:

```bash
UV_CACHE_DIR="$PWD/.superpowers/uv-cache" \
UV_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple \
UV_INDEX_STRATEGY=unsafe-best-match \
uv run skills/memory-management/scripts/memory_cli.py config show
```

Read the JSON and cache:
- `initialized`
- `default_project`
- `embedding_provider`

Do not re-probe per call unless the user explicitly reconfigures the store.

## Core Commands

| Goal | Command |
|---|---|
| Create node | `node create --id X --name N --type T --level L --description D --origin user_stated|skill_inferred` |
| Update node | `node update --id X --status S` |
| Add hierarchy edge | `edge add --kind hierarchy --from P --to C` |
| Add dependency edge | `edge add --kind dependency --from A --to B` |
| Store split decision | `decision store --id D --node N --question Q --options '[]' --chosen C --reasoning R` |
| Add interface | `interface add --id I --node N --name Name --description D --spec S` |
| Add file reference | `file-ref add --id F --node N --path P --lines "*" --role read|modify|test|create --content-hash H` |
| List file references | `file-ref list --node <leaf-id>` |
| Check stale file references | `file-ref check --node <leaf-id>` |
| Recall similar nodes | `memory recall --query "..." [--semantic]` |
| Assemble leaf package | `memory context --node <leaf-id>` |
| Check 5 criteria | `memory check-leaf-criteria --node <leaf-id>` |
| Recompute context size | `memory recompute-tokens --node <leaf-id>` |
| Freshness check | `memory freshness` |
| Incremental refresh | `memory refresh` |
| Tree view | `memory tree [--format ascii|mermaid] [--show-deps]` |
| Scratch write | `scratch write --key K --value V [--category must_persist|session_keep] [--ttl session|persist]` |
| Scratch list | `scratch list [--category must_persist|session_keep]` |
| Scratch promote | `scratch promote --key K --node N --as decision|interface` |
| Scratch clear | `scratch clear [--ttl session|persist]` |
| Validate whole project | `memory validate` |
| Project stats | `memory stats` |
| Health check | `memory doctor` |
| Export project | `memory export` |

## Output Contract

Every command returns:

```json
{
  "ok": true,
  "data": {},
  "warnings": [],
  "degraded": false
}
```

Interpretation:
- `ok: false` means a hard failure with `error.code` and `error.message`
- `warnings` are non-blocking notes
- `degraded: true` means a fallback path was used, most commonly semantic recall degrading to BM25

## Leaf Context Pattern

Before dispatching work for one leaf:

```bash
UV_CACHE_DIR="$PWD/.superpowers/uv-cache" \
UV_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple \
UV_INDEX_STRATEGY=unsafe-best-match \
uv run skills/memory-management/scripts/memory_cli.py memory context --node <leaf-id>
```

The package contains:
- the leaf node
- ancestor chain
- ancestor and leaf decisions
- the leaf interfaces and dependency interfaces
- dependency summary
- attached `file_refs` for the exact files to read or modify
- token estimate

Pass this package as the task context. Do not pass the full pyramid unless the user explicitly asks for it.

If any file ref in the package has `status: stale`, re-read that file before making implementation decisions. Stale refs may also include a warning string in the package.

## Existing Project Pattern

At session start on an existing codebase:

```bash
UV_CACHE_DIR="$PWD/.superpowers/uv-cache" \
UV_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple \
UV_INDEX_STRATEGY=unsafe-best-match \
uv run skills/memory-management/scripts/memory_cli.py memory freshness
```

Interpretation:
- `fresh`: keep going
- `stale`: run `memory refresh`
- `unknown`: no scan baseline exists yet; trigger `codebase-exploration`

When a file changes after the last scan:

```bash
UV_CACHE_DIR="$PWD/.superpowers/uv-cache" \
UV_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple \
UV_INDEX_STRATEGY=unsafe-best-match \
uv run skills/memory-management/scripts/memory_cli.py memory refresh
```

This marks affected `file_refs` as `stale` and advances `scan.last_commit`.

## Session Context Management

### When to write to scratchpad

Write a scratch entry when losing the finding would force you to re-run tools.

Use `must_persist` for:
- user constraints and preferences
- architectural findings that change decisions
- hidden couplings or non-obvious behaviors

Use `session_keep` for:
- module layout discoveries
- config/env details
- API response shapes you still need in this session

Do not write:
- raw tool output
- dead ends
- duplicate information already present in scratch

### Pre-decision recall gate

Before any of these actions:
- `node create`
- `decision store`
- proposing a split
- answering an architecture question
- committing code

Run:

```bash
UV_CACHE_DIR="$PWD/.superpowers/uv-cache" \
UV_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple \
UV_INDEX_STRATEGY=unsafe-best-match \
uv run skills/memory-management/scripts/memory_cli.py scratch list
UV_CACHE_DIR="$PWD/.superpowers/uv-cache" \
UV_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple \
UV_INDEX_STRATEGY=unsafe-best-match \
uv run skills/memory-management/scripts/memory_cli.py memory recall --query "<what you're about to decide>" --k 3
UV_CACHE_DIR="$PWD/.superpowers/uv-cache" \
UV_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple \
UV_INDEX_STRATEGY=unsafe-best-match \
uv run skills/memory-management/scripts/memory_cli.py query ancestors --id <current-node> --summary
```

Synthesize those three inputs before acting.

## Leaf Criteria Pattern

Before marking a node as `leaf`:

```bash
UV_CACHE_DIR="$PWD/.superpowers/uv-cache" \
UV_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple \
UV_INDEX_STRATEGY=unsafe-best-match \
uv run skills/memory-management/scripts/memory_cli.py memory check-leaf-criteria --node <leaf-id>
```

Then do the LLM-only checks:
- single responsibility
- independent testability

If all pass:

```bash
UV_CACHE_DIR="$PWD/.superpowers/uv-cache" \
UV_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple \
UV_INDEX_STRATEGY=unsafe-best-match \
uv run skills/memory-management/scripts/memory_cli.py node update \
  --id <leaf-id> \
  --status leaf \
  --criteria-confirmed
```

Without `--criteria-confirmed`, the CLI will reject the transition.

## Failure Modes

- `uninitialized`: run `init`
- `missing_project`: pass `--project` explicitly or restore `default_project`
- `criteria_not_confirmed`: run `memory check-leaf-criteria` and then re-run with `--criteria-confirmed`
- `criteria_failed`: fix the reported interface, token budget, or dependency issue first
- `degraded: true` during recall: semantic path was unavailable, BM25 results are still usable
- `status: stale` on a file ref: the file changed since the last scan, re-read it

## Boundaries

This skill does not:
- decide how to split a requirement
- replace code-level context tools
- manage project files outside the pyramid memory store
