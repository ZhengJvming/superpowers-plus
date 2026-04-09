# Decomposition Guide: The 5 Independence Criteria

Every leaf node in a pyramid must satisfy all five criteria. Failing any one means the node is still too large, too vague, or too coupled to hand off safely.

The CLI mechanically checks criteria 2, 4, and 5. Criteria 1 and 3 still require LLM judgment.

## Criterion 1: Single Responsibility

Rule: The description must express one responsibility, in one sentence, without bundled conjunctions such as `and`, `以及`, `同时`, or `plus`.

Why: Bundled leaves cause cross-cutting implementations, unclear ownership, and brittle reviews.

How to check: Read the description aloud. If it naturally decomposes into two verbs or two outcomes, split it.

Bad:

```text
Implement signup endpoint and send welcome email and track analytics
```

Good:

```text
Implement signup endpoint that creates a user row and returns the new user id
```

## Criterion 2: Interface Clarity

Rule: The leaf has at least one `interface_def`, and every `spec` is at least 20 meaningful characters.

Why: A leaf without a contract forces the implementer to invent inputs and outputs.

CLI check:

```bash
python3 ../memory-management/scripts/run_memory_cli.py memory check-leaf-criteria --node <leaf-id>
```

Acceptable specs:

```text
addItem(cart_id: str, sku: str, qty: int) -> {cart_id: str, total: float}
POST /api/v1/cart/items {sku, qty} -> 201 {cart_id, total}
emits "user.created" {user_id, email, created_at}
```

Too vague:

```text
the cart API
```

## Criterion 3: Independent Testability

Rule: The leaf must be testable with mocked dependencies only. A sibling leaf should never be required as a real fixture.

Why: If sibling instantiation is required, the boundary is wrong.

How to check:
- Mentally write the first three tests.
- If they require booting sibling leaves, lift the shared behavior into its own node.

Bad:

```text
Render checkout form, but tests require a real Cart implementation to exist first.
```

Better:

```text
Render checkout form from a mocked Cart contract.
```

## Criterion 4: Token Budget

Rule: `memory context --node <leaf-id>` must stay within 8000 estimated tokens.

Why: The whole point of the pyramid is bounded context per leaf.

CLI check:

```bash
python3 ../memory-management/scripts/run_memory_cli.py memory check-leaf-criteria --node <leaf-id>
```

If it fails:
- Trim the description.
- Move stale decisions up to a branch.
- Split the node again.

## Criterion 5: Closed Dependencies

Rule: Every dependency edge must point to a node that is either:
- already `leaf` or `done`, or
- has at least one published `interface_def`

Why: Depending on a mutable, contract-less node means the leaf is built on unstable ground.

CLI check:

```bash
python3 ../memory-management/scripts/run_memory_cli.py memory check-leaf-criteria --node <leaf-id>
```

If it fails:
- decompose the dependency first, or
- publish its interface now

## Quick Reference

| # | Criterion | Checked by | Typical fix |
|---|---|---|---|
| 1 | Single responsibility | LLM | Split the node |
| 2 | Interface clarity | CLI | Add interface(s) |
| 3 | Independent testability | LLM | Lift shared dependency |
| 4 | Token budget | CLI | Trim or split |
| 5 | Closed dependencies | CLI | Stabilize dependency |

When all five pass:

```bash
python3 ../memory-management/scripts/run_memory_cli.py node update \
  --id <leaf-id> \
  --status leaf \
  --criteria-confirmed
```

`--criteria-confirmed` means you personally checked criteria 1 and 3, and the CLI re-verified 2, 4, and 5 at transition time.

---

## Context Management During Decomposition

### Why BFS, not DFS

Depth-first decomposition accumulates full detail from every ancestor and quickly recreates the same context overflow that pyramid memory is supposed to avoid. Breadth-first decomposition keeps only one active node in full detail and everything else as summaries.

At any step, keep:
- one current node in full detail
- ancestor chain as summaries
- same-level siblings as summaries
- one parent decision

Do not load:
- full subtrees
- non-ancestor decisions
- the whole pyramid mid-decomposition

### The Summary Principle

Use full detail for the single node you are working on. Use summaries for ancestors and siblings.

Summary shape:
- `id`
- `name`
- `description`
- `status`
- `level`
- `node_type`

When you want more context, try in this order:
1. Re-read the parent's split decision
2. Run `memory recall`
3. Ask the user a clarifying question

Loading more raw context is the last resort, not the default move.

---

## Existing Projects

When decomposing a change to an existing codebase:

1. Run `memory freshness` at session start.
2. If the result is `stale`, run `memory refresh`.
3. If the result is `unknown` or recall is empty, trigger `codebase-exploration`.
4. Create `existing_module` or `change_*` nodes before splitting the change.
5. Add `file-ref` entries for the exact files that define the boundary.

Use `file_refs` to keep the implementation package concrete:
- `modify` for files the leaf must edit
- `read` for files that define the surrounding contract
- `test` for files that prove the change
- `create` for planned new files

If any `file_ref` is `stale`, re-read that file before making implementation decisions.
