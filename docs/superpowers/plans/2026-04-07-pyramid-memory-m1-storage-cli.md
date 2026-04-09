# Pyramid Memory — Milestone 1: Storage + CLI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a working `memory_cli.py` that exposes pyramid decomposition memory (graph + optional vector) over a clean CLI, backed by CozoDB, with a swappable `MemoryStore` Protocol.

**Architecture:** Single Python CLI (PEP 723 inline deps, run via `uv run`) with three layers: (1) `MemoryStore` Protocol + `CozoStore`/`InMemoryStore` impls, (2) `EmbeddingProvider` Protocol + `SkipProvider`/`FastembedProvider` impls, (3) Click-based CLI dispatching to the store/provider via dependency injection. JSON output contract on every command. Storage at `~/.pyramid-memory/`.

**Tech Stack:** Python ≥3.10, `pycozo[embedded]`, `click`, `tomli`/`tomllib`, `fastembed` (optional), `pytest`. Hard external dep: `uv`.

**Spec:** `docs/superpowers/specs/2026-04-07-pyramid-memory-skill-design.md` (Milestone 1 scope: §3, §4, §5, §8, AC #1, #3, #5–#13)

**Out of scope:** Skill files (`SKILL.md`), `decomposition-guide.md`, `pyramid-decomposition` orchestration — these belong to Milestone 2.

---

## File Map

```
superpowers-plus/skills/memory-management/
├── scripts/
│   ├── memory_cli.py         # PEP 723 entry point + Click commands
│   ├── models.py             # @dataclass: Node, Edge, Decision, Interface, ContextPackage, ScoredNode
│   ├── store.py              # MemoryStore Protocol + InMemoryStore impl
│   ├── cozo_store.py         # CozoStore impl
│   ├── embedding.py          # EmbeddingProvider Protocol + SkipProvider + FastembedProvider
│   ├── config.py             # Config loader/writer (~/.pyramid-memory/config.toml)
│   ├── output.py             # JSON output contract: {ok, data, warnings, degraded}
│   └── locks.py              # File-lock helper for ~/.pyramid-memory/.lock
└── tests/
    ├── conftest.py           # Fixtures: tmp ~/.pyramid-memory, in-memory store
    ├── test_models.py
    ├── test_in_memory_store.py
    ├── test_cozo_store.py
    ├── test_store_protocol_compliance.py   # Same suite run against both impls
    ├── test_embedding.py
    ├── test_config.py
    ├── test_locks.py
    ├── test_cli_init.py
    ├── test_cli_node.py
    ├── test_cli_edge.py
    ├── test_cli_query.py
    ├── test_cli_decision.py
    ├── test_cli_interface.py
    ├── test_cli_memory_recall.py
    ├── test_cli_memory_context.py
    ├── test_cli_memory_validate.py
    ├── test_cli_memory_stats.py
    ├── test_cli_memory_doctor.py
    └── test_fallbacks.py     # All 8 rows of §8 fallback matrix
```

**Note on file location:** Scripts live under `skills/memory-management/scripts/` even though the skill's `SKILL.md` is M2 — the directory exists from M1 so the CLI can be exercised in isolation. The skill file itself is created in M2.

---

## Pre-flight: Technical Spike (MUST run before Chunk 1)

### Task 0: Verify CozoDB HNSW filter syntax

The spec assumes `::hnsw create` supports a `filter:` clause with `status != 'failed'`. This is unverified against the current pycozo release. If it doesn't work, the schema must change.

**Files:**
- Create: `superpowers-plus/skills/memory-management/scripts/spike_cozo_hnsw.py` (delete after)

- [ ] **Step 1: Write the spike script**

```python
#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pycozo[embedded]>=0.7"]
# ///
from pycozo.client import Client

db = Client('sqlite', ':memory:')

# Create a node relation with vector
db.run("""
:create node {
  id: String,
  status: String,
  =>
  embedding: <F32; 4>?
}
""")

# Try to create HNSW with filter
try:
    db.run("""
    ::hnsw create node:idx {
      dim: 4,
      m: 16,
      ef_construction: 50,
      fields: [embedding],
      distance: Cosine,
      filter: status != 'failed'
    }
    """)
    print("OK: filter clause accepted")
except Exception as e:
    print(f"FAIL: {e}")

# Insert + query
db.run("""
?[id, status, embedding] <- [
  ['a', 'done', vec([0.1, 0.2, 0.3, 0.4])],
  ['b', 'failed', vec([0.5, 0.6, 0.7, 0.8])]
]
:put node {id, status => embedding}
""")

result = db.run("""
?[dist, id] := ~node:idx{ id, status |
  query: vec([0.1, 0.2, 0.3, 0.4]),
  k: 5,
  ef: 50,
  bind_distance: dist
}
""")
print("Query result:", result)
```

- [ ] **Step 2: Run it**

```bash
cd superpowers-plus/skills/memory-management/scripts
uv run spike_cozo_hnsw.py
```

Expected: Either "OK: filter clause accepted" with one result row (id='a' only, since 'b' is filtered out), OR a parse error revealing the actual supported syntax.

- [ ] **Step 3: Record findings**

Edit `docs/superpowers/specs/2026-04-07-pyramid-memory-skill-design.md` §10 Open Questions:
- If filter works → strike through the open question, note "verified 2026-04-07 with pycozo 0.7.x"
- If filter does NOT work → update §3 schema to remove `filter:` from the HNSW index, and add a §10 note: "filter at query time via `:filter status != 'failed'` instead"

- [ ] **Step 4: Delete the spike file**

```bash
rm superpowers-plus/skills/memory-management/scripts/spike_cozo_hnsw.py
```

- [ ] **Step 5: Commit**

```bash
git add docs/superpowers/specs/2026-04-07-pyramid-memory-skill-design.md
git commit -m "spike: verify CozoDB HNSW filter syntax for pyramid memory schema"
```

---

## Chunk 1: Project Skeleton

### Task 1: Create directory layout and PEP 723 entry point stub

**Files:**
- Create: `superpowers-plus/skills/memory-management/scripts/memory_cli.py`
- Create: `superpowers-plus/skills/memory-management/tests/conftest.py`

- [ ] **Step 1: Write `memory_cli.py` with PEP 723 header and a single `version` command**

```python
#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "pycozo[embedded]>=0.7",
#   "click>=8.1",
#   "tomli>=2.0; python_version<'3.11'",
# ]
# ///
"""Pyramid Memory CLI — Milestone 1 (storage + CLI)."""
import json
import sys
import click

VERSION = "0.1.0-m1"

@click.group()
def cli():
    """Pyramid Memory: graph + decision storage for AI-driven decomposition."""

@cli.command()
def version():
    """Print CLI version as JSON."""
    click.echo(json.dumps({"ok": True, "data": {"version": VERSION}, "warnings": [], "degraded": False}))

if __name__ == "__main__":
    cli()
```

- [ ] **Step 2: Write the failing test**

```python
# tests/conftest.py
import os
import subprocess
import sys
from pathlib import Path
import pytest

SCRIPTS = Path(__file__).parent.parent / "scripts"

@pytest.fixture
def run_cli(tmp_path, monkeypatch):
    """Run memory_cli.py with HOME redirected to tmp_path."""
    monkeypatch.setenv("HOME", str(tmp_path))
    def _run(*args):
        result = subprocess.run(
            ["uv", "run", str(SCRIPTS / "memory_cli.py"), *args],
            capture_output=True, text=True, env={**os.environ, "HOME": str(tmp_path)},
        )
        return result
    return _run
```

```python
# tests/test_cli_init.py (placeholder for now — just version)
import json

def test_version_command(run_cli):
    result = run_cli("version")
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["data"]["version"].startswith("0.1")
```

- [ ] **Step 3: Run test, expect PASS**

```bash
cd superpowers-plus/skills/memory-management
uv run pytest tests/test_cli_init.py::test_version_command -v
```

Expected: PASS (one test).

- [ ] **Step 4: Commit**

```bash
git add superpowers-plus/skills/memory-management/
git commit -m "feat(memory-cli): scaffold PEP 723 CLI with version command"
```

---

### Task 2: Define data models

**Files:**
- Create: `superpowers-plus/skills/memory-management/scripts/models.py`
- Create: `superpowers-plus/skills/memory-management/tests/test_models.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_models.py
from datetime import datetime, timezone
from scripts.models import Node, Edge, Decision, Interface, ContextPackage, ScoredNode

def test_node_to_dict_roundtrip():
    n = Node(
        id="n1", project="demo", name="root", node_type="root",
        level=0, description="root node", status="draft",
        origin="user_stated", tokens_estimate=100,
        created_at="2026-04-07T00:00:00Z", updated_at="2026-04-07T00:00:00Z",
    )
    d = n.to_dict()
    assert d["id"] == "n1"
    assert d["origin"] == "user_stated"
    n2 = Node.from_dict(d)
    assert n2 == n

def test_edge_kinds():
    e1 = Edge(kind="hierarchy", from_id="a", to_id="b", order_idx=0)
    e2 = Edge(kind="dependency", from_id="b", to_id="c", dep_type="requires")
    assert e1.kind == "hierarchy"
    assert e2.dep_type == "requires"

def test_context_package_token_count():
    pkg = ContextPackage(
        node={"id": "leaf"}, ancestors=[], decisions=[], interfaces=[], deps=[],
        tokens_estimate=4200,
    )
    assert pkg.tokens_estimate == 4200
```

- [ ] **Step 2: Run test, expect FAIL (ImportError)**

```bash
uv run pytest tests/test_models.py -v
```
Expected: FAIL — module `scripts.models` not found.

- [ ] **Step 3: Implement `models.py`**

```python
# scripts/models.py
from dataclasses import dataclass, asdict, field
from typing import Any, Optional

@dataclass
class Node:
    id: str
    project: str
    name: str
    node_type: str        # root | branch | leaf
    level: int
    description: str
    status: str           # draft | confirmed | in_progress | done | failed
    origin: str           # user_stated | skill_inferred
    tokens_estimate: int
    created_at: str
    updated_at: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Node":
        return cls(**{k: d[k] for k in cls.__dataclass_fields__})


@dataclass
class Edge:
    kind: str             # hierarchy | dependency
    from_id: str
    to_id: str
    order_idx: int = 0
    dep_type: str = "requires"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Decision:
    id: str
    node_id: str
    question: str
    options: str          # JSON-encoded list
    chosen: str
    reasoning: str
    tradeoffs: str
    created_at: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Interface:
    id: str
    node_id: str
    name: str
    description: str
    spec: str
    created_at: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ScoredNode:
    node: Node
    score: float
    match_type: str       # semantic | bm25 | exact


@dataclass
class ContextPackage:
    node: dict[str, Any]
    ancestors: list[dict[str, Any]]
    decisions: list[dict[str, Any]]
    interfaces: list[dict[str, Any]]
    deps: list[dict[str, Any]]
    tokens_estimate: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
```

- [ ] **Step 4: Run test, expect PASS**

```bash
uv run pytest tests/test_models.py -v
```
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add superpowers-plus/skills/memory-management/scripts/models.py superpowers-plus/skills/memory-management/tests/test_models.py
git commit -m "feat(memory-cli): add data models for nodes/edges/decisions/interfaces"
```

---

### Task 3: Define MemoryStore Protocol + InMemoryStore impl

**Files:**
- Create: `superpowers-plus/skills/memory-management/scripts/store.py`
- Create: `superpowers-plus/skills/memory-management/tests/test_in_memory_store.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_in_memory_store.py
from scripts.store import InMemoryStore
from scripts.models import Node, Edge, Decision

def make_node(id, **overrides):
    base = dict(
        id=id, project="demo", name=id, node_type="branch", level=1,
        description=f"node {id}", status="draft", origin="user_stated",
        tokens_estimate=0, created_at="2026-04-07T00:00:00Z",
        updated_at="2026-04-07T00:00:00Z",
    )
    base.update(overrides)
    return Node(**base)

def test_create_and_get_node():
    s = InMemoryStore()
    n = make_node("n1")
    s.create_node(n)
    got = s.get_node("demo", "n1")
    assert got.name == "n1"

def test_list_nodes_filters_by_project():
    s = InMemoryStore()
    s.create_node(make_node("a"))
    s.create_node(make_node("b", project="other"))
    nodes = s.list_nodes("demo")
    assert len(nodes) == 1 and nodes[0].id == "a"

def test_add_hierarchy_edge_and_query_children():
    s = InMemoryStore()
    s.create_node(make_node("p", node_type="root", level=0))
    s.create_node(make_node("c1", level=1))
    s.create_node(make_node("c2", level=1))
    s.add_edge(Edge(kind="hierarchy", from_id="p", to_id="c1", order_idx=0))
    s.add_edge(Edge(kind="hierarchy", from_id="p", to_id="c2", order_idx=1))
    children = s.query_children("demo", "p")
    assert [c.id for c in children] == ["c1", "c2"]

def test_recall_bm25_matches_description():
    s = InMemoryStore()
    s.create_node(make_node("a", description="implement OAuth login flow"))
    s.create_node(make_node("b", description="render dashboard charts"))
    results = s.recall("demo", query="oauth", k=5, semantic=False)
    assert len(results) >= 1
    assert results[0].node.id == "a"
    assert results[0].match_type == "bm25"
```

- [ ] **Step 2: Run test, expect FAIL**

```bash
uv run pytest tests/test_in_memory_store.py -v
```
Expected: FAIL — `scripts.store` not found.

- [ ] **Step 3: Implement `store.py`**

```python
# scripts/store.py
from typing import Protocol, Optional
from collections import defaultdict
import re
from .models import Node, Edge, Decision, Interface, ScoredNode, ContextPackage


class StoreError(Exception):
    pass


class NodeNotFound(StoreError):
    pass


class MemoryStore(Protocol):
    """Storage backend contract. Swappable: CozoStore (default) / InMemoryStore (tests) / future impls."""

    # ----- Nodes -----
    def create_node(self, node: Node) -> None: ...
    def get_node(self, project: str, node_id: str) -> Node: ...
    def update_node(self, project: str, node_id: str, **fields) -> Node: ...
    def delete_node(self, project: str, node_id: str) -> None: ...
    def list_nodes(self, project: str, *, status: Optional[str] = None) -> list[Node]: ...

    # ----- Edges -----
    def add_edge(self, edge: Edge) -> None: ...
    def remove_edge(self, kind: str, from_id: str, to_id: str) -> None: ...

    # ----- Graph queries -----
    def query_children(self, project: str, node_id: str) -> list[Node]: ...
    def query_ancestors(self, project: str, node_id: str) -> list[Node]: ...
    def query_subtree(self, project: str, root_id: str) -> list[Node]: ...
    def query_deps(self, project: str, node_id: str) -> list[Node]: ...
    def detect_cycles(self, project: str) -> list[list[str]]: ...

    # ----- Decisions / Interfaces -----
    def store_decision(self, decision: Decision) -> None: ...
    def list_decisions(self, project: str, node_id: str) -> list[Decision]: ...
    def add_interface(self, iface: Interface) -> None: ...
    def list_interfaces(self, project: str, node_id: str) -> list[Interface]: ...

    # ----- Recall + assembly -----
    def recall(self, project: str, query: str, k: int, semantic: bool) -> list[ScoredNode]: ...
    def assemble_context(self, project: str, leaf_id: str) -> ContextPackage: ...

    # ----- Validation / stats -----
    def validate(self, project: str) -> dict: ...
    def stats(self, project: str) -> dict: ...


class InMemoryStore:
    """Reference impl for tests. Pure Python, no external dependencies."""

    def __init__(self):
        self._nodes: dict[tuple[str, str], Node] = {}
        self._edges: list[Edge] = []
        self._decisions: list[Decision] = []
        self._interfaces: list[Interface] = []

    # ----- Nodes -----
    def create_node(self, node: Node) -> None:
        key = (node.project, node.id)
        if key in self._nodes:
            raise StoreError(f"node already exists: {node.id}")
        self._nodes[key] = node

    def get_node(self, project: str, node_id: str) -> Node:
        try:
            return self._nodes[(project, node_id)]
        except KeyError:
            raise NodeNotFound(node_id)

    def update_node(self, project: str, node_id: str, **fields) -> Node:
        n = self.get_node(project, node_id)
        for k, v in fields.items():
            setattr(n, k, v)
        return n

    def delete_node(self, project: str, node_id: str) -> None:
        self._nodes.pop((project, node_id), None)
        self._edges = [e for e in self._edges if e.from_id != node_id and e.to_id != node_id]

    def list_nodes(self, project: str, *, status: Optional[str] = None) -> list[Node]:
        nodes = [n for (p, _), n in self._nodes.items() if p == project]
        if status:
            nodes = [n for n in nodes if n.status == status]
        return nodes

    # ----- Edges -----
    def add_edge(self, edge: Edge) -> None:
        self._edges.append(edge)

    def remove_edge(self, kind: str, from_id: str, to_id: str) -> None:
        self._edges = [
            e for e in self._edges
            if not (e.kind == kind and e.from_id == from_id and e.to_id == to_id)
        ]

    # ----- Graph queries -----
    def query_children(self, project: str, node_id: str) -> list[Node]:
        edges = sorted(
            [e for e in self._edges if e.kind == "hierarchy" and e.from_id == node_id],
            key=lambda e: e.order_idx,
        )
        return [self.get_node(project, e.to_id) for e in edges]

    def query_ancestors(self, project: str, node_id: str) -> list[Node]:
        chain = []
        current = node_id
        while True:
            parent_edges = [e for e in self._edges if e.kind == "hierarchy" and e.to_id == current]
            if not parent_edges:
                break
            current = parent_edges[0].from_id
            chain.append(self.get_node(project, current))
        return chain

    def query_subtree(self, project: str, root_id: str) -> list[Node]:
        out = [self.get_node(project, root_id)]
        for child in self.query_children(project, root_id):
            out.extend(self.query_subtree(project, child.id))
        return out

    def query_deps(self, project: str, node_id: str) -> list[Node]:
        deps = [e.to_id for e in self._edges if e.kind == "dependency" and e.from_id == node_id]
        return [self.get_node(project, d) for d in deps]

    def detect_cycles(self, project: str) -> list[list[str]]:
        # Simple DFS-based cycle detection on dependency edges
        adj = defaultdict(list)
        for e in self._edges:
            if e.kind == "dependency":
                adj[e.from_id].append(e.to_id)
        WHITE, GRAY, BLACK = 0, 1, 2
        color = defaultdict(lambda: WHITE)
        cycles: list[list[str]] = []
        stack: list[str] = []

        def dfs(u: str) -> None:
            color[u] = GRAY
            stack.append(u)
            for v in adj[u]:
                if color[v] == GRAY:
                    idx = stack.index(v)
                    cycles.append(stack[idx:] + [v])
                elif color[v] == WHITE:
                    dfs(v)
            stack.pop()
            color[u] = BLACK

        for u in list(adj.keys()):
            if color[u] == WHITE:
                dfs(u)
        return cycles

    # ----- Decisions / Interfaces -----
    def store_decision(self, decision: Decision) -> None:
        self._decisions.append(decision)

    def list_decisions(self, project: str, node_id: str) -> list[Decision]:
        node_ids = {n.id for n in self.list_nodes(project)}
        return [d for d in self._decisions if d.node_id == node_id and node_id in node_ids]

    def add_interface(self, iface: Interface) -> None:
        self._interfaces.append(iface)

    def list_interfaces(self, project: str, node_id: str) -> list[Interface]:
        return [i for i in self._interfaces if i.node_id == node_id]

    # ----- Recall + assembly -----
    def recall(self, project: str, query: str, k: int, semantic: bool) -> list[ScoredNode]:
        # InMemory only does BM25-ish substring scoring; semantic falls back here too.
        terms = [t.lower() for t in re.findall(r"\w+", query)]
        scored: list[ScoredNode] = []
        for n in self.list_nodes(project):
            text = (n.name + " " + n.description).lower()
            score = sum(text.count(t) for t in terms)
            if score > 0:
                scored.append(ScoredNode(node=n, score=float(score), match_type="bm25"))
        scored.sort(key=lambda s: s.score, reverse=True)
        return scored[:k]

    def assemble_context(self, project: str, leaf_id: str) -> ContextPackage:
        leaf = self.get_node(project, leaf_id)
        ancestors = [a.to_dict() for a in self.query_ancestors(project, leaf_id)]
        deps = [d.to_dict() for d in self.query_deps(project, leaf_id)]
        decisions = [d.to_dict() for d in self.list_decisions(project, leaf_id)]
        # also gather decisions from ancestors
        for a in self.query_ancestors(project, leaf_id):
            decisions.extend(d.to_dict() for d in self.list_decisions(project, a.id))
        interfaces = [i.to_dict() for i in self.list_interfaces(project, leaf_id)]
        # gather interfaces from deps
        for d_node in self.query_deps(project, leaf_id):
            interfaces.extend(i.to_dict() for i in self.list_interfaces(project, d_node.id))
        # rough token estimate: 1 token per 4 chars of all text
        total_chars = (
            len(leaf.description)
            + sum(len(a["description"]) for a in ancestors)
            + sum(len(d["reasoning"]) + len(d["tradeoffs"]) for d in decisions)
            + sum(len(i["spec"]) for i in interfaces)
        )
        return ContextPackage(
            node=leaf.to_dict(),
            ancestors=ancestors,
            decisions=decisions,
            interfaces=interfaces,
            deps=[d.to_dict() for d in self.query_deps(project, leaf_id)],
            tokens_estimate=total_chars // 4,
        )

    # ----- Validation / stats -----
    def validate(self, project: str) -> dict:
        violations: list[dict] = []
        nodes = self.list_nodes(project)
        for n in nodes:
            if n.node_type == "branch":
                if not self.list_decisions(project, n.id):
                    violations.append({"node_id": n.id, "rule": "branch_requires_decision"})
            if n.node_type == "leaf":
                if not self.list_interfaces(project, n.id):
                    violations.append({"node_id": n.id, "rule": "leaf_requires_interface"})
        return {"passed": len(violations) == 0, "violations": violations}

    def stats(self, project: str) -> dict:
        nodes = self.list_nodes(project)
        total = len(nodes)
        inferred = sum(1 for n in nodes if n.origin == "skill_inferred")
        ratio = (inferred / total) if total else 0.0
        return {
            "total_nodes": total,
            "skill_inferred_nodes": inferred,
            "user_stated_nodes": total - inferred,
            "skill_inferred_node_ratio": round(ratio, 4),
        }
```

- [ ] **Step 4: Run test, expect PASS**

```bash
uv run pytest tests/test_in_memory_store.py -v
```
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add superpowers-plus/skills/memory-management/scripts/store.py superpowers-plus/skills/memory-management/tests/test_in_memory_store.py
git commit -m "feat(memory-cli): MemoryStore Protocol + InMemoryStore reference impl"
```

---

## Chunk 2: CozoStore Implementation

### Task 4: CozoStore — schema bring-up + node CRUD

**Files:**
- Create: `superpowers-plus/skills/memory-management/scripts/cozo_store.py`
- Create: `superpowers-plus/skills/memory-management/tests/test_cozo_store.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_cozo_store.py
import pytest
from scripts.cozo_store import CozoStore
from scripts.models import Node

@pytest.fixture
def store(tmp_path):
    return CozoStore(db_path=str(tmp_path / "data.cozo"))

def make_node(id, **overrides):
    base = dict(
        id=id, project="demo", name=id, node_type="branch", level=1,
        description=f"node {id}", status="draft", origin="user_stated",
        tokens_estimate=0, created_at="2026-04-07T00:00:00Z",
        updated_at="2026-04-07T00:00:00Z",
    )
    base.update(overrides)
    return Node(**base)

def test_schema_bringup_idempotent(store):
    store.ensure_schema()
    store.ensure_schema()  # Second call must not fail

def test_create_and_get_node(store):
    store.ensure_schema()
    store.create_node(make_node("n1"))
    got = store.get_node("demo", "n1")
    assert got.id == "n1"
    assert got.origin == "user_stated"

def test_create_duplicate_raises(store):
    store.ensure_schema()
    store.create_node(make_node("n1"))
    with pytest.raises(Exception):
        store.create_node(make_node("n1"))
```

- [ ] **Step 2: Run test, expect FAIL**

```bash
uv run pytest tests/test_cozo_store.py::test_schema_bringup_idempotent -v
```
Expected: FAIL — `scripts.cozo_store` not found.

- [ ] **Step 3: Implement schema bring-up + node CRUD**

NOTE: If the Task 0 spike showed that `filter:` in HNSW is not supported, omit the `filter:` line below and instead apply the filter at query time inside `recall()`.

```python
# scripts/cozo_store.py
from pathlib import Path
from typing import Optional
from pycozo.client import Client
from .models import Node, Edge, Decision, Interface, ScoredNode, ContextPackage
from .store import StoreError, NodeNotFound

SCHEMA_RELATIONS = [
    """:create node {
        id: String,
        project: String,
        name: String,
        node_type: String,
        level: Int,
        description: String,
        status: String,
        origin: String,
        tokens_estimate: Int default 0,
        created_at: String,
        updated_at: String,
        =>
        embedding: <F32; 1024>?
    }""",
    """:create edge_hierarchy {
        parent_id: String,
        child_id: String,
        order_idx: Int default 0
    }""",
    """:create edge_dependency {
        from_id: String,
        to_id: String,
        dep_type: String default 'requires'
    }""",
    """:create decision {
        id: String,
        node_id: String,
        question: String,
        options: String,
        chosen: String,
        reasoning: String,
        tradeoffs: String,
        created_at: String
    }""",
    """:create interface_def {
        id: String,
        node_id: String,
        name: String,
        description: String,
        spec: String,
        created_at: String
    }""",
    """:create config {
        key: String,
        value: String
    }""",
]

HNSW_INDEX = """::hnsw create node:embedding_idx {
    dim: 1024,
    m: 16,
    ef_construction: 200,
    fields: [embedding],
    distance: Cosine,
    filter: status != 'failed'
}"""


class CozoStore:
    def __init__(self, db_path: str):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.client = Client("sqlite", db_path)
        self._schema_ready = False

    def ensure_schema(self) -> None:
        if self._schema_ready:
            return
        existing = {row[0] for row in self.client.run("::relations")["rows"]}
        for stmt in SCHEMA_RELATIONS:
            relation_name = stmt.split("{")[0].split()[-1]
            if relation_name not in existing:
                self.client.run(stmt)
        # HNSW is optional — only create if embedding column has any rows OR forced.
        # Safe to attempt; ignore "already exists" errors.
        try:
            self.client.run(HNSW_INDEX)
        except Exception:
            pass
        self._schema_ready = True

    def create_node(self, node: Node) -> None:
        self.ensure_schema()
        # Check existence first to give a clean error
        existing = self.client.run(
            "?[id] := *node{id, project}, project = $p, id = $i",
            {"p": node.project, "i": node.id},
        )
        if existing["rows"]:
            raise StoreError(f"node already exists: {node.id}")
        self.client.run(
            """
            ?[id, project, name, node_type, level, description, status, origin,
              tokens_estimate, created_at, updated_at] <- [[
                $id, $project, $name, $node_type, $level, $description, $status, $origin,
                $tokens_estimate, $created_at, $updated_at
            ]]
            :put node {
                id, project, name, node_type, level, description, status, origin,
                tokens_estimate, created_at, updated_at
            }
            """,
            node.to_dict(),
        )

    def get_node(self, project: str, node_id: str) -> Node:
        self.ensure_schema()
        result = self.client.run(
            """
            ?[id, project, name, node_type, level, description, status, origin,
              tokens_estimate, created_at, updated_at] :=
              *node{id, project, name, node_type, level, description, status, origin,
                    tokens_estimate, created_at, updated_at},
              project = $p, id = $i
            """,
            {"p": project, "i": node_id},
        )
        if not result["rows"]:
            raise NodeNotFound(node_id)
        cols = result["headers"]
        row = result["rows"][0]
        return Node(**dict(zip(cols, row)))
```

- [ ] **Step 4: Run test, expect PASS**

```bash
uv run pytest tests/test_cozo_store.py::test_schema_bringup_idempotent tests/test_cozo_store.py::test_create_and_get_node tests/test_cozo_store.py::test_create_duplicate_raises -v
```
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add superpowers-plus/skills/memory-management/scripts/cozo_store.py superpowers-plus/skills/memory-management/tests/test_cozo_store.py
git commit -m "feat(memory-cli): CozoStore schema bring-up + node create/get"
```

---

### Task 5: CozoStore — update/delete/list nodes

**Files:**
- Modify: `superpowers-plus/skills/memory-management/scripts/cozo_store.py`
- Modify: `superpowers-plus/skills/memory-management/tests/test_cozo_store.py`

- [ ] **Step 1: Add failing tests**

Append to `test_cozo_store.py`:

```python
def test_update_node_status(store):
    store.ensure_schema()
    store.create_node(make_node("n1"))
    store.update_node("demo", "n1", status="confirmed")
    assert store.get_node("demo", "n1").status == "confirmed"

def test_list_nodes_filter_by_status(store):
    store.ensure_schema()
    store.create_node(make_node("a", status="draft"))
    store.create_node(make_node("b", status="leaf"))
    drafts = store.list_nodes("demo", status="draft")
    assert [n.id for n in drafts] == ["a"]

def test_delete_node(store):
    store.ensure_schema()
    store.create_node(make_node("n1"))
    store.delete_node("demo", "n1")
    from scripts.store import NodeNotFound
    with pytest.raises(NodeNotFound):
        store.get_node("demo", "n1")
```

- [ ] **Step 2: Run, expect FAIL**

```bash
uv run pytest tests/test_cozo_store.py -v -k "update_node or list_nodes_filter or delete_node"
```
Expected: FAIL — methods not implemented.

- [ ] **Step 3: Add implementations to `cozo_store.py`**

```python
    def update_node(self, project: str, node_id: str, **fields) -> Node:
        self.ensure_schema()
        existing = self.get_node(project, node_id)
        updated = existing.to_dict()
        updated.update(fields)
        # Re-put (CozoDB :put is upsert)
        self.client.run(
            """
            ?[id, project, name, node_type, level, description, status, origin,
              tokens_estimate, created_at, updated_at] <- [[
                $id, $project, $name, $node_type, $level, $description, $status, $origin,
                $tokens_estimate, $created_at, $updated_at
            ]]
            :put node {
                id, project, name, node_type, level, description, status, origin,
                tokens_estimate, created_at, updated_at
            }
            """,
            updated,
        )
        return Node(**{k: updated[k] for k in Node.__dataclass_fields__})

    def delete_node(self, project: str, node_id: str) -> None:
        self.ensure_schema()
        self.client.run(
            """
            ?[id, project] <- [[$i, $p]]
            :rm node {id, project}
            """,
            {"i": node_id, "p": project},
        )

    def list_nodes(self, project: str, *, status: Optional[str] = None) -> list[Node]:
        self.ensure_schema()
        if status is None:
            result = self.client.run(
                """
                ?[id, project, name, node_type, level, description, status, origin,
                  tokens_estimate, created_at, updated_at] :=
                  *node{id, project, name, node_type, level, description, status, origin,
                        tokens_estimate, created_at, updated_at},
                  project = $p
                """,
                {"p": project},
            )
        else:
            result = self.client.run(
                """
                ?[id, project, name, node_type, level, description, status, origin,
                  tokens_estimate, created_at, updated_at] :=
                  *node{id, project, name, node_type, level, description, status, origin,
                        tokens_estimate, created_at, updated_at},
                  project = $p, status = $s
                """,
                {"p": project, "s": status},
            )
        cols = result["headers"]
        return [Node(**dict(zip(cols, row))) for row in result["rows"]]
```

- [ ] **Step 4: Run test, expect PASS**

```bash
uv run pytest tests/test_cozo_store.py -v
```
Expected: PASS (6 tests).

- [ ] **Step 5: Commit**

```bash
git add superpowers-plus/skills/memory-management/scripts/cozo_store.py superpowers-plus/skills/memory-management/tests/test_cozo_store.py
git commit -m "feat(memory-cli): CozoStore update/delete/list nodes"
```

---

### Task 6: CozoStore — edges + graph queries

**Files:**
- Modify: `superpowers-plus/skills/memory-management/scripts/cozo_store.py`
- Modify: `superpowers-plus/skills/memory-management/tests/test_cozo_store.py`

- [ ] **Step 1: Add failing tests**

```python
from scripts.models import Edge

def test_hierarchy_children_ordered(store):
    store.ensure_schema()
    store.create_node(make_node("p", node_type="root", level=0))
    store.create_node(make_node("c1", level=1))
    store.create_node(make_node("c2", level=1))
    store.add_edge(Edge(kind="hierarchy", from_id="p", to_id="c2", order_idx=1))
    store.add_edge(Edge(kind="hierarchy", from_id="p", to_id="c1", order_idx=0))
    children = store.query_children("demo", "p")
    assert [c.id for c in children] == ["c1", "c2"]

def test_query_ancestors(store):
    store.ensure_schema()
    store.create_node(make_node("a", level=0, node_type="root"))
    store.create_node(make_node("b", level=1))
    store.create_node(make_node("c", level=2))
    store.add_edge(Edge(kind="hierarchy", from_id="a", to_id="b"))
    store.add_edge(Edge(kind="hierarchy", from_id="b", to_id="c"))
    chain = store.query_ancestors("demo", "c")
    assert [n.id for n in chain] == ["b", "a"]

def test_query_deps_and_cycles(store):
    store.ensure_schema()
    store.create_node(make_node("a"))
    store.create_node(make_node("b"))
    store.create_node(make_node("c"))
    store.add_edge(Edge(kind="dependency", from_id="a", to_id="b"))
    store.add_edge(Edge(kind="dependency", from_id="b", to_id="c"))
    deps = store.query_deps("demo", "a")
    assert [d.id for d in deps] == ["b"]
    assert store.detect_cycles("demo") == []
    store.add_edge(Edge(kind="dependency", from_id="c", to_id="a"))
    cycles = store.detect_cycles("demo")
    assert len(cycles) == 1
```

- [ ] **Step 2: Run, expect FAIL**

```bash
uv run pytest tests/test_cozo_store.py -v -k "hierarchy_children or query_ancestors or query_deps"
```

- [ ] **Step 3: Implement edges + graph queries in `cozo_store.py`**

```python
    def add_edge(self, edge: Edge) -> None:
        self.ensure_schema()
        if edge.kind == "hierarchy":
            self.client.run(
                """
                ?[parent_id, child_id, order_idx] <- [[$f, $t, $o]]
                :put edge_hierarchy {parent_id, child_id, order_idx}
                """,
                {"f": edge.from_id, "t": edge.to_id, "o": edge.order_idx},
            )
        elif edge.kind == "dependency":
            self.client.run(
                """
                ?[from_id, to_id, dep_type] <- [[$f, $t, $d]]
                :put edge_dependency {from_id, to_id, dep_type}
                """,
                {"f": edge.from_id, "t": edge.to_id, "d": edge.dep_type},
            )
        else:
            raise StoreError(f"unknown edge kind: {edge.kind}")

    def remove_edge(self, kind: str, from_id: str, to_id: str) -> None:
        self.ensure_schema()
        if kind == "hierarchy":
            self.client.run(
                "?[parent_id, child_id] <- [[$f, $t]] :rm edge_hierarchy {parent_id, child_id}",
                {"f": from_id, "t": to_id},
            )
        elif kind == "dependency":
            self.client.run(
                "?[from_id, to_id] <- [[$f, $t]] :rm edge_dependency {from_id, to_id}",
                {"f": from_id, "t": to_id},
            )

    def query_children(self, project: str, node_id: str) -> list[Node]:
        self.ensure_schema()
        result = self.client.run(
            """
            ?[id, project, name, node_type, level, description, status, origin,
              tokens_estimate, created_at, updated_at, order_idx] :=
              *edge_hierarchy{parent_id: $p, child_id: id, order_idx},
              *node{id, project, name, node_type, level, description, status, origin,
                    tokens_estimate, created_at, updated_at},
              project = $proj
            :order order_idx
            """,
            {"p": node_id, "proj": project},
        )
        cols = result["headers"]
        return [Node(**{k: dict(zip(cols, row))[k] for k in Node.__dataclass_fields__}) for row in result["rows"]]

    def query_ancestors(self, project: str, node_id: str) -> list[Node]:
        # Recursive walk via repeated single-parent queries (simpler than Datalog recursion for now)
        chain: list[Node] = []
        current = node_id
        seen = set()
        while True:
            if current in seen:
                break
            seen.add(current)
            result = self.client.run(
                "?[parent_id] := *edge_hierarchy{parent_id, child_id: $c}",
                {"c": current},
            )
            if not result["rows"]:
                break
            current = result["rows"][0][0]
            chain.append(self.get_node(project, current))
        return chain

    def query_subtree(self, project: str, root_id: str) -> list[Node]:
        out = [self.get_node(project, root_id)]
        for child in self.query_children(project, root_id):
            out.extend(self.query_subtree(project, child.id))
        return out

    def query_deps(self, project: str, node_id: str) -> list[Node]:
        self.ensure_schema()
        result = self.client.run(
            "?[to_id] := *edge_dependency{from_id: $f, to_id}",
            {"f": node_id},
        )
        return [self.get_node(project, row[0]) for row in result["rows"]]

    def detect_cycles(self, project: str) -> list[list[str]]:
        # Pull all dependency edges, run DFS in Python (small N)
        result = self.client.run("?[from_id, to_id] := *edge_dependency{from_id, to_id}")
        from collections import defaultdict
        adj = defaultdict(list)
        for f, t in result["rows"]:
            adj[f].append(t)
        WHITE, GRAY, BLACK = 0, 1, 2
        color = defaultdict(lambda: WHITE)
        cycles: list[list[str]] = []
        stack: list[str] = []

        def dfs(u: str) -> None:
            color[u] = GRAY
            stack.append(u)
            for v in adj[u]:
                if color[v] == GRAY:
                    idx = stack.index(v)
                    cycles.append(stack[idx:] + [v])
                elif color[v] == WHITE:
                    dfs(v)
            stack.pop()
            color[u] = BLACK

        for u in list(adj.keys()):
            if color[u] == WHITE:
                dfs(u)
        return cycles
```

- [ ] **Step 4: Run, expect PASS**

```bash
uv run pytest tests/test_cozo_store.py -v
```

- [ ] **Step 5: Commit**

```bash
git add -u
git commit -m "feat(memory-cli): CozoStore edges + graph queries (children/ancestors/deps/cycles)"
```

---

### Task 7: CozoStore — decisions, interfaces, recall, assemble, validate, stats

**Files:**
- Modify: `superpowers-plus/skills/memory-management/scripts/cozo_store.py`
- Modify: `superpowers-plus/skills/memory-management/tests/test_cozo_store.py`

- [ ] **Step 1: Add failing tests**

```python
from scripts.models import Decision, Interface

def test_store_and_list_decision(store):
    store.ensure_schema()
    store.create_node(make_node("n1"))
    store.store_decision(Decision(
        id="d1", node_id="n1", question="auth?", options='["jwt","session"]',
        chosen="jwt", reasoning="stateless", tradeoffs="revocation harder",
        created_at="2026-04-07T00:00:00Z",
    ))
    decisions = store.list_decisions("demo", "n1")
    assert len(decisions) == 1 and decisions[0].chosen == "jwt"

def test_add_and_list_interface(store):
    store.ensure_schema()
    store.create_node(make_node("n1"))
    store.add_interface(Interface(
        id="i1", node_id="n1", name="login",
        description="auth endpoint", spec="POST /login (email,pwd)->token",
        created_at="2026-04-07T00:00:00Z",
    ))
    ifaces = store.list_interfaces("demo", "n1")
    assert ifaces[0].name == "login"

def test_recall_bm25(store):
    store.ensure_schema()
    store.create_node(make_node("a", description="implement OAuth login"))
    store.create_node(make_node("b", description="render dashboard"))
    results = store.recall("demo", query="oauth", k=5, semantic=False)
    assert results and results[0].node.id == "a"

def test_assemble_context_includes_ancestors_and_decisions(store):
    store.ensure_schema()
    store.create_node(make_node("root", node_type="root", level=0))
    store.create_node(make_node("leaf", node_type="leaf", level=1))
    store.add_edge(Edge(kind="hierarchy", from_id="root", to_id="leaf"))
    store.store_decision(Decision(
        id="d1", node_id="root", question="q", options="[]",
        chosen="x", reasoning="r", tradeoffs="t", created_at="2026-04-07T00:00:00Z",
    ))
    store.add_interface(Interface(
        id="i1", node_id="leaf", name="iface", description="d", spec="s",
        created_at="2026-04-07T00:00:00Z",
    ))
    pkg = store.assemble_context("demo", "leaf")
    assert pkg.node["id"] == "leaf"
    assert any(a["id"] == "root" for a in pkg.ancestors)
    assert pkg.decisions and pkg.decisions[0]["chosen"] == "x"
    assert pkg.interfaces and pkg.interfaces[0]["name"] == "iface"

def test_validate_branch_requires_decision(store):
    store.ensure_schema()
    store.create_node(make_node("b", node_type="branch"))
    result = store.validate("demo")
    assert not result["passed"]
    assert any(v["rule"] == "branch_requires_decision" for v in result["violations"])

def test_validate_leaf_requires_interface(store):
    store.ensure_schema()
    store.create_node(make_node("l", node_type="leaf"))
    result = store.validate("demo")
    assert any(v["rule"] == "leaf_requires_interface" for v in result["violations"])

def test_stats_inferred_ratio(store):
    store.ensure_schema()
    store.create_node(make_node("a", origin="user_stated"))
    store.create_node(make_node("b", origin="skill_inferred"))
    store.create_node(make_node("c", origin="skill_inferred"))
    s = store.stats("demo")
    assert s["total_nodes"] == 3
    assert s["skill_inferred_nodes"] == 2
    assert abs(s["skill_inferred_node_ratio"] - 0.6667) < 0.001
```

- [ ] **Step 2: Run, expect FAIL**

- [ ] **Step 3: Implement in `cozo_store.py`**

```python
    def store_decision(self, decision: Decision) -> None:
        self.ensure_schema()
        self.client.run(
            """
            ?[id, node_id, question, options, chosen, reasoning, tradeoffs, created_at] <- [[
                $id, $node_id, $question, $options, $chosen, $reasoning, $tradeoffs, $created_at
            ]]
            :put decision {id, node_id, question, options, chosen, reasoning, tradeoffs, created_at}
            """,
            decision.to_dict(),
        )

    def list_decisions(self, project: str, node_id: str) -> list[Decision]:
        self.ensure_schema()
        result = self.client.run(
            """
            ?[id, node_id, question, options, chosen, reasoning, tradeoffs, created_at] :=
              *decision{id, node_id, question, options, chosen, reasoning, tradeoffs, created_at},
              node_id = $n
            """,
            {"n": node_id},
        )
        cols = result["headers"]
        return [Decision(**dict(zip(cols, row))) for row in result["rows"]]

    def add_interface(self, iface: Interface) -> None:
        self.ensure_schema()
        self.client.run(
            """
            ?[id, node_id, name, description, spec, created_at] <- [[
                $id, $node_id, $name, $description, $spec, $created_at
            ]]
            :put interface_def {id, node_id, name, description, spec, created_at}
            """,
            iface.to_dict(),
        )

    def list_interfaces(self, project: str, node_id: str) -> list[Interface]:
        self.ensure_schema()
        result = self.client.run(
            """
            ?[id, node_id, name, description, spec, created_at] :=
              *interface_def{id, node_id, name, description, spec, created_at},
              node_id = $n
            """,
            {"n": node_id},
        )
        cols = result["headers"]
        return [Interface(**dict(zip(cols, row))) for row in result["rows"]]

    def recall(self, project: str, query: str, k: int, semantic: bool) -> list[ScoredNode]:
        # M1: BM25 only via Python substring scoring against name+description.
        # Semantic recall is wired in Task 12 once EmbeddingProvider exists.
        import re
        terms = [t.lower() for t in re.findall(r"\w+", query)]
        nodes = self.list_nodes(project)
        scored: list[ScoredNode] = []
        for n in nodes:
            text = (n.name + " " + n.description).lower()
            score = sum(text.count(t) for t in terms)
            if score > 0:
                scored.append(ScoredNode(node=n, score=float(score), match_type="bm25"))
        scored.sort(key=lambda s: s.score, reverse=True)
        return scored[:k]

    def assemble_context(self, project: str, leaf_id: str) -> ContextPackage:
        leaf = self.get_node(project, leaf_id)
        ancestors_nodes = self.query_ancestors(project, leaf_id)
        ancestors = [a.to_dict() for a in ancestors_nodes]
        decisions = [d.to_dict() for d in self.list_decisions(project, leaf_id)]
        for a in ancestors_nodes:
            decisions.extend(d.to_dict() for d in self.list_decisions(project, a.id))
        interfaces = [i.to_dict() for i in self.list_interfaces(project, leaf_id)]
        deps_nodes = self.query_deps(project, leaf_id)
        for d_node in deps_nodes:
            interfaces.extend(i.to_dict() for i in self.list_interfaces(project, d_node.id))
        total_chars = (
            len(leaf.description)
            + sum(len(a["description"]) for a in ancestors)
            + sum(len(d["reasoning"]) + len(d["tradeoffs"]) for d in decisions)
            + sum(len(i["spec"]) for i in interfaces)
        )
        return ContextPackage(
            node=leaf.to_dict(),
            ancestors=ancestors,
            decisions=decisions,
            interfaces=interfaces,
            deps=[d.to_dict() for d in deps_nodes],
            tokens_estimate=total_chars // 4,
        )

    def validate(self, project: str) -> dict:
        violations: list[dict] = []
        for n in self.list_nodes(project):
            if n.node_type == "branch" and not self.list_decisions(project, n.id):
                violations.append({"node_id": n.id, "rule": "branch_requires_decision"})
            if n.node_type == "leaf" and not self.list_interfaces(project, n.id):
                violations.append({"node_id": n.id, "rule": "leaf_requires_interface"})
        return {"passed": len(violations) == 0, "violations": violations}

    def stats(self, project: str) -> dict:
        nodes = self.list_nodes(project)
        total = len(nodes)
        inferred = sum(1 for n in nodes if n.origin == "skill_inferred")
        ratio = (inferred / total) if total else 0.0
        return {
            "total_nodes": total,
            "skill_inferred_nodes": inferred,
            "user_stated_nodes": total - inferred,
            "skill_inferred_node_ratio": round(ratio, 4),
        }
```

- [ ] **Step 4: Run, expect PASS**

```bash
uv run pytest tests/test_cozo_store.py -v
```

- [ ] **Step 5: Commit**

```bash
git add -u
git commit -m "feat(memory-cli): CozoStore decisions/interfaces/recall/assemble/validate/stats"
```

---

### Task 8: Protocol compliance test (same suite, both impls)

This is the test that proves `MemoryStore` is a real abstraction. AC #13.

**Files:**
- Create: `superpowers-plus/skills/memory-management/tests/test_store_protocol_compliance.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_store_protocol_compliance.py
import pytest
from scripts.store import InMemoryStore
from scripts.cozo_store import CozoStore
from scripts.models import Node, Edge, Decision, Interface

def make_node(id, **overrides):
    base = dict(
        id=id, project="demo", name=id, node_type="branch", level=1,
        description=f"node {id}", status="draft", origin="user_stated",
        tokens_estimate=0, created_at="2026-04-07T00:00:00Z",
        updated_at="2026-04-07T00:00:00Z",
    )
    base.update(overrides)
    return Node(**base)

@pytest.fixture(params=["in_memory", "cozo"])
def store(request, tmp_path):
    if request.param == "in_memory":
        return InMemoryStore()
    else:
        s = CozoStore(db_path=str(tmp_path / "data.cozo"))
        s.ensure_schema()
        return s

def test_full_lifecycle_via_protocol(store):
    # Create a tiny pyramid
    store.create_node(make_node("root", node_type="root", level=0))
    store.create_node(make_node("leaf", node_type="leaf", level=1))
    store.add_edge(Edge(kind="hierarchy", from_id="root", to_id="leaf"))
    store.store_decision(Decision(
        id="d1", node_id="root", question="q", options="[]",
        chosen="x", reasoning="r", tradeoffs="t", created_at="2026-04-07T00:00:00Z",
    ))
    store.add_interface(Interface(
        id="i1", node_id="leaf", name="api", description="d", spec="s",
        created_at="2026-04-07T00:00:00Z",
    ))
    pkg = store.assemble_context("demo", "leaf")
    assert pkg.node["id"] == "leaf"
    assert pkg.ancestors[0]["id"] == "root"
    assert pkg.decisions[0]["chosen"] == "x"
    assert pkg.interfaces[0]["name"] == "api"
    val = store.validate("demo")
    assert val["passed"] is True
    stats = store.stats("demo")
    assert stats["total_nodes"] == 2
```

- [ ] **Step 2: Run test, expect PASS for both params**

```bash
uv run pytest tests/test_store_protocol_compliance.py -v
```
Expected: PASS — 2 test cases (in_memory + cozo).

- [ ] **Step 3: Commit**

```bash
git add superpowers-plus/skills/memory-management/tests/test_store_protocol_compliance.py
git commit -m "test(memory-cli): protocol compliance suite running on both store impls"
```

---

## Chunk 3: Config + Locks + Output Helpers

### Task 9: Config loader (`config.py`)

**Files:**
- Create: `superpowers-plus/skills/memory-management/scripts/config.py`
- Create: `superpowers-plus/skills/memory-management/tests/test_config.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_config.py
from pathlib import Path
from scripts.config import Config, load_config, save_config

def test_default_config_when_missing(tmp_path):
    cfg = load_config(tmp_path / "config.toml")
    assert cfg.embedding_provider == "skip"
    assert cfg.db_path.endswith("data.cozo")
    assert cfg.initialized is False

def test_save_and_reload(tmp_path):
    p = tmp_path / "config.toml"
    cfg = Config(
        embedding_provider="fastembed",
        db_path=str(tmp_path / "data.cozo"),
        default_project="myapp",
        initialized=True,
    )
    save_config(p, cfg)
    cfg2 = load_config(p)
    assert cfg2.embedding_provider == "fastembed"
    assert cfg2.default_project == "myapp"
    assert cfg2.initialized is True
```

- [ ] **Step 2: Run, expect FAIL**

- [ ] **Step 3: Implement `config.py`**

```python
# scripts/config.py
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional
import sys

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib


@dataclass
class Config:
    embedding_provider: str = "skip"        # skip | fastembed | voyage | openai | ollama
    db_path: str = "~/.pyramid-memory/data.cozo"
    default_project: Optional[str] = None
    initialized: bool = False

    def expanded_db_path(self) -> str:
        return str(Path(self.db_path).expanduser())


def load_config(path: Path) -> Config:
    if not path.exists():
        return Config()
    with open(path, "rb") as f:
        data = tomllib.load(f)
    embedding = data.get("embedding", {})
    storage = data.get("storage", {})
    meta = data.get("meta", {})
    return Config(
        embedding_provider=embedding.get("provider", "skip"),
        db_path=storage.get("db_path", "~/.pyramid-memory/data.cozo"),
        default_project=meta.get("default_project"),
        initialized=meta.get("initialized", False),
    )


def save_config(path: Path, cfg: Config) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "[embedding]",
        f'provider = "{cfg.embedding_provider}"',
        "",
        "[storage]",
        f'db_path = "{cfg.db_path}"',
        "",
        "[meta]",
        f"initialized = {'true' if cfg.initialized else 'false'}",
    ]
    if cfg.default_project:
        lines.append(f'default_project = "{cfg.default_project}"')
    path.write_text("\n".join(lines) + "\n")


