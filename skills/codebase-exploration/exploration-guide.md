# Exploration Guide

## Session Start Protocol

1. `memory freshness`
2. If `stale`, `memory refresh`
3. If `unknown` or recall is empty, begin module discovery

## Module Discovery

Read only enough to identify:
- entry points
- major source roots
- top-level modules/packages
- their one-sentence responsibilities

For each discovered module:
- create an `existing_module` node
- add at least one `file-ref` pointing to the entry file or primary implementation file

## Impact Analysis

When the user requests a change:
- identify which existing module owns the behavior
- create `change_root` / `change_branch` / `change_leaf` nodes as needed
- attach `file_refs` for the exact files to modify, read, test, or create

## Dependency Graph Extraction

For each mapped `existing_module`:
- read only enough entry files to identify internal imports or requires
- add `dependency` edges only for internal module-to-module relationships
- skip external libraries and package-manager dependencies

After mapping edges:
- run `query cycles`
- if cycles exist, record them as architecture findings instead of pretending the graph is clean

## Hotspot Analysis

Run:

```bash
python3 ../memory-management/scripts/run_memory_cli.py memory hotspots --days 90 --top 20
```

Interpretation rule:
- high commit frequency + many reverse dependencies = risky module

Store those findings in scratchpad before planning a large change.

## Architecture Pattern Recognition

After module and dependency mapping, identify the dominant shape:
- layered
- MVC
- hexagonal
- event-driven
- monolith
- mixed / transitional

Store the result as a decision on the root or review node.

## Enhanced Impact Analysis

When the user requests a change, run:

```bash
python3 ../memory-management/scripts/run_memory_cli.py query impact --id <node-id> --direction downstream
```

Use the result to decide which modules need `change_*` nodes.
Do not create change nodes for unaffected modules.

## Budget

- Initial exploration should stay shallow and fast
- Prefer breadth over depth
- Deeper reading only happens when the requested change demands it
