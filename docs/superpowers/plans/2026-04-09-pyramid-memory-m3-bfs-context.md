# Pyramid Memory — Milestone 3: BFS Context Control

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prevent context overflow during the decomposition phase itself by switching from DFS recursion to BFS level-by-level processing, with explicit context budget rules and CLI support for summary-mode queries.

**Architecture:** Two small CLI extensions (`--level` filter, `--summary` mode) + one new command (`memory recompute-tokens`) + a rewrite of `pyramid-decomposition/SKILL.md` Phase 1. No new dependencies, no schema changes.

**Tech Stack:** Same as M1/M2. Python CLI changes only.

**Spec:** `docs/superpowers/specs/2026-04-07-pyramid-memory-skill-design.md` — Milestone 3.

**Prerequisite:** M2 shipped.

---

## File Map

```
superpowers-plus/skills/memory-management/
├── scripts/
│   ├── memory_cli.py              # MODIFY: add --level, --summary, recompute-tokens, tree
│   ├── store.py                   # MODIFY: add list_nodes(level=), summary projection
│   ├── cozo_store.py              # MODIFY: same
│   ├── config.py                  # MODIFY: add [display] tree_format
│   └── tree_renderer.py           # NEW: ASCII + Mermaid tree rendering
└── tests/
    ├── test_cli_node.py           # MODIFY: add --level, --summary tests
    ├── test_cli_query.py          # MODIFY: add --summary tests for ancestors
    ├── test_cli_memory_recompute.py  # NEW
    ├── test_bfs_context_budget.py    # NEW: verify context stays bounded
    ├── test_tree_renderer.py         # NEW: ASCII + Mermaid output tests
    └── test_cli_tree.py              # NEW: memory tree CLI tests

superpowers-plus/skills/pyramid-decomposition/
├── SKILL.md                       # MODIFY: Phase 1 DFS → BFS rewrite + visualization rules
└── decomposition-guide.md         # MODIFY: add "Context Management" section
```

---

## Chunk 1: CLI Extensions

### Task 1: Add `--level` filter to `node list`

**Files:**
- Modify: `superpowers-plus/skills/memory-management/scripts/store.py`
- Modify: `superpowers-plus/skills/memory-management/scripts/cozo_store.py`
- Modify: `superpowers-plus/skills/memory-management/scripts/memory_cli.py`
- Modify: `superpowers-plus/skills/memory-management/tests/test_cli_node.py`

- [ ] **Step 1: Write the failing test**

```python
# Append to tests/test_cli_node.py
def test_node_list_filter_by_level(initialized):
    initialized("node", "create", "--id", "r", "--name", "r", "--type", "root",
                "--level", "0", "--description", "x", "--origin", "user_stated")
    initialized("node", "create", "--id", "a", "--name", "a", "--type", "branch",
                "--level", "1", "--description", "x", "--origin", "user_stated")
    initialized("node", "create", "--id", "b", "--name", "b", "--type", "leaf",
                "--level", "2", "--description", "x", "--origin", "user_stated")
    r = initialized("node", "list", "--level", "1")
    nodes = json.loads(r.stdout)["data"]["nodes"]
    assert len(nodes) == 1 and nodes[0]["id"] == "a"
```

- [ ] **Step 2: Run, expect FAIL**

```bash
uv run pytest tests/test_cli_node.py::test_node_list_filter_by_level -v
```

- [ ] **Step 3: Add `level` parameter to Protocol, both impls, and CLI**

In `store.py` `MemoryStore` Protocol and `InMemoryStore`:
```python
    def list_nodes(self, project: str, *, status: Optional[str] = None, level: Optional[int] = None) -> list[Node]:
```

InMemoryStore impl — add level filter:
```python
        if level is not None:
            nodes = [n for n in nodes if n.level == level]
```

CozoStore — add level filter to the Datalog query (add `level = $l` condition when level is not None).

CLI `node_list` command — add:
```python
@click.option("--level", type=int, default=None)
```

- [ ] **Step 4: Run, expect PASS**

- [ ] **Step 5: Commit**

```bash
git add -u
git commit -m "feat(memory-cli): add --level filter to node list"
```

---

### Task 2: Add `--summary` mode to `node list` and `query ancestors`

**Files:**
- Modify: `superpowers-plus/skills/memory-management/scripts/memory_cli.py`
- Modify: `superpowers-plus/skills/memory-management/tests/test_cli_node.py`
- Modify: `superpowers-plus/skills/memory-management/tests/test_cli_query.py`

- [ ] **Step 1: Write the failing tests**

