---
name: codebase-exploration
description: Use when working on an existing codebase whose structure is not yet represented in pyramid memory, or when freshness/recall signals that the stored code map is missing or stale
---

# Codebase Exploration

Map an existing codebase into pyramid memory before decomposing a change.

## Activation

Use this skill when:
- `memory freshness` returns `unknown`
- `memory freshness` returns `stale` and the changed area is not yet remapped
- `memory recall` returns nothing for a concept that should already exist in the repository
- the user asks for a modification to an unfamiliar existing system

Do not ask the user whether to explore the codebase. This is an automatic preparation step.

## Workflow

1. Run `python3 ../memory-management/scripts/run_memory_cli.py memory freshness`.
2. If stale, run `python3 ../memory-management/scripts/run_memory_cli.py memory refresh`.
3. Identify top-level modules and major entry points.
4. Create `existing_module` or `change_*` nodes for the area you are about to modify.
5. Add `file-ref` entries for the concrete files that define that boundary.
6. Hand the resulting node into `pyramid-decomposition` for BFS splitting.

## Rules

- Map top-level structure first. Do not recursively read the whole repository.
- Store one-sentence responsibilities, not speculative redesigns.
- Prefer `file-ref` entries over prose when you can name the exact file.
- If a `file_ref` becomes `stale`, re-read the file before making decisions.

See [exploration-guide.md](/Users/jimmy/coding/AI/straw/skills-explore/superpowers-plus/skills/codebase-exploration/exploration-guide.md) for the scanning strategy.
