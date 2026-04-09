---
name: pyramid-decomposition
description: Use when the user has a fuzzy or oversized engineering requirement that needs to be recursively split into independently implementable leaves with explicit contracts and dependencies
---

# Pyramid Decomposition

Turn a fuzzy large requirement into a confirmed pyramid of branches and leaves. Every split is stored as a decision. Every leaf must pass five independence criteria before implementation planning.

See [decomposition-guide.md](/Users/jimmy/coding/AI/straw/skills-explore/superpowers-plus/skills/pyramid-decomposition/decomposition-guide.md) for the criteria reference.

**Core principle:** breadth-first decomposition only. Never recurse depth-first through the tree.

## Escalation Gate

Use this skill when any of these are true:
- the requirement spans multiple subsystems or boundaries
- the user cannot provide a clean implementation spec up front
- one normal spec/plan cycle will not safely hold the whole problem
- the task needs persistent structural mapping of an existing codebase

Do not use it when all of these are true:
- one clear outcome
- one bounded subsystem
- no persistent decomposition state needed
- a normal `brainstorming -> writing-plans -> execution` path is sufficient

If the task is simple, stay on the normal Superpowers workflow. Do not decompose it just because pyramid exists.

## Launcher

Use the memory launcher from the sibling skill directory:

```bash
python3 ../memory-management/scripts/run_memory_cli.py ...
```

## Minimal Start

1. Check memory state:

```bash
python3 ../memory-management/scripts/run_memory_cli.py config show
```

2. If uninitialized:

```bash
python3 ../memory-management/scripts/run_memory_cli.py init --project <project-name> --embedding skip --non-interactive
```

3. If this is an existing-project change:

```bash
python3 ../memory-management/scripts/run_memory_cli.py memory freshness
```

If freshness is `stale`, run `memory refresh`.
If freshness is `unknown`, trigger `codebase-exploration` before decomposition.

## Phase 0: Root Node

Create the level-0 root from the user's raw requirement:

```bash
python3 ../memory-management/scripts/run_memory_cli.py node create \
  --id root \
  --name "<short-title>" \
  --type root \
  --level 0 \
  --description "<raw requirement>" \
  --origin user_stated
```

## Phase 1: BFS Decomposition

For the current level, load only:
- `node get --id <node>`
- `query ancestors --id <node> --summary`
- `node list --level <level> --summary`
- the parent split decision
- optional `memory recall --query "<node-description>" --k 3`
- current scratch entries

Do not load:
- the entire subtree
- non-ancestor decisions
- full sibling detail
- the whole pyramid mid-decomposition

### Per-node loop

Before each split decision:

```bash
python3 ../memory-management/scripts/run_memory_cli.py scratch list
python3 ../memory-management/scripts/run_memory_cli.py memory recall --query "<what you are about to decide>" --k 3
python3 ../memory-management/scripts/run_memory_cli.py query ancestors --id <node-id> --summary
```

Then:
1. Decide whether the node can already be a leaf.
2. If not, propose 3-5 children along natural boundaries.
3. Confirm the split with focused micro-questions.
4. Create children.
5. Store the split decision on the parent.

For each accepted child:

```bash
python3 ../memory-management/scripts/run_memory_cli.py node create ...
python3 ../memory-management/scripts/run_memory_cli.py edge add --kind hierarchy --from <parent-id> --to <child-id>
```

Record the split decision:

```bash
python3 ../memory-management/scripts/run_memory_cli.py decision store ...
```

Do not recurse into the new children immediately. Finish the whole level first.

## Phase 1.5: Leaf Qualification

Before marking a node as `leaf`:

1. Publish at least one interface:

```bash
python3 ../memory-management/scripts/run_memory_cli.py interface add ...
```

2. Run the mechanical criteria check:

```bash
python3 ../memory-management/scripts/run_memory_cli.py memory check-leaf-criteria --node <leaf-id>
```

3. Personally verify:
- single responsibility
- independent testability

4. If all five pass:

```bash
python3 ../memory-management/scripts/run_memory_cli.py node update --id <leaf-id> --status leaf --criteria-confirmed
```

If any criterion fails, the node remains a branch. Split again or stabilize its dependencies first.

## Phase 2: Dependency Pass

After leaves exist:

```bash
python3 ../memory-management/scripts/run_memory_cli.py edge add --kind dependency --from <leaf-a> --to <leaf-b>
python3 ../memory-management/scripts/run_memory_cli.py query cycles
```

If a cycle appears, remove the weakest dependency or extract a shared abstraction into a new node.

## Phase 3: Validate and Hand Off

Run:

```bash
python3 ../memory-management/scripts/run_memory_cli.py memory validate
python3 ../memory-management/scripts/run_memory_cli.py memory stats
```

When the pyramid is ready, hand off one leaf at a time:

```bash
python3 ../memory-management/scripts/run_memory_cli.py memory context --node <leaf-id>
```

Pass only that package into `writing-plans` or `subagent-driven-development`. Do not dump the full pyramid into the next agent.

## Existing Project Rule

If this is a change to a real codebase rather than greenfield design:
- run freshness first
- trigger `codebase-exploration` when freshness is `unknown`
- create `existing_module` or `change_*` nodes before deep splitting
- attach `file-ref` entries for the exact boundary files

Do not ask the user whether to explore. Exploration is automatic preparation.

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

Then offer exactly two next steps:
1. pause for review
2. hand off a leaf into implementation planning