```python
# Append to tests/test_cli_node.py
def test_node_list_summary_mode(initialized):
    initialized("node", "create", "--id", "a", "--name", "mynode", "--type", "branch",
                "--level", "1", "--description", "full desc here", "--origin", "user_stated")
    r = initialized("node", "list", "--summary")
    nodes = json.loads(r.stdout)["data"]["nodes"]
    assert len(nodes) == 1
    n = nodes[0]
    # Summary only has: id, name, description, status, level, node_type
    assert set(n.keys()) == {"id", "name", "description", "status", "level", "node_type"}
    assert "created_at" not in n
    assert "tokens_estimate" not in n
```

```python
# Append to tests/test_cli_query.py
def test_query_ancestors_summary(initialized):
    _seed_pyramid(initialized)
    r = initialized("query", "ancestors", "--id", "b", "--summary")
    nodes = json.loads(r.stdout)["data"]["nodes"]
    assert len(nodes) == 2  # a, root
    for n in nodes:
        assert set(n.keys()) == {"id", "name", "description", "status", "level", "node_type"}
```

- [ ] **Step 2: Run, expect FAIL**

- [ ] **Step 3: Add `--summary` flag to CLI commands**

```python
SUMMARY_FIELDS = {"id", "name", "description", "status", "level", "node_type"}

def _project_nodes(nodes: list, summary: bool) -> list[dict]:
    if summary:
        return [{k: n[k] for k in SUMMARY_FIELDS if k in n} for n in (n.to_dict() if hasattr(n, 'to_dict') else n for n in nodes)]
    return [n.to_dict() if hasattr(n, 'to_dict') else n for n in nodes]
```

Add `@click.option("--summary", is_flag=True)` to `node_list`, `query_children`, `query_ancestors`, `query_subtree`. Use `_project_nodes()` to filter output.

- [ ] **Step 4: Run, expect PASS**

- [ ] **Step 5: Commit**

```bash
git add -u
git commit -m "feat(memory-cli): add --summary mode for compact node output"
```

---

### Task 3: Add `memory recompute-tokens` command

**Files:**
- Modify: `superpowers-plus/skills/memory-management/scripts/memory_cli.py`
- Create: `superpowers-plus/skills/memory-management/tests/test_cli_memory_recompute.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_cli_memory_recompute.py
import json

def test_recompute_tokens_updates_estimate(run_cli):
    run_cli("init", "--project", "demo", "--embedding", "skip", "--non-interactive")
    run_cli("node", "create", "--id", "root", "--name", "r", "--type", "root",
            "--level", "0", "--description", "root", "--origin", "user_stated",
            "--tokens-estimate", "0")
    run_cli("node", "create", "--id", "leaf", "--name", "l", "--type", "leaf",
            "--level", "1", "--description", "a detailed leaf description with many words",
            "--origin", "user_stated", "--tokens-estimate", "0")
    run_cli("edge", "add", "--kind", "hierarchy", "--from", "root", "--to", "leaf")
    run_cli("decision", "store", "--id", "d1", "--node", "root",
            "--question", "q?", "--options", "[]", "--chosen", "x",
            "--reasoning", "long reasoning text here for token count",
            "--tradeoffs", "some tradeoffs")
    run_cli("interface", "add", "--id", "i1", "--node", "leaf",
            "--name", "api", "--description", "d",
            "--spec", "GET /x returns {id, name, status, created_at}")
    r = run_cli("memory", "recompute-tokens", "--node", "leaf")
    payload = json.loads(r.stdout)
    assert payload["ok"]
    assert payload["data"]["tokens_estimate"] > 0
    # Verify it was persisted
    r2 = run_cli("node", "get", "--id", "leaf")
    assert json.loads(r2.stdout)["data"]["tokens_estimate"] > 0
```

- [ ] **Step 2: Run, expect FAIL**

- [ ] **Step 3: Implement**

```python
@memory.command("recompute-tokens")
@click.option("--node", "node_id", required=True)
@click.option("--project")
def memory_recompute_tokens(node_id, project):
    """Recompute tokens_estimate from actual assemble_context output."""
    s, cfg = _store()
    p = _project(project, cfg)
    pkg = s.assemble_context(p, node_id)
    new_estimate = pkg.tokens_estimate
    s.update_node(p, node_id, tokens_estimate=new_estimate, updated_at=_now())
    emit({"node_id": node_id, "tokens_estimate": new_estimate})
```

- [ ] **Step 4: Run, expect PASS**

- [ ] **Step 5: Commit**

```bash
git add -u
git commit -m "feat(memory-cli): memory recompute-tokens command"
```

---

## Chunk 2: BFS Context Budget Test

### Task 4: Write a context budget integration test

This test proves the BFS approach works: decomposing a multi-level pyramid never loads more than a bounded amount of state.

**Files:**
- Create: `superpowers-plus/skills/memory-management/tests/test_bfs_context_budget.py`

- [ ] **Step 1: Write the test**

