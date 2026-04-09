---
name: codebase-exploration
description: Use when analyzing an existing codebase for structure, dependencies, hotspots, or when freshness/recall signals that the stored code map is missing or stale
---

# Codebase Exploration

Map an existing codebase into pyramid memory before decomposing a change, or run a standalone architecture review when the user asks for analysis without an immediate change request.

## Activation

Use this skill when:
- `memory freshness` returns `unknown`
- `memory freshness` returns `stale` and the changed area is not yet remapped
- `memory recall` returns nothing for a concept that should already exist in the repository
- the user asks for a modification to an unfamiliar existing system
- the user asks to review architecture, analyze dependencies, map the codebase, or inspect hotspots

Mode A: change preparation
- used before decomposition or planning for an existing project change
- exits into `pyramid-decomposition`

Mode B: standalone architecture review
- used when the user explicitly asks for architecture analysis, dependency mapping, or hotspot review
- exits by reporting findings to the user

Do not ask the user whether to explore the codebase when Mode A is triggered. That exploration is automatic preparation.

## Workflow

1. Run `python3 ../memory-management/scripts/run_memory_cli.py memory freshness`.
2. If stale, run `python3 ../memory-management/scripts/run_memory_cli.py memory refresh`.
3. Identify top-level modules and major entry points.
4. Extract internal dependency edges between mapped modules.
5. Run `python3 ../memory-management/scripts/run_memory_cli.py memory hotspots`.
6. Record hotspot and architecture findings in scratchpad or decisions.
7. For change work, create `existing_module` or `change_*` nodes for the area you are about to modify.
8. Add `file-ref` entries for the concrete files that define that boundary.
9. In Mode A, hand the resulting node into `pyramid-decomposition` for BFS splitting.
10. In Mode B, report module map, dependency shape, hotspot summary, and architecture pattern to the user.

## Rules

- Map top-level structure first. Do not recursively read the whole repository.
- Store one-sentence responsibilities, not speculative redesigns.
- Prefer `file-ref` entries over prose when you can name the exact file.
- If a `file_ref` becomes `stale`, re-read the file before making decisions.
- Only map internal module-to-module dependencies. Ignore third-party packages.
- High-change modules with many reverse dependencies are high-risk hotspots.

See `exploration-guide.md` in this directory for the scanning strategy.
