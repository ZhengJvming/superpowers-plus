---
name: pyramid-decomposition
description: Use when the user has a fuzzy or oversized engineering requirement that needs to be recursively split into independently implementable leaves with explicit contracts and dependencies
---

# Pyramid Decomposition

Turn a fuzzy large requirement into a confirmed pyramid of branches and leaves. Every split is stored as a decision. Every leaf must pass five independence criteria before it can be marked complete enough for implementation planning.

See [decomposition-guide.md](/Users/jimmy/coding/AI/straw/skills-explore/superpowers-plus/skills/pyramid-decomposition/decomposition-guide.md) for the full criteria reference.

## When to Use

Use this skill when:
- the requirement spans multiple subsystems or boundaries
- the user cannot provide a clean implementation spec up front
- a single context window cannot safely hold the whole design

Do not use it for:
- single-file features
- tightly scoped bug fixes
- already-finished specs that are ready for `writing-plans`

## Prerequisites

1. `memory-management` must be available.
2. `uv` must be installed.
3. `memory config show` must report `initialized: true`, or you initialize the store first.

## Workflow

### Phase 0: Initialize

Run:

```bash
uv run skills/memory-management/scripts/memory_cli.py config show
```

If uninitialized:

```bash
uv run skills/memory-management/scripts/memory_cli.py init --project <project-name> --embedding skip --non-interactive
```

The memory store is workspace-local by default and lives under `<workspace-root>/.superpowers/pyramid-memory/`. If you are operating from a nested directory but want a different root, pass `--workspace-root <path>`.

Then create the L0 root from the user's raw requirement:

```bash
uv run skills/memory-management/scripts/memory_cli.py node create \
  --id root \
  --name "<short-title>" \
  --type root \
  --level 0 \
  --description "<raw requirement>" \
  --origin user_stated
```

### Phase 0.5: Existing Project Impact Analysis

If the user is modifying an existing codebase rather than designing a greenfield system:

1. Run `memory freshness`.
2. If freshness is `stale`, run `memory refresh`.
3. If freshness is `unknown` or recall returns nothing useful, activate `codebase-exploration`.
4. Create or reuse `existing_module` / `change_*` nodes to map the code area before decomposition.
5. Add `file-ref` entries for the concrete files that define the current boundary.

Do not ask the user whether to explore. Existing-project exploration is an automatic preparation step.

### Phase 1: BFS Decomposition (level by level)

**Core rule: process one level at a time, never recurse depth-first.**

When processing node `N` at level `L`, load only:
- `node get --id N`
- `query ancestors --id N --summary`
- `node list --level L --summary`
- the parent's split decision
- optional `memory recall --query "<N.description>" --k 3`
- current scratchpad findings from `scratch list`

Do not load:
- the entire subtree
- non-ancestor decisions
- full details for sibling nodes
- full pyramid state mid-decomposition

#### BFS loop

1. `node list --level <current-level>` to get pending nodes.
2. For each node at that level:
   - run the pre-decision recall gate:

```bash
uv run skills/memory-management/scripts/memory_cli.py scratch list
uv run skills/memory-management/scripts/memory_cli.py memory recall --query "<what you are about to decide>" --k 3
uv run skills/memory-management/scripts/memory_cli.py query ancestors --id <node-id> --summary
```

   - decide whether the node can already be a leaf
   - if not, propose 3-5 children along natural boundaries
   - confirm the split with focused micro-questions
   - create children and a split decision
3. After finishing the whole level, advance to the next level.

For each accepted child:

```bash
uv run skills/memory-management/scripts/memory_cli.py node create \
  --id <child-id> \
  --name "<child-name>" \
  --type branch \
  --level <parent-level + 1> \
  --description "<one-sentence description>" \
  --origin <user_stated|skill_inferred>

uv run skills/memory-management/scripts/memory_cli.py edge add \
  --kind hierarchy \
  --from <parent-id> \
  --to <child-id>
```

Record the split decision on the parent:

```bash
uv run skills/memory-management/scripts/memory_cli.py decision store \
  --id "d-split-<node-id>" \
  --node <node-id> \
  --question "How should <node-name> be decomposed?" \
  --options '["chosen-split", "alt-1", "alt-2"]' \
  --chosen "<chosen-split>" \
  --reasoning "<why this split>" \
  --tradeoffs "<tradeoffs>"
```

Do not recurse into the children immediately. They are processed when the BFS loop advances.

### Phase 1.5: Leaf Qualification

Before marking a node as `leaf`:

1. Publish at least one interface:

```bash
uv run skills/memory-management/scripts/memory_cli.py interface add \
  --id "iface-<leaf-id>" \
  --node <leaf-id> \
  --name "<name>" \
  --description "<what it exposes>" \
  --spec "<signature, endpoint, event, or contract>"
```

2. Run the mechanical criteria check:

```bash
uv run skills/memory-management/scripts/memory_cli.py memory check-leaf-criteria --node <leaf-id>
```

3. Perform the two LLM-only checks:
- single responsibility
- independent testability

4. If all five pass:

```bash
uv run skills/memory-management/scripts/memory_cli.py node update \
  --id <leaf-id> \
  --status leaf \
  --criteria-confirmed
```

If any criterion fails, the node is still a branch. Split again or stabilize its dependencies first.

### Phase 2: Dependency Pass

After leaves exist, add cross-leaf dependencies explicitly:

```bash
uv run skills/memory-management/scripts/memory_cli.py edge add --kind dependency --from <leaf-a> --to <leaf-b>
```

Then verify no cycles:

```bash
uv run skills/memory-management/scripts/memory_cli.py query cycles
```

If a cycle appears, remove the weakest dependency or extract the shared abstraction into a new node.

### Phase 3: Validate and Hand Off

Run:

```bash
uv run skills/memory-management/scripts/memory_cli.py memory validate
uv run skills/memory-management/scripts/memory_cli.py memory stats
```

Expected:
- validation passes
- the skill-inferred ratio is meaningfully non-zero; if it is too low, you likely failed to surface hidden structure

When the pyramid is ready, hand off one leaf at a time:

```bash
uv run skills/memory-management/scripts/memory_cli.py memory context --node <leaf-id>
```

Pass only that package into `subagent-driven-development` or `writing-plans`. Do not dump the full pyramid into the next agent.

## Non-Negotiables

- Every accepted branch split gets a stored decision.
- Every leaf gets at least one interface.
- Every leaf transition uses `--criteria-confirmed`.
- Every child node gets a correct `origin` tag.
- Dependencies must be explicit edges, not implied in prose.

## User-Facing Closeout

At the end, summarize:
- total leaves
- total branches
- total decisions
- skill-inferred ratio
- whether validation passed

Then ask whether to pause for review or hand off to implementation planning.