```python
"""Prove that BFS-style context loading stays bounded as the tree grows."""
import json

def test_context_at_each_level_stays_bounded(run_cli):
    """Simulate what the LLM loads at each level during BFS decomposition.
    
    Build a 4-level tree (root → 4 branches → 4×3 sub-branches → 4×3×2 leaves = 24 leaves).
    At each level, measure the total chars of summary data the LLM would load.
    Assert it stays under 3000 tokens (~12000 chars) at every level.
    """
    cli = run_cli
    cli("init", "--project", "budget", "--embedding", "skip", "--non-interactive")
    
    # Build the tree
    cli("node", "create", "--id", "root", "--name", "system", "--type", "root",
        "--level", "0", "--description", "a large system with many modules",
        "--origin", "user_stated")
    
    l1_ids = []
    for i in range(4):
        nid = f"l1-{i}"
        l1_ids.append(nid)
        cli("node", "create", "--id", nid, "--name", f"module-{i}", "--type", "branch",
            "--level", "1", "--description", f"module {i} handles feature {i}",
            "--origin", "user_stated")
        cli("edge", "add", "--kind", "hierarchy", "--from", "root", "--to", nid)
        cli("decision", "store", "--id", f"d-{nid}", "--node", "root",
            "--question", "split?", "--options", "[]", "--chosen", nid,
            "--reasoning", f"module {i} is independent")
    
    l2_ids = []
    for l1 in l1_ids:
        for j in range(3):
            nid = f"{l1}-sub-{j}"
            l2_ids.append(nid)
            cli("node", "create", "--id", nid, "--name", f"sub-{j}", "--type", "branch",
                "--level", "2", "--description", f"sub-component {j} of {l1}",
                "--origin", "skill_inferred")
            cli("edge", "add", "--kind", "hierarchy", "--from", l1, "--to", nid)
            cli("decision", "store", "--id", f"d-{nid}", "--node", l1,
                "--question", "split?", "--options", "[]", "--chosen", nid,
                "--reasoning", f"component {j} is separable")
    
    l3_ids = []
    for l2 in l2_ids:
        for k in range(2):
            nid = f"{l2}-leaf-{k}"
            l3_ids.append(nid)
            cli("node", "create", "--id", nid, "--name", f"leaf-{k}", "--type", "leaf",
                "--level", "3", "--description", f"implement leaf {k} of {l2}",
                "--origin", "skill_inferred")
            cli("edge", "add", "--kind", "hierarchy", "--from", l2, "--to", nid)
    
    # Now simulate BFS context loading at each level
    MAX_CONTEXT_CHARS = 12000  # ~3000 tokens
    
    # Level 1: processing l1-0. Load: root full + l1 siblings summary
    root_full = json.loads(cli("node", "get", "--id", "root").stdout)["data"]
    l1_summaries = json.loads(cli("node", "list", "--level", "1", "--summary").stdout)["data"]["nodes"]
    level1_chars = len(json.dumps(root_full)) + len(json.dumps(l1_summaries))
    assert level1_chars < MAX_CONTEXT_CHARS, f"Level 1 context: {level1_chars} chars"
    
    # Level 2: processing l1-0-sub-0. Load: ancestor summaries + l2 siblings under l1-0
    ancestors = json.loads(cli("query", "ancestors", "--id", "l1-0-sub-0", "--summary").stdout)["data"]["nodes"]
    current_full = json.loads(cli("node", "get", "--id", "l1-0-sub-0").stdout)["data"]
    l2_siblings = json.loads(cli("node", "list", "--level", "2", "--summary").stdout)["data"]["nodes"]
    # In real BFS, LLM only loads siblings under the same parent, but even loading ALL l2 should be bounded
    level2_chars = len(json.dumps(ancestors)) + len(json.dumps(current_full)) + len(json.dumps(l2_siblings))
    assert level2_chars < MAX_CONTEXT_CHARS, f"Level 2 context: {level2_chars} chars"
    
    # Level 3: processing a leaf. Load: ancestor summaries + l3 siblings under parent
    ancestors3 = json.loads(cli("query", "ancestors", "--id", f"{l2_ids[0]}-leaf-0", "--summary").stdout)["data"]["nodes"]
    current3 = json.loads(cli("node", "get", "--id", f"{l2_ids[0]}-leaf-0").stdout)["data"]
    l3_siblings = json.loads(cli("node", "list", "--level", "3", "--summary").stdout)["data"]["nodes"]
    level3_chars = len(json.dumps(ancestors3)) + len(json.dumps(current3)) + len(json.dumps(l3_siblings))
    # Even with 24 leaf summaries, should still be bounded
    assert level3_chars < MAX_CONTEXT_CHARS, f"Level 3 context: {level3_chars} chars"
    
    # Verify total tree size
    all_nodes = json.loads(cli("node", "list").stdout)["data"]["nodes"]
    total = len(all_nodes)  # root + 4 + 12 + 24 = 41
    assert total == 41
```