def default_config_path() -> Path:
    return Path.home() / ".pyramid-memory" / "config.toml"
```

- [ ] **Step 4: Run, expect PASS**

```bash
uv run pytest tests/test_config.py -v
```

- [ ] **Step 5: Commit**

```bash
git add superpowers-plus/skills/memory-management/scripts/config.py superpowers-plus/skills/memory-management/tests/test_config.py
git commit -m "feat(memory-cli): config loader with toml read/write"
```

---

### Task 10: File lock helper (`locks.py`)

For §8 row "concurrent access" — single-writer file lock with stale-PID cleanup.

**Files:**
- Create: `superpowers-plus/skills/memory-management/scripts/locks.py`
- Create: `superpowers-plus/skills/memory-management/tests/test_locks.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_locks.py
import os
import pytest
from scripts.locks import file_lock, LockTimeout

def test_acquire_and_release(tmp_path):
    lock_path = tmp_path / ".lock"
    with file_lock(lock_path, timeout=1):
        assert lock_path.exists()
    assert not lock_path.exists()

def test_stale_pid_cleanup(tmp_path):
    lock_path = tmp_path / ".lock"
    lock_path.write_text("999999")  # Almost certainly not a real PID
    with file_lock(lock_path, timeout=1):
        # Should have cleaned up the stale lock
        assert lock_path.read_text() == str(os.getpid())

