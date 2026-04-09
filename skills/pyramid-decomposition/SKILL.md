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

### Phase 1: Recursive Decomposition

For the current node:

1. Decide whether it is still a branch or close to a leaf.
2. Recall prior similar work if useful:

```bash
uv run skills/memory-management/scripts/memory_cli.py memory recall --query "<node description>" --k 5
```

3. Propose 3-5 children along natural boundaries.
4. Ask the user focused micro-questions to confirm or refine those children.
5. For each accepted child:

```bash
uv run skills/memory-management/scripts/memory_cli.py node create \
  --id <child-id> \
  --name "<child-name>" \
  --type branch \
  --level <level> \
  --description "<one-sentence description>" \
  --origin <user_stated|skill_inferred>

uv run skills/memory-management/scripts/memory_cli.py edge add \
  --kind hierarchy \
  --from <parent-id> \
  --to <child-id>
```

6. Record why the split happened:

```bash
uv run skills/memory-management/scripts/memory_cli.py decision store \
  --id "d-split-<node-id>" \
  --node <node-id> \
  --question "How should <node-name> be decomposed?" \
  --options '["option-a","option-b"]' \
  --chosen "option-a" \
  --reasoning "<why this split>" \
  --tradeoffs "<tradeoffs>"
```

7. Recurse into each child.

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