- [ ] **Step 2: Run, expect PASS**

```bash
uv run pytest tests/test_bfs_context_budget.py -v
```

- [ ] **Step 3: Commit**

```bash
git add superpowers-plus/skills/memory-management/tests/test_bfs_context_budget.py
git commit -m "test(memory-cli): BFS context budget stays bounded on 41-node tree"
```

---

## Chunk 3: SKILL.md Phase 1 Rewrite

### Task 5: Rewrite `pyramid-decomposition/SKILL.md` Phase 1 to BFS

**Files:**
- Modify: `superpowers-plus/skills/pyramid-decomposition/SKILL.md`

- [ ] **Step 1: Replace the entire Phase 1 section**

Find the section starting with `### Phase 1 — Recursive Decomposition` and replace it with:

```markdown
### Phase 1 — BFS Decomposition (level by level)

**Core rule: process one level at a time, never recurse depth-first.**

DFS accumulates ancestor context at each level, causing context overflow on deep trees. BFS keeps context bounded: at any step, you hold ONE node in full detail + summaries of ancestors and siblings.

#### Context Budget (STRICT — violating this causes context drift)

When processing node N at level L, load into your working context ONLY:

| Data | How to get it | Approx tokens |
|---|---|---|
| N itself | `node get --id N` | ~200 |
| Ancestor chain (summaries) | `query ancestors --id N --summary` | L × ~50 |
| Same-level siblings (summaries) | `node list --level L --summary` | siblings × ~50 |
| Parent's split decision | `decision list --node <N.parent>` (one decision) | ~200 |
| Historical recall (optional) | `memory recall --query "<N.description>" --k 3` | ~300 |
| **Total** | | **< 2k tokens** |

**DO NOT load:**
- Full subtree of already-processed branches
- Decisions from non-ancestor nodes
- Previous levels' full descriptions (use summaries)
- The entire pyramid (never call `query subtree` mid-decomposition)

#### The BFS Loop

```
current_level = 0
while nodes exist at current_level with status != leaf:
    pending = node list --level current_level --status draft
    for each N in pending:
        1. Load context per the budget table above
        2. Decide: can N be a leaf? (apply 5 criteria mentally)
        3. If YES → go to "Mark as Leaf" (§1.5 below)
        4. If NO → go to "Split into Children" (§1.4 below)
    current_level += 1
```

#### 1.4 Split into Children

This is YOUR reasoning step. Read `N.description` + ancestor summaries. Propose 3-5 children.

**Tag each child's origin** — essential for AC #6:
- `user_stated` → the concept was explicitly in the user's original requirement
- `skill_inferred` → you surfaced it through a clarifying question

**Confirm with the user** (micro-questions, not monologues):
- "I'm splitting `N` into A, B, C. A handles X, B handles Y, C handles Z. Did I miss anything?"
- "Does the order between B and C matter? If yes, that's a dependency edge."

For each confirmed child:
```bash
node create --id <child-id> --name "<name>" --type branch \
  --level <N.level + 1> --description "<one sentence>" \
  --origin <user_stated|skill_inferred>
edge add --kind hierarchy --from <N.id> --to <child-id> --order <position>
```

Store the split decision on N (MANDATORY — AC #5 requires every branch has ≥1 decision):
```bash
decision store --id "d-split-<N.id>" --node <N.id> \
  --question "How to decompose <N.name>?" \
  --options '["chosen-split", "alt-1", "alt-2"]' \
  --chosen "<chosen-split>" \
  --reasoning "<why — prefer user's words>" \
  --tradeoffs "<what we gave up>"
```

**DO NOT recurse into children now.** They will be processed when the BFS loop advances to `current_level + 1`.

After splitting, move to the NEXT node at the current level.

#### 1.5 Mark as Leaf

(unchanged from M2 — capture interface, run criteria check, confirm with `--criteria-confirmed`)
```

- [ ] **Step 2: Verify the SKILL.md is internally consistent**

Read the full file. Ensure Phase 0, Phase 1 (new), Phase 2, Phase 3 form a coherent sequence with no references to DFS or "recurse into each child".

- [ ] **Step 3: Commit**

```bash
git add superpowers-plus/skills/pyramid-decomposition/SKILL.md
git commit -m "feat(skill): rewrite pyramid-decomposition Phase 1 from DFS to BFS"
```

---

### Task 6: Add "Context Management" section to `decomposition-guide.md`

**Files:**
- Modify: `superpowers-plus/skills/pyramid-decomposition/decomposition-guide.md`

- [ ] **Step 1: Append a new section after the Quick Reference Card**

