---
name: memory-management
description: Use when storing, querying, or exporting pyramid decomposition state across sessions, or when another skill needs a bounded context package for a single leaf
---

# Memory Management

Persistent graph + decision memory for pyramid decomposition. Backed by `<workspace-root>/.superpowers/pyramid-memory/`.

**Core principle:** one leaf package at a time. If a bounded leaf context exists, do not pass the full pyramid.

## Launcher

Use the launcher from this skill directory:

```bash
python3 scripts/run_memory_cli.py ...
```

The launcher:
- resolves the workspace root
- uses workspace-local `UV_CACHE_DIR`
- uses the Tsinghua mirror by default, with retry fallback to Aliyun and official PyPI
- invokes `memory_cli.py` from the installed skill directory

If you need a different repository root, pass `--workspace-root <path>` before the subcommand.

## When to Use

Use this skill when:
- `pyramid-decomposition` needs to create or query nodes, edges, decisions, interfaces, file refs, or scratch entries
- `writing-plans` needs the bounded context package for one leaf
- `subagent-driven-development` needs to mark a leaf done or read its context
- an existing-project workflow needs freshness or refresh signals

Do not use it to decide how to split a requirement. It stores and retrieves the decomposition graph only.

## Minimal Start

Run once per session:

```bash
python3 scripts/run_memory_cli.py config show
```

If `initialized` is false:

```bash
python3 scripts/run_memory_cli.py init --project <project-name> --embedding skip --non-interactive
```

If you are in an existing codebase:

```bash
python3 scripts/run_memory_cli.py memory freshness
```

## Core Commands

| Goal | Command |
|---|---|
| Show config | `python3 scripts/run_memory_cli.py config show` |
| Health check | `python3 scripts/run_memory_cli.py memory doctor` |
| Create node | `python3 scripts/run_memory_cli.py node create ...` |
| Add hierarchy edge | `python3 scripts/run_memory_cli.py edge add --kind hierarchy ...` |
| Add dependency edge | `python3 scripts/run_memory_cli.py edge add --kind dependency ...` |
| Store decision | `python3 scripts/run_memory_cli.py decision store ...` |
| Add interface | `python3 scripts/run_memory_cli.py interface add ...` |
| Add file ref | `python3 scripts/run_memory_cli.py file-ref add ...` |
| Recall | `python3 scripts/run_memory_cli.py memory recall --query \"...\" --k 3` |
| Leaf package | `python3 scripts/run_memory_cli.py memory context --node <leaf-id>` |
| Check leaf criteria | `python3 scripts/run_memory_cli.py memory check-leaf-criteria --node <leaf-id>` |
| Freshness | `python3 scripts/run_memory_cli.py memory freshness` |
| Refresh | `python3 scripts/run_memory_cli.py memory refresh` |
| Tree | `python3 scripts/run_memory_cli.py memory tree --format ascii|mermaid --show-deps` |
| Scratch list | `python3 scripts/run_memory_cli.py scratch list` |
| Validate | `python3 scripts/run_memory_cli.py memory validate` |
| Stats | `python3 scripts/run_memory_cli.py memory stats` |
| Export | `python3 scripts/run_memory_cli.py memory export` |

## Embedding 配置建议

当 `memory stats` 显示 `total_nodes > 50` 且 `config show` 显示 `embedding_provider = skip` 时，提醒用户一次：

> 当前项目已有 N 个节点。节点较多时 BM25 关键词召回可能不够精确，建议配置 embedding 以启用语义搜索。

只建议，不要自动替用户启用。

OpenAI:

```bash
python3 scripts/run_memory_cli.py config set --key embedding_provider --value openai_compatible
python3 scripts/run_memory_cli.py config set --key embedding.model --value text-embedding-3-small
python3 scripts/run_memory_cli.py config set --key embedding.api_base --value https://api.openai.com/v1
python3 scripts/run_memory_cli.py config set --key embedding.api_key_env --value OPENAI_API_KEY
```

DashScope (OpenAI-compatible):

```bash
python3 scripts/run_memory_cli.py config set --key embedding_provider --value openai_compatible
python3 scripts/run_memory_cli.py config set --key embedding.model --value text-embedding-v3
python3 scripts/run_memory_cli.py config set --key embedding.api_base --value https://dashscope.aliyuncs.com/compatible-mode/v1
python3 scripts/run_memory_cli.py config set --key embedding.api_key_env --value DASHSCOPE_API_KEY
```

Silicon Flow (OpenAI-compatible):

```bash
python3 scripts/run_memory_cli.py config set --key embedding_provider --value openai_compatible
python3 scripts/run_memory_cli.py config set --key embedding.model --value BAAI/bge-m3
python3 scripts/run_memory_cli.py config set --key embedding.api_base --value https://api.siliconflow.cn/v1
python3 scripts/run_memory_cli.py config set --key embedding.api_key_env --value SILICONFLOW_API_KEY
```

## Leaf Package Rule

Before planning or implementing one leaf:

```bash
python3 scripts/run_memory_cli.py memory context --node <leaf-id>
```

The package is the authoritative context block. It contains:
- the leaf node
- ancestor summaries and decisions
- leaf and dependency interfaces
- dependency summary
- attached `file_refs`
- token estimate

Do not rebuild this context manually from the whole tree unless the user explicitly asks for a full-tree review.

## Existing Project Rule

At session start in an existing codebase:

```bash
python3 scripts/run_memory_cli.py memory freshness
```

Interpretation:
- `fresh`: continue
- `stale`: run `memory refresh`
- `unknown`: trigger `codebase-exploration`

When a file changes after the last scan:

```bash
python3 scripts/run_memory_cli.py memory refresh
```

If any `file_ref` is `stale`, re-read that file before making planning or implementation decisions.

## Pre-Decision Recall Gate

Before any of these actions:
- `node create`
- `decision store`
- proposing a split
- answering an architecture question
- committing code for a leaf

Run:

```bash
python3 scripts/run_memory_cli.py scratch list
python3 scripts/run_memory_cli.py memory recall --query "<what you're about to decide>" --k 3
python3 scripts/run_memory_cli.py query ancestors --id <current-node> --summary
```

Synthesize those three inputs before acting.

## Leaf Transition Rule

Before marking a node as `leaf`:

```bash
python3 scripts/run_memory_cli.py memory check-leaf-criteria --node <leaf-id>
```

Then personally confirm:
- single responsibility
- independent testability

Only then transition:

```bash
python3 scripts/run_memory_cli.py node update --id <leaf-id> --status leaf --criteria-confirmed
```

Without `--criteria-confirmed`, the CLI will reject the transition.

## Stop Conditions

Stop and repair before continuing when:
- `config show` or `memory doctor` reports `uninitialized`
- `memory doctor` reports db failure
- `memory check-leaf-criteria` returns `criteria_failed`
- a required file ref is `stale` and has not been re-read

Continue with caution when:
- `degraded: true` on recall, meaning semantic recall fell back to BM25

## Boundaries

This skill does not:
- decide whether a task is simple or pyramid-worthy
- decompose requirements by itself
- replace code-level repository exploration
- manage project files outside `.superpowers/`