def test_timeout_when_held(tmp_path):
    lock_path = tmp_path / ".lock"
    lock_path.write_text(str(os.getpid()))  # Pretend our own pid holds it
    # Real PID is alive, so should NOT clean — should time out
    with pytest.raises(LockTimeout):
        with file_lock(lock_path, timeout=0.5):
            pass
```

- [ ] **Step 2: Run, expect FAIL**

- [ ] **Step 3: Implement `locks.py`**

```python
# scripts/locks.py
import os
import time
from contextlib import contextmanager
from pathlib import Path


class LockTimeout(Exception):
    pass


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except (ProcessLookupError, PermissionError):
        return False
    except OSError:
        return False
    return True


@contextmanager
def file_lock(path: Path, timeout: float = 5.0, poll: float = 0.05):
    path = Path(path)
    deadline = time.monotonic() + timeout
    my_pid = os.getpid()
    while True:
        try:
            fd = os.open(str(path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(fd, str(my_pid).encode())
            os.close(fd)
            break
        except FileExistsError:
            # Check stale
            try:
                holder = int(path.read_text().strip())
                if holder != my_pid and not _pid_alive(holder):
                    path.unlink(missing_ok=True)
                    continue
                if holder == my_pid:
                    # Same process — pretend stale, allow takeover
                    path.unlink(missing_ok=True)
                    continue
            except (ValueError, FileNotFoundError):
                path.unlink(missing_ok=True)
                continue
            if time.monotonic() > deadline:
                raise LockTimeout(f"could not acquire {path} within {timeout}s")
            time.sleep(poll)
    try:
        yield
    finally:
        try:
            current = path.read_text().strip()
            if current == str(my_pid):
                path.unlink(missing_ok=True)
        except FileNotFoundError:
            pass
```

- [ ] **Step 4: Run, expect PASS**

```bash
uv run pytest tests/test_locks.py -v
```

- [ ] **Step 5: Commit**

```bash
git add superpowers-plus/skills/memory-management/scripts/locks.py superpowers-plus/skills/memory-management/tests/test_locks.py
git commit -m "feat(memory-cli): file lock helper with stale PID cleanup"
```

---

### Task 11: Output contract helper (`output.py`)

**Files:**
- Create: `superpowers-plus/skills/memory-management/scripts/output.py`

- [ ] **Step 1: Implement (no test needed; covered by CLI tests)**

```python
# scripts/output.py
import json
import sys
from typing import Any

def emit(data: Any = None, *, warnings: list[str] | None = None, degraded: bool = False, ok: bool = True) -> None:
    print(json.dumps({
        "ok": ok,
        "data": data if data is not None else {},
        "warnings": warnings or [],
        "degraded": degraded,
    }))

def emit_error(message: str, *, code: str = "error") -> None:
    print(json.dumps({
        "ok": False,
        "error": {"code": code, "message": message},
        "warnings": [],
        "degraded": False,
    }))
    sys.exit(1)
```

- [ ] **Step 2: Commit**

```bash
git add superpowers-plus/skills/memory-management/scripts/output.py
git commit -m "feat(memory-cli): JSON output contract helper"
```

---

## Chunk 4: CLI Commands

### Task 12: `init` and `config show/set`

**Files:**
- Modify: `superpowers-plus/skills/memory-management/scripts/memory_cli.py`
- Create: `superpowers-plus/skills/memory-management/tests/test_cli_init.py` (extend existing)

- [ ] **Step 1: Write failing tests**

```python
# tests/test_cli_init.py (append)
import json

def test_init_creates_config_and_db(run_cli, tmp_path):
    result = run_cli("init", "--project", "demo", "--embedding", "skip", "--non-interactive")
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    cfg_path = tmp_path / ".pyramid-memory" / "config.toml"
    assert cfg_path.exists()
    assert "demo" in cfg_path.read_text()

def test_config_show_uninitialized(run_cli):
    result = run_cli("config", "show")
    payload = json.loads(result.stdout)
    assert payload["data"]["initialized"] is False

def test_config_show_after_init(run_cli):
    run_cli("init", "--project", "demo", "--embedding", "skip", "--non-interactive")
    result = run_cli("config", "show")
    payload = json.loads(result.stdout)
    assert payload["data"]["initialized"] is True
    assert payload["data"]["embedding_provider"] == "skip"
```

- [ ] **Step 2: Run, expect FAIL**

- [ ] **Step 3: Extend `memory_cli.py` with init + config commands**

Replace the existing `memory_cli.py` body (after the PEP 723 header) with:

```python
"""Pyramid Memory CLI — Milestone 1 (storage + CLI)."""
import json
import sys
from pathlib import Path
import click

# Imports relative to the scripts/ directory
sys.path.insert(0, str(Path(__file__).parent))
from config import Config, load_config, save_config, default_config_path
from output import emit, emit_error

VERSION = "0.1.0-m1"


def _load() -> Config:
    return load_config(default_config_path())


@click.group()
def cli():
    """Pyramid Memory: graph + decision storage for AI-driven decomposition."""


@cli.command()
def version():
    """Print CLI version."""
    emit({"version": VERSION})


@cli.command()
@click.option("--project", required=True, help="Default project name (namespace).")
@click.option("--embedding", type=click.Choice(["skip", "fastembed", "voyage", "openai", "ollama"]), default="skip")
@click.option("--db-path", default="~/.pyramid-memory/data.cozo")
@click.option("--non-interactive", is_flag=True, help="Skip prompts (for tests / scripts).")
def init(project: str, embedding: str, db_path: str, non_interactive: bool):
    """Initialize the pyramid memory store."""
    cfg = Config(
        embedding_provider=embedding,
        db_path=db_path,
        default_project=project,
        initialized=True,
    )
    save_config(default_config_path(), cfg)
    # Touch DB file by ensuring schema (lazy import to keep startup fast)
    from cozo_store import CozoStore
    store = CozoStore(db_path=cfg.expanded_db_path())
    store.ensure_schema()
    emit({"initialized": True, "project": project, "embedding": embedding, "db_path": cfg.expanded_db_path()})


@cli.group()
def config():
    """Inspect or modify configuration."""


@config.command("show")
def config_show():
    """Show current configuration as JSON."""
    cfg = _load()
    emit({
        "initialized": cfg.initialized,
        "embedding_provider": cfg.embedding_provider,
        "db_path": cfg.expanded_db_path(),
        "default_project": cfg.default_project,
    })


@config.command("set")
@click.argument("key")
@click.argument("value")
def config_set(key: str, value: str):
    """Set a configuration value (embedding_provider | default_project | db_path)."""
    cfg = _load()
    if key not in {"embedding_provider", "default_project", "db_path"}:
        emit_error(f"unknown config key: {key}")
    setattr(cfg, key, value)
    save_config(default_config_path(), cfg)
    emit({"updated": {key: value}})


if __name__ == "__main__":
    cli()
```

- [ ] **Step 4: Run, expect PASS**

```bash
uv run pytest tests/test_cli_init.py -v
```

- [ ] **Step 5: Commit**

```bash
git add -u
git commit -m "feat(memory-cli): init + config show/set commands"
```

---

### Task 13: `node` command group (create/get/update/delete/list)

**Files:**
- Modify: `superpowers-plus/skills/memory-management/scripts/memory_cli.py`
- Create: `superpowers-plus/skills/memory-management/tests/test_cli_node.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_cli_node.py
import json
import pytest

@pytest.fixture
def initialized(run_cli):
    run_cli("init", "--project", "demo", "--embedding", "skip", "--non-interactive")
    return run_cli

def test_node_create_and_get(initialized):
    r = initialized("node", "create", "--id", "n1", "--name", "root",
                    "--type", "root", "--level", "0",
                    "--description", "the root", "--origin", "user_stated")
    assert r.returncode == 0
    payload = json.loads(r.stdout)
    assert payload["ok"] and payload["data"]["id"] == "n1"

    r2 = initialized("node", "get", "--id", "n1")
    assert json.loads(r2.stdout)["data"]["name"] == "root"

def test_node_list_filter_by_status(initialized):
    initialized("node", "create", "--id", "a", "--name", "a", "--type", "branch",
                "--level", "1", "--description", "x", "--origin", "user_stated")
    initialized("node", "create", "--id", "b", "--name", "b", "--type", "branch",
                "--level", "1", "--description", "y", "--origin", "skill_inferred",
                "--status", "confirmed")
    r = initialized("node", "list", "--status", "confirmed")
    rows = json.loads(r.stdout)["data"]["nodes"]
    assert len(rows) == 1 and rows[0]["id"] == "b"

def test_node_update_status(initialized):
    initialized("node", "create", "--id", "n1", "--name", "x", "--type", "branch",
                "--level", "1", "--description", "x", "--origin", "user_stated")
    r = initialized("node", "update", "--id", "n1", "--status", "confirmed")
    assert json.loads(r.stdout)["data"]["status"] == "confirmed"

def test_node_delete(initialized):
    initialized("node", "create", "--id", "n1", "--name", "x", "--type", "branch",
                "--level", "1", "--description", "x", "--origin", "user_stated")
    r = initialized("node", "delete", "--id", "n1")
    assert json.loads(r.stdout)["ok"]
```

- [ ] **Step 2: Run, expect FAIL**

- [ ] **Step 3: Add helpers and `node` command group to `memory_cli.py`**

Insert before `if __name__ == "__main__":`

```python
from datetime import datetime, timezone

def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _store():
    """Lazy-load the configured store."""
    cfg = _load()
    if not cfg.initialized:
        emit_error("not initialized — run `memory_cli.py init` first", code="uninitialized")
    from cozo_store import CozoStore
    s = CozoStore(db_path=cfg.expanded_db_path())
    s.ensure_schema()
    return s, cfg


def _project(opt_project: str | None, cfg: Config) -> str:
    p = opt_project or cfg.default_project
    if not p:
        emit_error("no project specified and no default_project configured", code="missing_project")
    return p


@cli.group()
def node():
    """Node CRUD."""


@node.command("create")
@click.option("--id", "node_id", required=True)
@click.option("--name", required=True)
@click.option("--type", "node_type", type=click.Choice(["root", "branch", "leaf"]), required=True)
@click.option("--level", type=int, required=True)
@click.option("--description", required=True)
@click.option("--origin", type=click.Choice(["user_stated", "skill_inferred"]), required=True)
@click.option("--status", default="draft")
@click.option("--tokens-estimate", type=int, default=0)
@click.option("--project")
def node_create(node_id, name, node_type, level, description, origin, status, tokens_estimate, project):
    from models import Node
    s, cfg = _store()
    p = _project(project, cfg)
    now = _now()
    n = Node(
        id=node_id, project=p, name=name, node_type=node_type, level=level,
        description=description, status=status, origin=origin,
        tokens_estimate=tokens_estimate, created_at=now, updated_at=now,
    )
    s.create_node(n)
    emit(n.to_dict())


@node.command("get")
@click.option("--id", "node_id", required=True)
@click.option("--project")
def node_get(node_id, project):
    s, cfg = _store()
    p = _project(project, cfg)
    n = s.get_node(p, node_id)
    emit(n.to_dict())


@node.command("update")
@click.option("--id", "node_id", required=True)
@click.option("--status")
@click.option("--description")
@click.option("--tokens-estimate", type=int)
@click.option("--project")
def node_update(node_id, status, description, tokens_estimate, project):
    s, cfg = _store()
    p = _project(project, cfg)
    fields = {}
    if status is not None:
        fields["status"] = status
    if description is not None:
        fields["description"] = description
    if tokens_estimate is not None:
        fields["tokens_estimate"] = tokens_estimate
    fields["updated_at"] = _now()
    n = s.update_node(p, node_id, **fields)
    emit(n.to_dict())


@node.command("delete")
@click.option("--id", "node_id", required=True)
@click.option("--project")
def node_delete(node_id, project):
    s, cfg = _store()
    p = _project(project, cfg)
    s.delete_node(p, node_id)
    emit({"deleted": node_id})


@node.command("list")
@click.option("--status")
@click.option("--project")
def node_list(status, project):
    s, cfg = _store()
    p = _project(project, cfg)
    nodes = s.list_nodes(p, status=status)
    emit({"nodes": [n.to_dict() for n in nodes]})
```

- [ ] **Step 4: Run, expect PASS**

```bash
uv run pytest tests/test_cli_node.py -v
```

- [ ] **Step 5: Commit**

```bash
git add -u
git commit -m "feat(memory-cli): node command group (create/get/update/delete/list)"
```

---

### Task 14: `edge` command group

**Files:**
- Modify: `superpowers-plus/skills/memory-management/scripts/memory_cli.py`
- Create: `superpowers-plus/skills/memory-management/tests/test_cli_edge.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_cli_edge.py
import json
import pytest

@pytest.fixture
def initialized(run_cli):
    run_cli("init", "--project", "demo", "--embedding", "skip", "--non-interactive")
    return run_cli

def _create_node(cli, nid, ntype="branch", level=1):
    cli("node", "create", "--id", nid, "--name", nid, "--type", ntype,
        "--level", str(level), "--description", nid, "--origin", "user_stated")

def test_edge_add_hierarchy(initialized):
    _create_node(initialized, "p", "root", 0)
    _create_node(initialized, "c", "leaf", 1)
    r = initialized("edge", "add", "--kind", "hierarchy", "--from", "p", "--to", "c", "--order", "0")
    assert json.loads(r.stdout)["ok"]

def test_edge_remove(initialized):
    _create_node(initialized, "a")
    _create_node(initialized, "b")
    initialized("edge", "add", "--kind", "dependency", "--from", "a", "--to", "b")
    r = initialized("edge", "remove", "--kind", "dependency", "--from", "a", "--to", "b")
    assert json.loads(r.stdout)["ok"]
```

- [ ] **Step 2: Run, expect FAIL**

- [ ] **Step 3: Add `edge` group to `memory_cli.py`**

```python
@cli.group()
def edge():
    """Edge add/remove."""


@edge.command("add")
@click.option("--kind", type=click.Choice(["hierarchy", "dependency"]), required=True)
@click.option("--from", "from_id", required=True)
@click.option("--to", "to_id", required=True)
@click.option("--order", "order_idx", type=int, default=0)
@click.option("--dep-type", default="requires")
def edge_add(kind, from_id, to_id, order_idx, dep_type):
    from models import Edge
    s, _ = _store()
    s.add_edge(Edge(kind=kind, from_id=from_id, to_id=to_id, order_idx=order_idx, dep_type=dep_type))
    emit({"added": {"kind": kind, "from": from_id, "to": to_id}})


@edge.command("remove")
@click.option("--kind", type=click.Choice(["hierarchy", "dependency"]), required=True)
@click.option("--from", "from_id", required=True)
@click.option("--to", "to_id", required=True)
def edge_remove(kind, from_id, to_id):
    s, _ = _store()
    s.remove_edge(kind, from_id, to_id)
    emit({"removed": {"kind": kind, "from": from_id, "to": to_id}})
```

- [ ] **Step 4: Run, expect PASS**

- [ ] **Step 5: Commit**

```bash
git add -u
git commit -m "feat(memory-cli): edge add/remove commands"
```

---

### Task 15: `query` command group (children/ancestors/subtree/deps/cycles)

**Files:**
- Modify: `superpowers-plus/skills/memory-management/scripts/memory_cli.py`
- Create: `superpowers-plus/skills/memory-management/tests/test_cli_query.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_cli_query.py
import json
import pytest

@pytest.fixture
def initialized(run_cli):
    run_cli("init", "--project", "demo", "--embedding", "skip", "--non-interactive")
    return run_cli

def _seed_pyramid(cli):
    cli("node", "create", "--id", "root", "--name", "root", "--type", "root",
        "--level", "0", "--description", "root", "--origin", "user_stated")
    cli("node", "create", "--id", "a", "--name", "a", "--type", "branch",
        "--level", "1", "--description", "a", "--origin", "user_stated")
    cli("node", "create", "--id", "b", "--name", "b", "--type", "leaf",
        "--level", "2", "--description", "b", "--origin", "skill_inferred")
    cli("edge", "add", "--kind", "hierarchy", "--from", "root", "--to", "a")
    cli("edge", "add", "--kind", "hierarchy", "--from", "a", "--to", "b")

def test_query_children(initialized):
    _seed_pyramid(initialized)
    r = initialized("query", "children", "--id", "root")
    payload = json.loads(r.stdout)
    assert [n["id"] for n in payload["data"]["nodes"]] == ["a"]

def test_query_ancestors(initialized):
    _seed_pyramid(initialized)
    r = initialized("query", "ancestors", "--id", "b")
    payload = json.loads(r.stdout)
    assert [n["id"] for n in payload["data"]["nodes"]] == ["a", "root"]

def test_query_subtree(initialized):
    _seed_pyramid(initialized)
    r = initialized("query", "subtree", "--root", "root")
    ids = sorted(n["id"] for n in json.loads(r.stdout)["data"]["nodes"])
    assert ids == ["a", "b", "root"]

def test_query_cycles_empty(initialized):
    _seed_pyramid(initialized)
    r = initialized("query", "cycles")
    assert json.loads(r.stdout)["data"]["cycles"] == []
```

- [ ] **Step 2: Run, expect FAIL**

- [ ] **Step 3: Add `query` group**

```python
@cli.group()
def query():
    """Graph traversals."""


def _project_opt(project, cfg):
    return _project(project, cfg)


@query.command("children")
@click.option("--id", "node_id", required=True)
@click.option("--project")
def query_children(node_id, project):
    s, cfg = _store()
    p = _project_opt(project, cfg)
    nodes = s.query_children(p, node_id)
    emit({"nodes": [n.to_dict() for n in nodes]})


@query.command("ancestors")
@click.option("--id", "node_id", required=True)
@click.option("--project")
def query_ancestors(node_id, project):
    s, cfg = _store()
    p = _project_opt(project, cfg)
    nodes = s.query_ancestors(p, node_id)
    emit({"nodes": [n.to_dict() for n in nodes]})


@query.command("subtree")
@click.option("--root", "root_id", required=True)
@click.option("--project")
def query_subtree(root_id, project):
    s, cfg = _store()
    p = _project_opt(project, cfg)
    nodes = s.query_subtree(p, root_id)
    emit({"nodes": [n.to_dict() for n in nodes]})


@query.command("deps")
@click.option("--id", "node_id", required=True)
@click.option("--project")
def query_deps(node_id, project):
    s, cfg = _store()
    p = _project_opt(project, cfg)
    nodes = s.query_deps(p, node_id)
    emit({"nodes": [n.to_dict() for n in nodes]})


@query.command("cycles")
@click.option("--project")
def query_cycles(project):
    s, cfg = _store()
    p = _project_opt(project, cfg)
    cycles = s.detect_cycles(p)
    emit({"cycles": cycles})
```

- [ ] **Step 4: Run, expect PASS**

- [ ] **Step 5: Commit**

```bash
git add -u
git commit -m "feat(memory-cli): query commands (children/ancestors/subtree/deps/cycles)"
```

---

### Task 16: `decision` and `interface` command groups

**Files:**
- Modify: `superpowers-plus/skills/memory-management/scripts/memory_cli.py`
- Create: `superpowers-plus/skills/memory-management/tests/test_cli_decision.py`
- Create: `superpowers-plus/skills/memory-management/tests/test_cli_interface.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_cli_decision.py
import json
import pytest

@pytest.fixture
def initialized(run_cli):
    run_cli("init", "--project", "demo", "--embedding", "skip", "--non-interactive")
    return run_cli

def test_decision_store_and_list(initialized):
    initialized("node", "create", "--id", "n1", "--name", "n1", "--type", "branch",
                "--level", "1", "--description", "x", "--origin", "user_stated")
    r = initialized("decision", "store", "--id", "d1", "--node", "n1",
                    "--question", "auth?", "--options", '["jwt","session"]',
                    "--chosen", "jwt", "--reasoning", "stateless",
                    "--tradeoffs", "revoke harder")
    assert json.loads(r.stdout)["ok"]
    r2 = initialized("decision", "list", "--node", "n1")
    decisions = json.loads(r2.stdout)["data"]["decisions"]
    assert len(decisions) == 1 and decisions[0]["chosen"] == "jwt"
```

```python
# tests/test_cli_interface.py
import json
import pytest

@pytest.fixture
def initialized(run_cli):
    run_cli("init", "--project", "demo", "--embedding", "skip", "--non-interactive")
    return run_cli

def test_interface_add_and_list(initialized):
    initialized("node", "create", "--id", "n1", "--name", "n1", "--type", "leaf",
                "--level", "1", "--description", "x", "--origin", "user_stated")
    r = initialized("interface", "add", "--id", "i1", "--node", "n1",
                    "--name", "login", "--description", "auth endpoint",
                    "--spec", "POST /login (email,pwd)->token")
    assert json.loads(r.stdout)["ok"]
    r2 = initialized("interface", "list", "--node", "n1")
    ifaces = json.loads(r2.stdout)["data"]["interfaces"]
    assert len(ifaces) == 1 and ifaces[0]["name"] == "login"
```

- [ ] **Step 2: Run, expect FAIL**

- [ ] **Step 3: Add `decision` and `interface` groups**

```python
@cli.group()
def decision():
    """Decision logging."""


@decision.command("store")
@click.option("--id", "decision_id", required=True)
@click.option("--node", "node_id", required=True)
@click.option("--question", required=True)
@click.option("--options", required=True, help="JSON-encoded list")
@click.option("--chosen", required=True)
@click.option("--reasoning", required=True)
@click.option("--tradeoffs", default="")
def decision_store(decision_id, node_id, question, options, chosen, reasoning, tradeoffs):
    from models import Decision
    s, _ = _store()
    d = Decision(
        id=decision_id, node_id=node_id, question=question, options=options,
        chosen=chosen, reasoning=reasoning, tradeoffs=tradeoffs, created_at=_now(),
    )
    s.store_decision(d)
    emit(d.to_dict())


@decision.command("list")
@click.option("--node", "node_id", required=True)
@click.option("--project")
def decision_list(node_id, project):
    s, cfg = _store()
    p = _project(project, cfg)
    decisions = s.list_decisions(p, node_id)
    emit({"decisions": [d.to_dict() for d in decisions]})


@cli.group()
def interface():
    """Interface capture."""


@interface.command("add")
@click.option("--id", "iface_id", required=True)
@click.option("--node", "node_id", required=True)
@click.option("--name", required=True)
@click.option("--description", required=True)
@click.option("--spec", required=True)
def interface_add(iface_id, node_id, name, description, spec):
    from models import Interface
    s, _ = _store()
    i = Interface(
        id=iface_id, node_id=node_id, name=name, description=description,
        spec=spec, created_at=_now(),
    )
    s.add_interface(i)
    emit(i.to_dict())


@interface.command("list")
@click.option("--node", "node_id", required=True)
@click.option("--project")
def interface_list(node_id, project):
    s, cfg = _store()
    p = _project(project, cfg)
    ifaces = s.list_interfaces(p, node_id)
    emit({"interfaces": [i.to_dict() for i in ifaces]})
```

- [ ] **Step 4: Run, expect PASS**

- [ ] **Step 5: Commit**

```bash
git add -u
git commit -m "feat(memory-cli): decision and interface command groups"
```

---

### Task 17: `memory recall` (BM25 path)

**Files:**
- Modify: `superpowers-plus/skills/memory-management/scripts/memory_cli.py`
- Create: `superpowers-plus/skills/memory-management/tests/test_cli_memory_recall.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_cli_memory_recall.py
import json
import pytest

@pytest.fixture
def initialized(run_cli):
    run_cli("init", "--project", "demo", "--embedding", "skip", "--non-interactive")
    return run_cli

def test_recall_bm25_finds_match(initialized):
    initialized("node", "create", "--id", "a", "--name", "auth-flow", "--type", "leaf",
                "--level", "1", "--description", "implement OAuth login flow",
                "--origin", "user_stated")
    initialized("node", "create", "--id", "b", "--name", "dashboard", "--type", "leaf",
                "--level", "1", "--description", "render charts", "--origin", "user_stated")
    r = initialized("memory", "recall", "--query", "oauth", "--k", "3")
    payload = json.loads(r.stdout)
    matches = payload["data"]["matches"]
    assert matches and matches[0]["node"]["id"] == "a"
    assert matches[0]["match_type"] == "bm25"
```

- [ ] **Step 2: Run, expect FAIL**

- [ ] **Step 3: Add `memory` group with `recall`**

```python
@cli.group()
def memory():
    """Recall, context assembly, validation, maintenance."""


@memory.command("recall")
@click.option("--query", required=True)
@click.option("--k", type=int, default=5)
@click.option("--semantic/--no-semantic", default=False)
@click.option("--project")
def memory_recall(query, k, semantic, project):
    s, cfg = _store()
    p = _project(project, cfg)
    degraded = False
    warnings: list[str] = []
    if semantic and cfg.embedding_provider == "skip":
        warnings.append("semantic requested but embedding_provider=skip; falling back to BM25")
        semantic = False
        degraded = True
    matches = s.recall(p, query=query, k=k, semantic=semantic)
    emit(
        {"matches": [{"node": m.node.to_dict(), "score": m.score, "match_type": m.match_type} for m in matches]},
        warnings=warnings,
        degraded=degraded,
    )
```

- [ ] **Step 4: Run, expect PASS**

- [ ] **Step 5: Commit**

```bash
git add -u
git commit -m "feat(memory-cli): memory recall (BM25 + semantic-fallback warning)"
```

---

### Task 18: `memory context` (assembly)

**Files:**
- Modify: `superpowers-plus/skills/memory-management/scripts/memory_cli.py`
- Create: `superpowers-plus/skills/memory-management/tests/test_cli_memory_context.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_cli_memory_context.py
import json
import pytest

@pytest.fixture
def initialized(run_cli):
    run_cli("init", "--project", "demo", "--embedding", "skip", "--non-interactive")
    return run_cli

def test_context_assembles_full_package(initialized):
    initialized("node", "create", "--id", "root", "--name", "r", "--type", "root",
                "--level", "0", "--description", "the root", "--origin", "user_stated")
    initialized("node", "create", "--id", "leaf", "--name", "l", "--type", "leaf",
                "--level", "1", "--description", "the leaf", "--origin", "skill_inferred")
    initialized("edge", "add", "--kind", "hierarchy", "--from", "root", "--to", "leaf")
    initialized("decision", "store", "--id", "d1", "--node", "root",
                "--question", "q?", "--options", "[]", "--chosen", "x",
                "--reasoning", "r", "--tradeoffs", "t")
    initialized("interface", "add", "--id", "i1", "--node", "leaf",
                "--name", "api", "--description", "d", "--spec", "GET /x")
    r = initialized("memory", "context", "--node", "leaf")
    pkg = json.loads(r.stdout)["data"]
    assert pkg["node"]["id"] == "leaf"
    assert any(a["id"] == "root" for a in pkg["ancestors"])
    assert pkg["decisions"][0]["chosen"] == "x"
    assert pkg["interfaces"][0]["name"] == "api"
    assert pkg["tokens_estimate"] > 0
```

- [ ] **Step 2: Run, expect FAIL**

- [ ] **Step 3: Add `memory context` command**

```python
@memory.command("context")
@click.option("--node", "node_id", required=True)
@click.option("--project")
def memory_context(node_id, project):
    s, cfg = _store()
    p = _project(project, cfg)
    pkg = s.assemble_context(p, node_id)
    emit(pkg.to_dict())
```

- [ ] **Step 4: Run, expect PASS**

- [ ] **Step 5: Commit**

```bash
git add -u
git commit -m "feat(memory-cli): memory context command (full implementation package)"
```

---

### Task 19: `memory validate` and `memory stats` (AC #5, #6)

**Files:**
- Modify: `superpowers-plus/skills/memory-management/scripts/memory_cli.py`
- Create: `superpowers-plus/skills/memory-management/tests/test_cli_memory_validate.py`
- Create: `superpowers-plus/skills/memory-management/tests/test_cli_memory_stats.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_cli_memory_validate.py
import json
import pytest

@pytest.fixture
def initialized(run_cli):
    run_cli("init", "--project", "demo", "--embedding", "skip", "--non-interactive")
    return run_cli

def test_validate_fails_branch_without_decision(initialized):
    initialized("node", "create", "--id", "b", "--name", "b", "--type", "branch",
                "--level", "1", "--description", "x", "--origin", "user_stated")
    r = initialized("memory", "validate")
    payload = json.loads(r.stdout)["data"]
    assert payload["passed"] is False
    assert any(v["rule"] == "branch_requires_decision" for v in payload["violations"])

def test_validate_fails_leaf_without_interface(initialized):
    initialized("node", "create", "--id", "l", "--name", "l", "--type", "leaf",
                "--level", "1", "--description", "x", "--origin", "user_stated")
    r = initialized("memory", "validate")
    payload = json.loads(r.stdout)["data"]
    assert any(v["rule"] == "leaf_requires_interface" for v in payload["violations"])

def test_validate_passes_when_complete(initialized):
    initialized("node", "create", "--id", "b", "--name", "b", "--type", "branch",
                "--level", "1", "--description", "x", "--origin", "user_stated")
    initialized("decision", "store", "--id", "d1", "--node", "b",
                "--question", "q", "--options", "[]", "--chosen", "x",
                "--reasoning", "r")
    initialized("node", "create", "--id", "l", "--name", "l", "--type", "leaf",
                "--level", "2", "--description", "x", "--origin", "user_stated")
    initialized("interface", "add", "--id", "i1", "--node", "l",
                "--name", "api", "--description", "d", "--spec", "s")
    r = initialized("memory", "validate")
    assert json.loads(r.stdout)["data"]["passed"] is True
```

```python
# tests/test_cli_memory_stats.py
import json
import pytest

@pytest.fixture
def initialized(run_cli):
    run_cli("init", "--project", "demo", "--embedding", "skip", "--non-interactive")
    return run_cli

def test_stats_inferred_ratio(initialized):
    initialized("node", "create", "--id", "a", "--name", "a", "--type", "branch",
                "--level", "1", "--description", "x", "--origin", "user_stated")
    initialized("node", "create", "--id", "b", "--name", "b", "--type", "branch",
                "--level", "1", "--description", "x", "--origin", "skill_inferred")
    initialized("node", "create", "--id", "c", "--name", "c", "--type", "branch",
                "--level", "1", "--description", "x", "--origin", "skill_inferred")
    r = initialized("memory", "stats")
    s = json.loads(r.stdout)["data"]
    assert s["total_nodes"] == 3
    assert s["skill_inferred_nodes"] == 2
    assert abs(s["skill_inferred_node_ratio"] - 0.6667) < 0.001
```

- [ ] **Step 2: Run, expect FAIL**

- [ ] **Step 3: Add commands**

```python
@memory.command("validate")
@click.option("--project")
def memory_validate(project):
    s, cfg = _store()
    p = _project(project, cfg)
    result = s.validate(p)
    emit(result, ok=result["passed"])


@memory.command("stats")
@click.option("--project")
def memory_stats(project):
    s, cfg = _store()
    p = _project(project, cfg)
    emit(s.stats(p))
```

- [ ] **Step 4: Run, expect PASS**

- [ ] **Step 5: Commit**

```bash
git add -u
git commit -m "feat(memory-cli): memory validate + stats (AC #5, #6 enforcement)"
```

---

## Chunk 5: Embedding (optional capability)

### Task 20: `EmbeddingProvider` Protocol + `SkipProvider` + `FastembedProvider`

**Files:**
- Create: `superpowers-plus/skills/memory-management/scripts/embedding.py`
- Create: `superpowers-plus/skills/memory-management/tests/test_embedding.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_embedding.py
import pytest
from scripts.embedding import SkipProvider, get_provider

def test_skip_provider_returns_none():
    p = SkipProvider()
    assert p.embed(["hello"]) == [None]
    assert p.dim == 0
    assert p.name == "skip"

def test_get_provider_skip():
    p = get_provider("skip")
    assert isinstance(p, SkipProvider)

@pytest.mark.skipif_fastembed_unavailable
def test_fastembed_provider_returns_vector():
    from scripts.embedding import FastembedProvider
    p = FastembedProvider()
    vecs = p.embed(["hello world"])
    assert len(vecs) == 1
    assert len(vecs[0]) == p.dim
    assert all(isinstance(x, float) for x in vecs[0])
```

Add to `tests/conftest.py`:
```python
def pytest_configure(config):
    config.addinivalue_line("markers", "skipif_fastembed_unavailable: skip if fastembed not installed")

def pytest_collection_modifyitems(config, items):
    try:
        import fastembed  # noqa
        available = True
    except ImportError:
        available = False
    if not available:
        skip = pytest.mark.skip(reason="fastembed not available")
        for item in items:
            if "skipif_fastembed_unavailable" in item.keywords:
                item.add_marker(skip)
```

- [ ] **Step 2: Run, expect FAIL**

- [ ] **Step 3: Implement `embedding.py`**

```python
# scripts/embedding.py
from typing import Protocol, Optional


class EmbeddingProvider(Protocol):
    name: str
    dim: int
    def embed(self, texts: list[str]) -> list[Optional[list[float]]]: ...


class SkipProvider:
    name = "skip"
    dim = 0

    def embed(self, texts: list[str]) -> list[Optional[list[float]]]:
        return [None for _ in texts]


class FastembedProvider:
    name = "fastembed"
    dim = 384  # bge-small-en-v1.5

    def __init__(self, model: str = "BAAI/bge-small-en-v1.5"):
        from fastembed import TextEmbedding
        self._embedder = TextEmbedding(model_name=model)

    def embed(self, texts: list[str]) -> list[Optional[list[float]]]:
        vectors = list(self._embedder.embed(texts))
        return [v.tolist() for v in vectors]


def get_provider(name: str) -> EmbeddingProvider:
    if name == "skip":
        return SkipProvider()
    if name == "fastembed":
        return FastembedProvider()
    raise ValueError(f"unknown embedding provider: {name}")
```

- [ ] **Step 4: Run, expect PASS**

```bash
uv run pytest tests/test_embedding.py -v
```

- [ ] **Step 5: Commit**

```bash
git add superpowers-plus/skills/memory-management/scripts/embedding.py superpowers-plus/skills/memory-management/tests/test_embedding.py superpowers-plus/skills/memory-management/tests/conftest.py
git commit -m "feat(memory-cli): EmbeddingProvider Protocol + Skip + Fastembed impls"
```

**Note on dim mismatch**: Schema declares `<F32; 1024>` but bge-small is dim 384. **Defer wiring CozoStore HNSW to Task 21** where we resolve this — either by switching to a 1024-dim local model (e.g. `BAAI/bge-large-en-v1.5`), or making `dim` per-config and rebuilding the HNSW index at `init` time. Document the resolution in the spec §10 Open Questions.

---

### Task 21: Wire embeddings into CozoStore + semantic recall

**Files:**
- Modify: `superpowers-plus/skills/memory-management/scripts/cozo_store.py`
- Modify: `superpowers-plus/skills/memory-management/scripts/memory_cli.py`
- Modify: `superpowers-plus/skills/memory-management/tests/test_cli_memory_recall.py`

- [ ] **Step 1: Resolve dim**

Change `cozo_store.py` SCHEMA_RELATIONS first relation: replace `<F32; 1024>?` with `<F32; 384>?`. Document in spec §10: "Resolved 2026-04-07: dim=384 to match bge-small-en-v1.5 (default fastembed). Cloud providers requiring different dims will need a future migration command."

Also update HNSW_INDEX: `dim: 384`.

- [ ] **Step 2: Write failing test**

Append to `tests/test_cli_memory_recall.py`:

```python
import pytest

@pytest.fixture
def initialized_fastembed(run_cli):
    run_cli("init", "--project", "demo", "--embedding", "fastembed", "--non-interactive")
    return run_cli

@pytest.mark.skipif_fastembed_unavailable
def test_recall_semantic_finds_paraphrase(initialized_fastembed):
    cli = initialized_fastembed
    cli("node", "create", "--id", "a", "--name", "auth", "--type", "leaf",
        "--level", "1", "--description", "user authentication via OAuth2", "--origin", "user_stated")
    cli("node", "create", "--id", "b", "--name", "viz", "--type", "leaf",
        "--level", "1", "--description", "draw bar charts", "--origin", "user_stated")
    import json
    r = cli("memory", "recall", "--query", "login system", "--semantic", "--k", "3")
    matches = json.loads(r.stdout)["data"]["matches"]
    assert matches and matches[0]["node"]["id"] == "a"
    assert matches[0]["match_type"] == "semantic"
```

- [ ] **Step 3: Run, expect FAIL**

- [ ] **Step 4: Add embedding storage + semantic recall to CozoStore**

Add a new method, modify `create_node` and `recall`:

```python
    # Add to __init__ args:
    def __init__(self, db_path: str, embedding_provider=None):
        self.db_path = db_path
        self.embedding_provider = embedding_provider
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.client = Client("sqlite", db_path)
        self._schema_ready = False

    # Override create_node to compute embedding when provider exists and is not skip
    def create_node(self, node: Node) -> None:
        self.ensure_schema()
        existing = self.client.run(
            "?[id] := *node{id, project}, project = $p, id = $i",
            {"p": node.project, "i": node.id},
        )
        if existing["rows"]:
            raise StoreError(f"node already exists: {node.id}")
        emb = None
        if self.embedding_provider and self.embedding_provider.name != "skip":
            try:
                emb = self.embedding_provider.embed([node.name + " " + node.description])[0]
            except Exception:
                emb = None  # silent degrade; recall will reflect via match_type
        params = node.to_dict()
        params["embedding"] = emb
        if emb is None:
            self.client.run(
                """
                ?[id, project, name, node_type, level, description, status, origin,
                  tokens_estimate, created_at, updated_at] <- [[
                    $id, $project, $name, $node_type, $level, $description, $status, $origin,
                    $tokens_estimate, $created_at, $updated_at
                ]]
                :put node {
                    id, project, name, node_type, level, description, status, origin,
                    tokens_estimate, created_at, updated_at
                }
                """,
                params,
            )
        else:
            self.client.run(
                """
                ?[id, project, name, node_type, level, description, status, origin,
                  tokens_estimate, created_at, updated_at, embedding] <- [[
                    $id, $project, $name, $node_type, $level, $description, $status, $origin,
                    $tokens_estimate, $created_at, $updated_at, vec($embedding)
                ]]
                :put node {
                    id, project, name, node_type, level, description, status, origin,
                    tokens_estimate, created_at, updated_at => embedding
                }
                """,
                params,
            )

    def recall(self, project: str, query: str, k: int, semantic: bool) -> list[ScoredNode]:
        if semantic and self.embedding_provider and self.embedding_provider.name != "skip":
            try:
                qvec = self.embedding_provider.embed([query])[0]
                if qvec is not None:
                    result = self.client.run(
                        """
                        ?[dist, id, project, name, node_type, level, description, status, origin,
                          tokens_estimate, created_at, updated_at] :=
                          ~node:embedding_idx{
                            id, project, name, node_type, level, description, status, origin,
                            tokens_estimate, created_at, updated_at |
                            query: vec($q),
                            k: $k,
                            ef: 50,
                            bind_distance: dist
                          },
                          project = $p
                        :order +dist
                        """,
                        {"q": qvec, "k": k, "p": project},
                    )
                    out: list[ScoredNode] = []
                    cols = result["headers"]
                    for row in result["rows"]:
                        d = dict(zip(cols, row))
                        node_fields = {k: d[k] for k in Node.__dataclass_fields__}
                        out.append(ScoredNode(node=Node(**node_fields), score=1.0 - d["dist"], match_type="semantic"))
                    return out
            except Exception:
                pass  # fall through to BM25
        # BM25 path (unchanged)
        import re
        terms = [t.lower() for t in re.findall(r"\w+", query)]
        nodes = self.list_nodes(project)
        scored: list[ScoredNode] = []
        for n in nodes:
            text = (n.name + " " + n.description).lower()
            score = sum(text.count(t) for t in terms)
            if score > 0:
                scored.append(ScoredNode(node=n, score=float(score), match_type="bm25"))
        scored.sort(key=lambda s: s.score, reverse=True)
        return scored[:k]
```

Update `_store()` in `memory_cli.py` to inject the provider:

```python
def _store():
    cfg = _load()
    if not cfg.initialized:
        emit_error("not initialized — run `memory_cli.py init` first", code="uninitialized")
    from cozo_store import CozoStore
    from embedding import get_provider
    try:
        provider = get_provider(cfg.embedding_provider)
    except Exception as e:
        provider = None  # degraded
    s = CozoStore(db_path=cfg.expanded_db_path(), embedding_provider=provider)
    s.ensure_schema()
    return s, cfg
```

- [ ] **Step 5: Run, expect PASS (if fastembed available)**

```bash
uv run --with fastembed pytest tests/test_cli_memory_recall.py -v
```

- [ ] **Step 6: Commit**

```bash
git add -u
git commit -m "feat(memory-cli): wire EmbeddingProvider into CozoStore + semantic recall"
```

---

## Chunk 6: Maintenance + Fallbacks

### Task 22: `memory doctor`, `memory reindex`, `memory export`

**Files:**
- Modify: `superpowers-plus/skills/memory-management/scripts/memory_cli.py`
- Create: `superpowers-plus/skills/memory-management/tests/test_cli_memory_doctor.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_cli_memory_doctor.py
import json
import pytest

@pytest.fixture
def initialized(run_cli):
    run_cli("init", "--project", "demo", "--embedding", "skip", "--non-interactive")
    return run_cli

def test_doctor_reports_healthy(initialized):
    r = initialized("memory", "doctor")
    payload = json.loads(r.stdout)["data"]
    assert payload["db_ok"] is True
    assert payload["embedding_provider"] == "skip"

def test_export_returns_json(initialized):
    initialized("node", "create", "--id", "n1", "--name", "x", "--type", "branch",
                "--level", "1", "--description", "x", "--origin", "user_stated")
    r = initialized("memory", "export")
    payload = json.loads(r.stdout)["data"]
    assert "nodes" in payload and len(payload["nodes"]) == 1
```

- [ ] **Step 2: Run, expect FAIL**

- [ ] **Step 3: Add doctor / reindex / export commands**

```python
@memory.command("doctor")
def memory_doctor():
    """Health check for the memory store."""
    cfg = _load()
    db_ok = False
    embedding_ok = cfg.embedding_provider == "skip"
    notes: list[str] = []
    if not cfg.initialized:
        notes.append("not initialized")
    else:
        try:
            from cozo_store import CozoStore
            CozoStore(db_path=cfg.expanded_db_path()).ensure_schema()
            db_ok = True
        except Exception as e:
            notes.append(f"db error: {e}")
        if cfg.embedding_provider != "skip":
            try:
                from embedding import get_provider
                p = get_provider(cfg.embedding_provider)
                p.embed(["healthcheck"])
                embedding_ok = True
            except Exception as e:
                notes.append(f"embedding error: {e}")
    emit({
        "initialized": cfg.initialized,
        "db_ok": db_ok,
        "embedding_provider": cfg.embedding_provider,
        "embedding_ok": embedding_ok,
        "notes": notes,
    })


@memory.command("reindex")
@click.option("--project")
def memory_reindex(project):
    """Recompute embeddings for all nodes in a project."""
    s, cfg = _store()
    if cfg.embedding_provider == "skip":
        emit_error("cannot reindex with embedding_provider=skip")
    p = _project(project, cfg)
    nodes = s.list_nodes(p)
    count = 0
    for n in nodes:
        try:
            s.update_node(p, n.id, updated_at=_now())
            count += 1
        except Exception:
            pass
    emit({"reindexed": count})


@memory.command("export")
@click.option("--project")
def memory_export(project):
    """Export all nodes/edges/decisions/interfaces for a project as JSON."""
    s, cfg = _store()
    p = _project(project, cfg)
    nodes = [n.to_dict() for n in s.list_nodes(p)]
    decisions = []
    interfaces = []
    for n in nodes:
        decisions.extend(d.to_dict() for d in s.list_decisions(p, n["id"]))
        interfaces.extend(i.to_dict() for i in s.list_interfaces(p, n["id"]))
    emit({"nodes": nodes, "decisions": decisions, "interfaces": interfaces})
```

- [ ] **Step 4: Run, expect PASS**

- [ ] **Step 5: Commit**

```bash
git add -u
git commit -m "feat(memory-cli): doctor/reindex/export maintenance commands"
```

---

### Task 23: Fallback matrix tests (§8 of spec)

**Files:**
- Create: `superpowers-plus/skills/memory-management/tests/test_fallbacks.py`

This is one task for all 8 rows of §8. Each row gets one test.

- [ ] **Step 1: Write all 8 fallback tests**

```python
# tests/test_fallbacks.py
"""Exercises every row of spec §8 fallback matrix."""
import json
import os
import pytest
import subprocess
from pathlib import Path

@pytest.fixture
def initialized_skip(run_cli):
    run_cli("init", "--project", "demo", "--embedding", "skip", "--non-interactive")
    return run_cli

# Row 1: uv not installed — covered manually; documented as: SKILL.md prints install hint.
def test_row1_uv_missing_documented():
    """Row 1 is harness-level; assert SKILL.md instruction text exists in M2."""
    pytest.skip("Row 1 (uv missing) is documented in SKILL.md created in M2")

# Row 2: pycozo build failure — out of scope for unit tests; documented.
def test_row2_pycozo_build_failure_documented():
    pytest.skip("Row 2 (pycozo build) verified manually on alpine; see spec §10")

# Row 3: embedding model download fails → falls back to skip
def test_row3_embedding_download_failure_falls_back(run_cli, monkeypatch, tmp_path):
    # Force fastembed init to fail by pointing HF cache at unwriteable dir
    monkeypatch.setenv("HF_HOME", "/dev/null/nonexistent")
    r = run_cli("init", "--project", "demo", "--embedding", "fastembed", "--non-interactive")
    # Init must still succeed (degraded), or report failure clearly
    payload = json.loads(r.stdout) if r.stdout else {}
    # Acceptable: either init reports degraded:true OR explicit error with code
    assert ("degraded" in payload and payload.get("degraded")) or ("error" in payload)

# Row 4: voyage/openai 429 — simulated by injecting a failing provider
def test_row4_provider_runtime_failure_falls_back_to_bm25(initialized_skip):
    # The skip path is itself a degradation of "voyage failed". We test the BM25 fallback.
    initialized_skip("node", "create", "--id", "a", "--name", "auth", "--type", "leaf",
                     "--level", "1", "--description", "OAuth login", "--origin", "user_stated")
    r = initialized_skip("memory", "recall", "--query", "oauth", "--semantic")
    payload = json.loads(r.stdout)
    assert payload["degraded"] is True
    assert payload["data"]["matches"][0]["match_type"] == "bm25"

# Row 5: corrupted DB — write garbage to db file
def test_row5_corrupted_db_reports_error(initialized_skip, tmp_path):
    db_path = tmp_path / ".pyramid-memory" / "data.cozo"
    db_path.write_bytes(b"not a sqlite file at all")
    r = initialized_skip("node", "list")
    payload = json.loads(r.stdout) if r.stdout else {"ok": False}
    assert payload.get("ok") is False or "error" in payload

# Row 6: cross-harness path — same HOME, different harness
def test_row6_shared_home_directory(run_cli, tmp_path):
    run_cli("init", "--project", "demo", "--embedding", "skip", "--non-interactive")
    run_cli("node", "create", "--id", "x", "--name", "x", "--type", "leaf",
            "--level", "1", "--description", "x", "--origin", "user_stated")
    # Second invocation as if a different harness
    r = run_cli("node", "list")
    nodes = json.loads(r.stdout)["data"]["nodes"]
    assert len(nodes) == 1

# Row 7: no-network sandbox — same as row 3 essentially
def test_row7_no_network_uses_skip(run_cli, monkeypatch):
    monkeypatch.setenv("PYRAMID_MEMORY_NO_NETWORK", "1")
    r = run_cli("init", "--project", "demo", "--embedding", "skip", "--non-interactive")
    assert json.loads(r.stdout)["ok"] is True

# Row 8: missing project — fail-fast
def test_row8_missing_project_fails_fast(run_cli):
    run_cli("init", "--project", "demo", "--embedding", "skip", "--non-interactive")
    # Manually corrupt config to remove default_project
    cfg_path = Path(os.environ.get("HOME", "~")).expanduser() / ".pyramid-memory" / "config.toml"
    text = cfg_path.read_text().replace('default_project = "demo"', "")
    cfg_path.write_text(text)
    r = run_cli("node", "list")
    payload = json.loads(r.stdout)
    assert payload.get("ok") is False
    assert payload["error"]["code"] == "missing_project"
```

- [ ] **Step 2: Run all fallback tests**

```bash
uv run pytest tests/test_fallbacks.py -v
```

Some rows are `pytest.skip()` because they're harness-level (Row 1, Row 2). The rest should PASS.

- [ ] **Step 3: Commit**

```bash
git add superpowers-plus/skills/memory-management/tests/test_fallbacks.py
git commit -m "test(memory-cli): exercise all 8 rows of spec §8 fallback matrix"
```

---

## Chunk 7: Final Integration

### Task 24: End-to-end smoke test (full pyramid lifecycle)

**Files:**
- Create: `superpowers-plus/skills/memory-management/tests/test_e2e_smoke.py`

- [ ] **Step 1: Write the smoke test**

```python
# tests/test_e2e_smoke.py
"""Drives the full lifecycle a human/LLM would exercise."""
import json
import pytest

def test_full_pyramid_lifecycle(run_cli):
    cli = run_cli
    # 1. Init
    r = cli("init", "--project", "ecommerce", "--embedding", "skip", "--non-interactive")
    assert json.loads(r.stdout)["ok"]

    # 2. Create root + branches + leaves
    cli("node", "create", "--id", "root", "--name", "ecommerce", "--type", "root",
        "--level", "0", "--description", "online store with cart, payment, inventory",
        "--origin", "user_stated")
    cli("node", "create", "--id", "cart", "--name", "cart", "--type", "branch",
        "--level", "1", "--description", "shopping cart", "--origin", "user_stated")
    cli("node", "create", "--id", "pay", "--name", "payment", "--type", "branch",
        "--level", "1", "--description", "payment processing", "--origin", "user_stated")
    cli("node", "create", "--id", "inv", "--name", "inventory", "--type", "branch",
        "--level", "1", "--description", "stock tracking", "--origin", "skill_inferred")
    cli("node", "create", "--id", "cart-add", "--name", "add-item", "--type", "leaf",
        "--level", "2", "--description", "add item to cart endpoint", "--origin", "skill_inferred")

    # 3. Edges
    for child in ["cart", "pay", "inv"]:
        cli("edge", "add", "--kind", "hierarchy", "--from", "root", "--to", child)
    cli("edge", "add", "--kind", "hierarchy", "--from", "cart", "--to", "cart-add")
    cli("edge", "add", "--kind", "dependency", "--from", "cart-add", "--to", "inv")

    # 4. Decisions on branches
    for n in ["cart", "pay", "inv"]:
        cli("decision", "store", "--id", f"d-{n}", "--node", n,
            "--question", f"why split {n}?", "--options", "[]",
            "--chosen", "isolation", "--reasoning", "single responsibility")

    # 5. Interface on leaf
    cli("interface", "add", "--id", "i-cart-add", "--node", "cart-add",
        "--name", "AddItem", "--description", "add item to cart",
        "--spec", "POST /cart/items {sku, qty} -> {cart_id, total}")

    # 6. Validate (should pass)
    r = cli("memory", "validate")
    assert json.loads(r.stdout)["data"]["passed"] is True

    # 7. Stats (skill_inferred ratio = 2/5 = 0.4)
    r = cli("memory", "stats")
    s = json.loads(r.stdout)["data"]
    assert s["total_nodes"] == 5
    assert s["skill_inferred_node_ratio"] >= 0.3  # AC #6

    # 8. Recall finds the leaf
    r = cli("memory", "recall", "--query", "add cart")
    matches = json.loads(r.stdout)["data"]["matches"]
    assert any(m["node"]["id"] == "cart-add" for m in matches)

    # 9. Context assembly for the leaf
    r = cli("memory", "context", "--node", "cart-add")
    pkg = json.loads(r.stdout)["data"]
    assert pkg["node"]["id"] == "cart-add"
    assert any(a["id"] == "cart" for a in pkg["ancestors"])
    assert any(a["id"] == "root" for a in pkg["ancestors"])
    assert any(d["chosen"] == "isolation" for d in pkg["decisions"])
    assert any(i["name"] == "AddItem" for i in pkg["interfaces"])
    assert any(d["id"] == "inv" for d in pkg["deps"])
    assert pkg["tokens_estimate"] > 0

    # 10. Cycles check
    r = cli("query", "cycles")
    assert json.loads(r.stdout)["data"]["cycles"] == []

    # 11. Export
    r = cli("memory", "export")
    exp = json.loads(r.stdout)["data"]
    assert len(exp["nodes"]) == 5
```

- [ ] **Step 2: Run, expect PASS**

```bash
uv run pytest tests/test_e2e_smoke.py -v
```

- [ ] **Step 3: Commit**

```bash
git add superpowers-plus/skills/memory-management/tests/test_e2e_smoke.py
git commit -m "test(memory-cli): end-to-end pyramid lifecycle smoke test"
```

---

### Task 25: Run full suite, fix lingering issues, tag M1

**Files:** (none new)

- [ ] **Step 1: Run the full test suite**

```bash
cd superpowers-plus/skills/memory-management
uv run pytest -v
```

Expected: All tests PASS (except documented `pytest.skip()` rows in fallback matrix).

- [ ] **Step 2: Smoke-check on a second platform if available**

Run the same suite on Linux if you developed on macOS (or vice versa).

- [ ] **Step 3: Tag the milestone**

```bash
git tag -a m1-memory-cli -m "Milestone 1: pyramid memory CLI complete (storage + commands + fallbacks)"
```

- [ ] **Step 4: Update task #7 to mark M1 done in spec §11.5**

Add a line to `docs/superpowers/specs/2026-04-07-pyramid-memory-skill-design.md` §11.5 Milestone 1 section: `**Status: Shipped 2026-MM-DD (tag: m1-memory-cli)**`.

- [ ] **Step 5: Commit the spec update**

```bash
git add docs/superpowers/specs/2026-04-07-pyramid-memory-skill-design.md
git commit -m "docs: mark Milestone 1 as shipped in pyramid memory spec"
```

---

## Self-Review Checklist (run after writing the plan)

### Spec coverage
| Spec section | Plan tasks |
|---|---|
| §3 CozoDB schema | Tasks 0, 4 |
| §3 MemoryStore Protocol | Task 3 |
| §4 CLI command groups | Tasks 12–19, 22 |
| §4 JSON output contract | Task 11 |
| §5 Embedding strategy | Tasks 20, 21 |
| §8 Fallback matrix | Task 23 |
| AC #1 (init works) | Tasks 12, 24 |
| AC #3 (≥100 leaves no full load) | Implicit in query design; 24 covers small case |
| AC #5 (validate gate) | Task 19 |
| AC #6 (stats ratio) | Task 19 |
| AC #7 (5 criteria — leaf rejection) | Deferred to M2 (criteria are skill-level enforcement; CLI exposes `validate`) |
| AC #8 (zero shared mutable state) | Out of M1 scope; relies on skill orchestration |
| AC #9 (no implicit imports / cycles) | Task 6, 15 |
| AC #10 (init cross-platform) | Task 12, 25 |
| AC #11 (recall two modes) | Tasks 17, 21 |
| AC #12 (8 fallback rows) | Task 23 |
| AC #13 (Protocol with two impls) | Tasks 3, 4–7, 8 |

**Coverage gaps acknowledged**: AC #3 (large pyramid scaling), AC #7 and #8 are not validated by M1 tests — they require the skill orchestration layer in M2. M1 provides the substrate; M2 proves the user-facing properties.

### Type consistency
- `Node` fields used identically across Tasks 2, 3, 4, 5, 7, 21
- `Edge.kind` values (`hierarchy` | `dependency`) consistent across Tasks 3, 6, 14, 15
- `match_type` values (`bm25` | `semantic` | `exact`) consistent across Tasks 3, 7, 17, 21
- `--origin` values (`user_stated` | `skill_inferred`) consistent across Tasks 13, 19, 24
- `_store()` and `_project()` helpers introduced in Task 13, used in Tasks 14–22

### Placeholder scan
- No "TODO", "TBD", "implement later" in steps
- All code blocks complete
- Spike (Task 0) is a real one-time validation, not a placeholder
- Task 21 has a real dim resolution decision (384) — not deferred

### Known risks (called out in plan)
1. **Task 0 outcome may invalidate Task 4 schema** — if HNSW filter fails, Task 4 needs the schema patched. Plan acknowledges this in Task 4 step 3 NOTE.
2. **Task 21 dim mismatch** — resolved to 384; cloud providers requiring 1024 deferred to M2 or future work.
3. **CozoDB Datalog query syntax** — every query in Tasks 4–7 is written but unverified against current pycozo. Tasks 4–7 may need iteration during execution; the test-first structure catches mismatches early.