```markdown
---

## Context Management During Decomposition

### Why BFS, not DFS

DFS recursion means processing root → child1 → child1.1 → child1.1.1 before returning to child2. At depth 4, the LLM holds 4 levels of full node detail + decisions + sibling context — easily 5-10k tokens of decomposition state. This is the same context overflow problem the pyramid is designed to solve, just happening during construction instead of implementation.

BFS processes all nodes at level 1 before moving to level 2. At any point, the LLM holds:
- 1 node in full detail (~200 tokens)
- Ancestor chain as summaries (level × ~50 tokens)
- Sibling summaries (~siblings × 50 tokens)
- 1 parent decision (~200 tokens)

Total: ~1-2k tokens regardless of tree depth or width.

### The Summary Principle

**Full detail** = name + description + origin + status + tokens_estimate + created_at + updated_at
**Summary** = id + name + description + status + level + node_type

Use full detail for the ONE node you're currently processing. Use summary for everything else (ancestors, siblings). The full detail is always available via `node get --id X` if needed — don't pre-load it.

### When you're tempted to load more

If you feel you need "more context" to make a decomposition decision:
1. First: re-read the parent's split decision (`decision list --node <parent>`). It captures the reasoning for this branch.
2. Second: try `memory recall --query "<your question>"` to find similar historical decisions.
3. Last resort: `node get --id <specific-ancestor>` to load one ancestor's full detail. But never load more than one extra full node.

If you still can't decide → the node is probably too vague. Ask the user a clarifying question instead of loading more context.
```

- [ ] **Step 2: Commit**

```bash
git add superpowers-plus/skills/pyramid-decomposition/decomposition-guide.md
git commit -m "docs(pyramid): add Context Management section to decomposition guide"
```

---

## Chunk 4: Config — Display Defaults

### Task 7: Add `[display]` section to Config

**Files:**
- Modify: `superpowers-plus/skills/memory-management/scripts/config.py`
- Modify: `superpowers-plus/skills/memory-management/tests/test_config.py`

- [ ] **Step 1: Write the failing test**

```python
# Append to tests/test_config.py
def test_config_display_section(tmp_path):
    path = tmp_path / "config.toml"
    cfg = Config(initialized=True, default_project="demo", display_tree_format="mermaid")
    save_config(path, cfg)
    loaded = load_config(path)
    assert loaded.display_tree_format == "mermaid"

def test_config_display_defaults_to_ascii(tmp_path):
    path = tmp_path / "config.toml"
    cfg = Config(initialized=True)
    save_config(path, cfg)
    loaded = load_config(path)
    assert loaded.display_tree_format == "ascii"
```

- [ ] **Step 2: Run, expect FAIL**

- [ ] **Step 3: Implement**

Add to `Config` dataclass:
```python
@dataclass
class Config:
    # ... existing fields ...
    display_tree_format: str = "ascii"  # ascii | mermaid
```

Update `load_config`:
```python
    display = data.get("display", {})
    return Config(
        # ... existing ...
        display_tree_format=display.get("tree_format", "ascii"),
    )
```

Update `save_config`:
```python
    lines.append("")
    lines.append("[display]")
    lines.append(f'tree_format = "{cfg.display_tree_format}"')
```

- [ ] **Step 4: Run, expect PASS**

- [ ] **Step 5: Commit**

```bash
git add -u
git commit -m "feat(config): add [display] section with tree_format default"
```

---

## Chunk 5: Tree Visualization

### Task 8: Create `tree_renderer.py` — ASCII + Mermaid renderers

