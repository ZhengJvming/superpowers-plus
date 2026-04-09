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

## Budget

- Initial exploration should stay shallow and fast
- Prefer breadth over depth
- Deeper reading only happens when the requested change demands it