**Files:**
- Create: `superpowers-plus/skills/memory-management/scripts/tree_renderer.py`
- Create: `superpowers-plus/skills/memory-management/tests/test_tree_renderer.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_tree_renderer.py
from models import Node
from tree_renderer import render_ascii, render_mermaid

def _make_node(id, name, node_type, level, status="draft"):
    return Node(id=id, project="demo", name=name, node_type=node_type,
                level=level, description=f"{name} desc", status=status,
                origin="user_stated", tokens_estimate=0,
                created_at="t", updated_at="t")

def _sample_tree():
    """Returns (nodes, edges_map) for: root -> [auth, payment], auth -> [login, register]"""
    nodes = {
        "root": _make_node("root", "system", "root", 0, "done"),
        "auth": _make_node("auth", "auth", "branch", 1, "done"),
        "payment": _make_node("payment", "payment", "branch", 1, "draft"),
        "login": _make_node("login", "login", "leaf", 2, "done"),
        "register": _make_node("register", "register", "leaf", 2, "in_progress"),
    }
    children = {
        "root": ["auth", "payment"],
        "auth": ["login", "register"],
        "payment": [],
        "login": [],
        "register": [],
    }
    return nodes, children

# --- ASCII ---
def test_ascii_basic_structure():
    nodes, children = _sample_tree()
    output = render_ascii("root", nodes, children)
    assert "system" in output
    assert "auth" in output
    assert "login" in output
    # Tree connectors present
    assert "├" in output or "└" in output

def test_ascii_shows_status():
    nodes, children = _sample_tree()
    output = render_ascii("root", nodes, children)
    assert "done" in output
    assert "draft" in output

def test_ascii_leaf_done_has_checkmark():
    nodes, children = _sample_tree()
    output = render_ascii("root", nodes, children)
    lines = output.strip().splitlines()
    login_line = [l for l in lines if "login" in l][0]
    assert "✓" in login_line

# --- Mermaid ---
def test_mermaid_valid_syntax():
    nodes, children = _sample_tree()
    output = render_mermaid("root", nodes, children)
    assert output.startswith("graph TD")
    assert "-->" in output

def test_mermaid_has_class_defs():
    nodes, children = _sample_tree()
    output = render_mermaid("root", nodes, children)
    assert "classDef" in output

def test_mermaid_includes_all_nodes():
    nodes, children = _sample_tree()
    output = render_mermaid("root", nodes, children)
    for name in ["system", "auth", "payment", "login", "register"]:
        assert name in output

def test_mermaid_node_types_styled():
    nodes, children = _sample_tree()
    nodes["existing"] = _make_node("existing", "legacy", "existing_module", 1, "done")
    children["root"].append("existing")
    children["existing"] = []
    output = render_mermaid("root", nodes, children)
    assert "existing_module" in output or "legacy" in output

# --- Dependency edges ---
def test_mermaid_with_deps():
    nodes, children = _sample_tree()
    dep_edges = [("login", "register")]  # login depends on register
    output = render_mermaid("root", nodes, children, dep_edges=dep_edges)
    assert "-.->" in output or "-.->|" in output  # dotted arrow
```

- [ ] **Step 2: Run, expect FAIL**

```bash
uv run pytest tests/test_tree_renderer.py -v
```

- [ ] **Step 3: Implement**

```python
# scripts/tree_renderer.py
"""Pure-Python tree renderers. No LLM tokens needed."""
from __future__ import annotations
from typing import Optional

try:
    from .models import Node
except ImportError:
    from models import Node

# ── Status indicators ──
_STATUS_ICON = {
    "done": " ✓",
    "leaf": " ✓",
    "in_progress": " …",
    "draft": "",
}

# ── Mermaid style classes ──
_MERMAID_CLASSES = {
    "leaf":            "fill:#d4edda,stroke:#28a745",   # green
    "branch":          "fill:#cce5ff,stroke:#0d6efd",   # blue
    "root":            "fill:#e2e3e5,stroke:#6c757d",   # gray
    "draft":           "fill:#f8f9fa,stroke:#adb5bd",   # light gray
    "existing_module": "fill:#fff3cd,stroke:#ffc107",   # yellow
    "change_root":     "fill:#ffe0cc,stroke:#fd7e14",   # orange
    "change_branch":   "fill:#ffe0cc,stroke:#fd7e14",
    "change_leaf":     "fill:#ffe0cc,stroke:#fd7e14",
}


def render_ascii(
    root_id: str,
    nodes: dict[str, Node],
    children: dict[str, list[str]],
) -> str:
    lines: list[str] = []

    def _walk(node_id: str, prefix: str, is_last: bool, is_root: bool):
        node = nodes[node_id]
        icon = _STATUS_ICON.get(node.status, "")
        label = f"{node.name} [{node.node_type}, {node.status}]{icon}"

        if is_root:
            lines.append(label)
        else:
            connector = "└── " if is_last else "├── "
            lines.append(f"{prefix}{connector}{label}")

        child_ids = children.get(node_id, [])
        for i, child_id in enumerate(child_ids):
            is_child_last = (i == len(child_ids) - 1)
            child_prefix = prefix + ("    " if is_last else "│   ") if not is_root else ""
            _walk(child_id, child_prefix if is_root else prefix + ("    " if is_last else "│   "),
                  is_child_last, False)

    _walk(root_id, "", True, True)
    return "\n".join(lines)


def render_mermaid(
    root_id: str,
    nodes: dict[str, Node],
    children: dict[str, list[str]],
    dep_edges: Optional[list[tuple[str, str]]] = None,
) -> str:
    lines = ["graph TD"]

    # Node definitions
    for nid, node in nodes.items():
        label = f'{node.name}<br/><small>{node.node_type} · {node.status}</small>'
        lines.append(f'  {nid}["{label}"]')

    # Hierarchy edges
    for parent_id, child_ids in children.items():
        for child_id in child_ids:
            lines.append(f"  {parent_id} --> {child_id}")

    # Dependency edges (dotted)
    if dep_edges:
        for from_id, to_id in dep_edges:
            lines.append(f'  {from_id} -.->|depends| {to_id}')

    # Style classes
    lines.append("")
    for cls_name, style in _MERMAID_CLASSES.items():
        lines.append(f"  classDef {cls_name} {style}")

    # Apply classes
    for nid, node in nodes.items():
        cls = node.node_type if node.node_type in _MERMAID_CLASSES else "draft"
        if node.status == "draft" and node.node_type not in ("existing_module",):
            cls = "draft"
        lines.append(f"  class {nid} {cls}")

    return "\n".join(lines)
```

- [ ] **Step 4: Run, expect PASS**

- [ ] **Step 5: Commit**

```bash
git add scripts/tree_renderer.py tests/test_tree_renderer.py
git commit -m "feat(memory-cli): add ASCII + Mermaid tree renderers"
```

---

### Task 9: Add `memory tree` CLI command

**Files:**
- Modify: `superpowers-plus/skills/memory-management/scripts/memory_cli.py`
- Create: `superpowers-plus/skills/memory-management/tests/test_cli_tree.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_cli_tree.py
import json

def _seed_tree(cli):
    cli("init", "--project", "demo", "--embedding", "skip", "--non-interactive")
    cli("node", "create", "--id", "root", "--name", "system", "--type", "root",
        "--level", "0", "--description", "top", "--origin", "user_stated")
    cli("node", "create", "--id", "auth", "--name", "auth", "--type", "branch",
        "--level", "1", "--description", "auth module", "--origin", "user_stated")
    cli("node", "create", "--id", "login", "--name", "login", "--type", "leaf",
        "--level", "2", "--description", "login page", "--origin", "skill_inferred")
    cli("edge", "add", "--kind", "hierarchy", "--from", "root", "--to", "auth")
    cli("edge", "add", "--kind", "hierarchy", "--from", "auth", "--to", "login")

def test_tree_ascii_default(run_cli):
    _seed_tree(run_cli)
    r = run_cli("memory", "tree")
    out = json.loads(r.stdout)
    assert out["ok"]
    assert "system" in out["data"]["tree"]
    assert "auth" in out["data"]["tree"]
    assert "login" in out["data"]["tree"]
    assert out["data"]["format"] == "ascii"

def test_tree_mermaid_explicit(run_cli):
    _seed_tree(run_cli)
    r = run_cli("memory", "tree", "--format", "mermaid")
    out = json.loads(r.stdout)
    assert "graph TD" in out["data"]["tree"]
    assert out["data"]["format"] == "mermaid"

def test_tree_subtree_from_root(run_cli):
    _seed_tree(run_cli)
    r = run_cli("memory", "tree", "--root", "auth")
    tree = json.loads(r.stdout)["data"]["tree"]
    assert "auth" in tree
    assert "login" in tree
    # root should NOT appear when --root is auth
    lines = tree.strip().splitlines()
    assert lines[0].startswith("auth")

def test_tree_mermaid_with_deps(run_cli):
    _seed_tree(run_cli)
    cli = run_cli
    cli("node", "create", "--id", "pay", "--name", "payment", "--type", "leaf",
        "--level", "1", "--description", "pay", "--origin", "user_stated")
    cli("edge", "add", "--kind", "hierarchy", "--from", "root", "--to", "pay")
    cli("edge", "add", "--kind", "dependency", "--from", "login", "--to", "pay")
    r = cli("memory", "tree", "--format", "mermaid", "--show-deps")
    tree = json.loads(r.stdout)["data"]["tree"]
    assert "-.->|depends|" in tree

def test_tree_respects_config_default(run_cli):
    """When config says mermaid, tree defaults to mermaid."""
    _seed_tree(run_cli)
    run_cli("config", "set", "--key", "display.tree_format", "--value", "mermaid")
    r = run_cli("memory", "tree")
    out = json.loads(r.stdout)
    assert out["data"]["format"] == "mermaid"
```

- [ ] **Step 2: Run, expect FAIL**

```bash
uv run pytest tests/test_cli_tree.py -v
```

- [ ] **Step 3: Implement**

```python
@memory.command("tree")
@click.option("--root", "root_id", default=None,
              help="Root node ID. Defaults to the project's root node.")
@click.option("--format", "fmt", default=None,
              type=click.Choice(["ascii", "mermaid"]),
              help="Output format. Defaults to config [display] tree_format.")
@click.option("--show-deps", is_flag=True, help="Include dependency edges (mermaid only).")
@click.option("--project")
def memory_tree(root_id, fmt, show_deps, project):
    """Render the pyramid as ASCII or Mermaid. No LLM tokens needed."""
    s, cfg = _store()
    p = _project(project, cfg)

    # Resolve format from config if not specified
    if fmt is None:
        fmt = getattr(cfg, "display_tree_format", "ascii")

    # Find root
    if root_id is None:
        roots = [n for n in s.list_nodes(p) if n.node_type in ("root", "change_root")]
        if not roots:
            emit_error("no root node found", code="no_root")
            return
        root_id = roots[0].id

    # Build node map and children map from subtree
    subtree_nodes = s.query_subtree(p, root_id)
    nodes_map = {n.id: n for n in subtree_nodes}
    children_map = {n.id: [c.id for c in s.query_children(p, n.id)] for n in subtree_nodes}

    from tree_renderer import render_ascii, render_mermaid

    if fmt == "ascii":
        tree_str = render_ascii(root_id, nodes_map, children_map)
    else:
        dep_edges = None
        if show_deps:
            dep_edges = []
            for n in subtree_nodes:
                for dep in s.query_deps(p, n.id):
                    if dep.id in nodes_map:
                        dep_edges.append((n.id, dep.id))
        tree_str = render_mermaid(root_id, nodes_map, children_map, dep_edges=dep_edges)

    emit({"tree": tree_str, "format": fmt, "node_count": len(subtree_nodes)})
```

- [ ] **Step 4: Run, expect PASS**

- [ ] **Step 5: Commit**

```bash
git add -u && git add tests/test_cli_tree.py
git commit -m "feat(memory-cli): add memory tree command with ascii/mermaid output"
```

---

### Task 10: Update Phase 3 hand-off to use `memory tree`

**Files:**
- Modify: `superpowers-plus/skills/pyramid-decomposition/SKILL.md`

- [ ] **Step 1: Replace the Phase 3 subtree dump with `memory tree`**

Find the Phase 3 section. Replace the presentation logic with:

```markdown
#### 3.2 Show the pyramid to the user

Use `memory tree` — it renders the tree mechanically. **Do NOT format the tree yourself** (wastes tokens, inconsistent output).

```bash
# Default: uses config [display] tree_format (ascii for terminal, mermaid for IDE)
memory tree

# Subtree from a specific node
memory tree --root auth

# Mermaid with dependency edges (for docs/PRs)
memory tree --format mermaid --show-deps
```

**Format auto-selection** (no need to ask the user):
- Responding in terminal (Claude Code, Codex CLI, Gemini CLI) → config default is `ascii`
- Writing to a markdown file, PR body, or documentation → use `--format mermaid`
- User explicitly requests a format → use that format

For large pyramids (> 15 nodes), show the tree, then ask:
"This is the full pyramid. Want me to expand any branch's details, or does the structure look right?"

For very large pyramids (> 50 nodes), show subtree by subtree:
```bash
memory tree --root <subsystem-1>
memory tree --root <subsystem-2>
```
```

- [ ] **Step 2: Commit**

```bash
git add superpowers-plus/skills/pyramid-decomposition/SKILL.md
git commit -m "feat(skill): use memory tree for Phase 3 visualization"
```

---

### Task 11: Run full test suite + tag M3

- [ ] **Step 1: Run all tests**

```bash
cd superpowers-plus/skills/memory-management
uv run pytest -v
```

Expected: All M1 + M2 + M3 tests PASS.

- [ ] **Step 2: Tag**

```bash
git tag -a m3-bfs-context -m "Milestone 3: BFS context control + --level/--summary + recompute-tokens + memory tree"
```

- [ ] **Step 3: Update spec §11.5**

Add: `**Status: Shipped 2026-MM-DD (tag: m3-bfs-context)**`

- [ ] **Step 4: Commit**

```bash
git add docs/superpowers/specs/2026-04-07-pyramid-memory-skill-design.md
git commit -m "docs: mark Milestone 3 as shipped"
```

---

## Self-Review

### Spec coverage
| Spec M3 scope | Plan task |
|---|---|
| `node list --level L` | Task 1 |
| `--summary` mode | Task 2 |
| `memory recompute-tokens` | Task 3 |
| SKILL.md Phase 1 DFS→BFS | Task 5 |
| Context budget rule | Tasks 4, 5 |
| Config `[display] tree_format` | Task 7 |
| `tree_renderer.py` (ASCII + Mermaid) | Task 8 |
| `memory tree` CLI command | Task 9 |
| Phase 3 visualization with `memory tree` | Task 10 |
| decomposition-guide.md update | Task 6 |

### M3 exit criteria mapping
| Criterion | Verified by |
|---|---|
| 4-level 30-node pyramid stays < 3k tokens per step | Task 4 (41-node tree, 12k char budget ≈ 3k tokens) |
| `node list --level 2 --summary` < 100ms on 1000 nodes | Task 4 doesn't test 1000 nodes — **note: needs a separate perf test in M4 or a manual check** |
| `memory tree` outputs valid ASCII for terminal harnesses | Task 8 (renderer tests), Task 9 (CLI tests) |
| `memory tree --format mermaid` outputs valid Mermaid | Task 8 (renderer tests), Task 9 (CLI tests) |
| Format auto-selection via config `[display]` | Task 7 (config), Task 9 (`test_tree_respects_config_default`) |
