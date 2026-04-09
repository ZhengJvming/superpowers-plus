# Pyramid Memory — Milestone 5: Session Context Management

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give the LLM a structured scratchpad to capture in-session discoveries, classify their value, recall them before decisions, and survive context compaction — all while keeping the context window lean and prefix-cache friendly.

**Architecture:** Lightweight JSON-backed scratchpad (not CozoDB — this is ephemeral/session-scoped). Three CLI commands (`scratch write/list/promote`). Value classification rules and pre-decision recall gate written into skill files. No new hard dependencies.

**Tech Stack:** Same as M1-M4. Python CLI. `json` stdlib for scratchpad file. No new deps.

**Spec:** `docs/superpowers/specs/2026-04-07-pyramid-memory-skill-design.md` — Milestone 5 (§11.5).

**Prerequisite:** M3 shipped (needs `--summary` mode for pre-decision recall). M4 not strictly required but recommended.

---

## File Map

```
superpowers-plus/skills/memory-management/
├── scripts/
│   ├── memory_cli.py              # MODIFY: add scratch write/list/promote/clear commands
│   ├── models.py                  # MODIFY: add ScratchEntry dataclass
│   └── scratchpad.py              # NEW: JSON file read/write for scratchpad
└── tests/
    ├── test_models.py             # MODIFY: add ScratchEntry tests
    ├── test_scratchpad.py         # NEW: scratchpad storage unit tests
    ├── test_cli_scratch.py        # NEW: scratch CLI commands
    └── test_pre_decision_recall.py # NEW: integration test for recall gate

superpowers-plus/skills/memory-management/
└── SKILL.md                       # MODIFY: add Session Context Management section
                                   #   - value classification table
                                   #   - pre-decision recall gate
                                   #   - cache-friendly rules

superpowers-plus/skills/pyramid-decomposition/
└── SKILL.md                       # MODIFY: add pre-decision recall step to Phase 1
```

---

## Chunk 1: Data Model

### Task 1: Add `ScratchEntry` dataclass

**Files:**
- Modify: `superpowers-plus/skills/memory-management/scripts/models.py`
- Modify: `superpowers-plus/skills/memory-management/tests/test_models.py`

- [ ] **Step 1: Write the failing test**

```python
# Append to tests/test_models.py
from models import ScratchEntry

def test_scratch_entry_dataclass():
    e = ScratchEntry(
        key="api-rate-limit",
        value="Payment API rate limit is 100/min",
        category="must_persist",
        ttl="session",
        created_at="2026-04-09T10:00:00Z",
    )
    d = e.to_dict()
    assert d["key"] == "api-rate-limit"
    assert d["category"] == "must_persist"
    e2 = ScratchEntry.from_dict(d)
    assert e2 == e

def test_scratch_entry_defaults():
    e = ScratchEntry(
        key="temp",
        value="something",
        created_at="2026-04-09T10:00:00Z",
    )
    assert e.category == "session_keep"
    assert e.ttl == "session"
```

- [ ] **Step 2: Run, expect FAIL**

```bash
uv run pytest tests/test_models.py::test_scratch_entry_dataclass tests/test_models.py::test_scratch_entry_defaults -v
```

- [ ] **Step 3: Implement**

```python
@dataclass
class ScratchEntry:
    key: str
    value: str
    created_at: str
    category: str = "session_keep"   # must_persist | session_keep
    ttl: str = "session"             # session | persist

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "ScratchEntry":
        return cls(**{k: d[k] for k in cls.__dataclass_fields__ if k in d})
```

- [ ] **Step 4: Run, expect PASS**

- [ ] **Step 5: Commit**

```bash
git add -u
git commit -m "feat(models): add ScratchEntry dataclass"
```

---

## Chunk 2: Scratchpad Storage

### Task 2: Create `scratchpad.py` — JSON file backend

**Files:**
- Create: `superpowers-plus/skills/memory-management/scripts/scratchpad.py`
- Create: `superpowers-plus/skills/memory-management/tests/test_scratchpad.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_scratchpad.py
import json
from pathlib import Path
from models import ScratchEntry
from scratchpad import ScratchpadStore

def test_write_and_list(tmp_path):
    sp = ScratchpadStore(tmp_path / "scratchpad.json")
    sp.write(ScratchEntry(
        key="finding-1", value="API uses pagination",
        category="session_keep", ttl="session", created_at="t1",
    ))
    sp.write(ScratchEntry(
        key="constraint-1", value="Must not use Redis",
        category="must_persist", ttl="persist", created_at="t2",
    ))
    entries = sp.list_all()
    assert len(entries) == 2
    assert entries[0].key == "finding-1"

def test_list_by_category(tmp_path):
    sp = ScratchpadStore(tmp_path / "scratchpad.json")
    sp.write(ScratchEntry(key="a", value="x", category="session_keep", created_at="t"))
    sp.write(ScratchEntry(key="b", value="y", category="must_persist", created_at="t"))
    assert len(sp.list_all(category="must_persist")) == 1
    assert sp.list_all(category="must_persist")[0].key == "b"

def test_write_overwrites_same_key(tmp_path):
    sp = ScratchpadStore(tmp_path / "scratchpad.json")
    sp.write(ScratchEntry(key="k", value="old", created_at="t1"))
    sp.write(ScratchEntry(key="k", value="new", created_at="t2"))
    entries = sp.list_all()
    assert len(entries) == 1
    assert entries[0].value == "new"

def test_delete(tmp_path):
    sp = ScratchpadStore(tmp_path / "scratchpad.json")
    sp.write(ScratchEntry(key="k", value="v", created_at="t"))
    sp.delete("k")
    assert sp.list_all() == []

def test_clear_session_only(tmp_path):
    sp = ScratchpadStore(tmp_path / "scratchpad.json")
    sp.write(ScratchEntry(key="s", value="x", ttl="session", created_at="t"))
    sp.write(ScratchEntry(key="p", value="y", ttl="persist", created_at="t"))
    sp.clear(ttl="session")
    entries = sp.list_all()
    assert len(entries) == 1
    assert entries[0].key == "p"

def test_clear_all(tmp_path):
    sp = ScratchpadStore(tmp_path / "scratchpad.json")
    sp.write(ScratchEntry(key="a", value="x", created_at="t"))
    sp.write(ScratchEntry(key="b", value="y", created_at="t"))
    sp.clear()
    assert sp.list_all() == []

def test_persistence_across_instances(tmp_path):
    path = tmp_path / "scratchpad.json"
    sp1 = ScratchpadStore(path)
    sp1.write(ScratchEntry(key="k", value="v", created_at="t"))
    sp2 = ScratchpadStore(path)
    assert len(sp2.list_all()) == 1

def test_empty_file_returns_empty_list(tmp_path):
    sp = ScratchpadStore(tmp_path / "scratchpad.json")
    assert sp.list_all() == []
```

- [ ] **Step 2: Run, expect FAIL**

```bash
uv run pytest tests/test_scratchpad.py -v
```

- [ ] **Step 3: Implement**

```python
# scripts/scratchpad.py
"""Lightweight JSON-backed session scratchpad. Not CozoDB — this is ephemeral."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

try:
    from .models import ScratchEntry
except ImportError:
    from models import ScratchEntry


class ScratchpadStore:
    def __init__(self, path: Path):
        self._path = path

    def _read(self) -> list[dict]:
        if not self._path.exists():
            return []
        text = self._path.read_text()
        if not text.strip():
            return []
        return json.loads(text)

    def _write_all(self, entries: list[dict]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(entries, ensure_ascii=False, indent=2))

    def write(self, entry: ScratchEntry) -> None:
        entries = [e for e in self._read() if e["key"] != entry.key]
        entries.append(entry.to_dict())
        self._write_all(entries)

    def list_all(self, *, category: Optional[str] = None) -> list[ScratchEntry]:
        entries = self._read()
        if category:
            entries = [e for e in entries if e.get("category") == category]
        return [ScratchEntry.from_dict(e) for e in entries]

    def delete(self, key: str) -> None:
        entries = [e for e in self._read() if e["key"] != key]
        self._write_all(entries)

    def clear(self, *, ttl: Optional[str] = None) -> None:
        if ttl is None:
            self._write_all([])
        else:
            entries = [e for e in self._read() if e.get("ttl") != ttl]
            self._write_all(entries)
```

- [ ] **Step 4: Run, expect PASS**

- [ ] **Step 5: Commit**

```bash
git add scripts/scratchpad.py tests/test_scratchpad.py
git commit -m "feat(memory-cli): add ScratchpadStore JSON backend"
```

---

## Chunk 3: CLI Commands

### Task 3: Add `scratch write` command

**Files:**
- Modify: `superpowers-plus/skills/memory-management/scripts/memory_cli.py`
- Create: `superpowers-plus/skills/memory-management/tests/test_cli_scratch.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_cli_scratch.py
import json

def test_scratch_write_and_list(run_cli):
    run_cli("init", "--project", "demo", "--embedding", "skip", "--non-interactive")
    r = run_cli("scratch", "write", "--key", "api-limit",
                "--value", "Rate limit is 100/min",
                "--category", "must_persist", "--ttl", "persist")
    assert json.loads(r.stdout)["ok"]

    r = run_cli("scratch", "list")
    entries = json.loads(r.stdout)["data"]["entries"]
    assert len(entries) == 1
    assert entries[0]["key"] == "api-limit"
    assert entries[0]["category"] == "must_persist"

def test_scratch_write_defaults(run_cli):
    run_cli("init", "--project", "demo", "--embedding", "skip", "--non-interactive")
    run_cli("scratch", "write", "--key", "temp", "--value", "some finding")
    r = run_cli("scratch", "list")
    e = json.loads(r.stdout)["data"]["entries"][0]
    assert e["category"] == "session_keep"
    assert e["ttl"] == "session"

def test_scratch_list_by_category(run_cli):
    run_cli("init", "--project", "demo", "--embedding", "skip", "--non-interactive")
    run_cli("scratch", "write", "--key", "a", "--value", "x", "--category", "session_keep")
    run_cli("scratch", "write", "--key", "b", "--value", "y", "--category", "must_persist")
    r = run_cli("scratch", "list", "--category", "must_persist")
    entries = json.loads(r.stdout)["data"]["entries"]
    assert len(entries) == 1
    assert entries[0]["key"] == "b"
```

- [ ] **Step 2: Run, expect FAIL**

```bash
uv run pytest tests/test_cli_scratch.py -v
```

- [ ] **Step 3: Implement**

```python
@cli.group("scratch")
def scratch_group():
    """Session scratchpad for in-conversation findings."""
    pass

def _scratchpad():
    """Get scratchpad store. Works even without full init (scratchpad is lightweight)."""
    cfg = _load()
    from pathlib import Path
    from scratchpad import ScratchpadStore
    storage_dir = Path(cfg.db_path).parent
    return ScratchpadStore(storage_dir / "scratchpad.json")

@scratch_group.command("write")
@click.option("--key", required=True)
@click.option("--value", required=True)
@click.option("--category", default="session_keep",
              type=click.Choice(["must_persist", "session_keep"]))
@click.option("--ttl", default="session", type=click.Choice(["session", "persist"]))
def scratch_write(key, value, category, ttl):
    """Write a finding to the session scratchpad."""
    from models import ScratchEntry
    sp = _scratchpad()
    sp.write(ScratchEntry(key=key, value=value, category=category, ttl=ttl, created_at=_now()))
    emit({"key": key, "written": True})

@scratch_group.command("list")
@click.option("--category", default=None,
              type=click.Choice(["must_persist", "session_keep"]))
def scratch_list(category):
    """List scratchpad entries."""
    sp = _scratchpad()
    entries = sp.list_all(category=category)
    emit({"entries": [e.to_dict() for e in entries], "count": len(entries)})
```

- [ ] **Step 4: Run, expect PASS**

- [ ] **Step 5: Commit**

```bash
git add -u && git add tests/test_cli_scratch.py
git commit -m "feat(memory-cli): add scratch write/list commands"
```

---

### Task 4: Add `scratch promote` command

**Files:**
- Modify: `superpowers-plus/skills/memory-management/scripts/memory_cli.py`
- Modify: `superpowers-plus/skills/memory-management/tests/test_cli_scratch.py`

- [ ] **Step 1: Write the failing test**

```python
# Append to tests/test_cli_scratch.py
def test_scratch_promote_to_decision(run_cli):
    run_cli("init", "--project", "demo", "--embedding", "skip", "--non-interactive")
    run_cli("node", "create", "--id", "root", "--name", "root", "--type", "root",
            "--level", "0", "--description", "r", "--origin", "user_stated")
    run_cli("scratch", "write", "--key", "no-redis",
            "--value", "User said: must not use Redis, use in-memory cache instead",
            "--category", "must_persist", "--ttl", "persist")

    r = run_cli("scratch", "promote", "--key", "no-redis", "--node", "root",
                "--as", "decision")
    assert json.loads(r.stdout)["ok"]
    data = json.loads(r.stdout)["data"]
    assert data["promoted_as"] == "decision"

    # Verify decision was created
    r2 = run_cli("decision", "list", "--node", "root")
    decisions = json.loads(r2.stdout)["data"]["decisions"]
    assert any("no-redis" in d["id"] or "Redis" in d["reasoning"] for d in decisions)

    # Verify scratchpad entry was removed
    r3 = run_cli("scratch", "list")
    entries = json.loads(r3.stdout)["data"]["entries"]
    assert all(e["key"] != "no-redis" for e in entries)

def test_scratch_promote_to_interface(run_cli):
    run_cli("init", "--project", "demo", "--embedding", "skip", "--non-interactive")
    run_cli("node", "create", "--id", "leaf-1", "--name", "api", "--type", "leaf",
            "--level", "1", "--description", "payment api", "--origin", "user_stated")
    run_cli("scratch", "write", "--key", "pay-api-spec",
            "--value", "POST /pay {amount, currency} -> {tx_id, status}",
            "--category", "must_persist")

    r = run_cli("scratch", "promote", "--key", "pay-api-spec", "--node", "leaf-1",
                "--as", "interface")
    assert json.loads(r.stdout)["ok"]

    r2 = run_cli("interface", "list", "--node", "leaf-1")
    interfaces = json.loads(r2.stdout)["data"]["interfaces"]
    assert len(interfaces) >= 1
```

- [ ] **Step 2: Run, expect FAIL**

- [ ] **Step 3: Implement**

```python
@scratch_group.command("promote")
@click.option("--key", required=True)
@click.option("--node", "node_id", required=True)
@click.option("--as", "promote_as", required=True,
              type=click.Choice(["decision", "interface"]))
@click.option("--project")
def scratch_promote(key, node_id, promote_as, project):
    """Promote a scratchpad entry to persistent pyramid memory."""
    sp = _scratchpad()
    entries = [e for e in sp.list_all() if e.key == key]
    if not entries:
        emit_error(f"scratchpad key not found: {key}", code="not_found")
        return

    entry = entries[0]
    s, cfg = _store()
    p = _project(project, cfg)

    import uuid
    if promote_as == "decision":
        from models import Decision
        d = Decision(
            id=f"scratch-{key}-{uuid.uuid4().hex[:8]}",
            node_id=node_id,
            question=f"Session finding: {key}",
            options="[]",
            chosen=entry.value,
            reasoning=entry.value,
            tradeoffs="Promoted from session scratchpad",
            created_at=_now(),
        )
        s.store_decision(d)
    elif promote_as == "interface":
        from models import Interface
        i = Interface(
            id=f"scratch-{key}-{uuid.uuid4().hex[:8]}",
            node_id=node_id,
            name=key,
            description=f"Discovered during session: {key}",
            spec=entry.value,
            created_at=_now(),
        )
        s.add_interface(i)

    sp.delete(key)
    emit({"key": key, "node_id": node_id, "promoted_as": promote_as})
```

- [ ] **Step 4: Run, expect PASS**

- [ ] **Step 5: Commit**

```bash
git add -u
git commit -m "feat(memory-cli): add scratch promote command"
```

---

### Task 5: Add `scratch clear` command

**Files:**
- Modify: `superpowers-plus/skills/memory-management/scripts/memory_cli.py`
- Modify: `superpowers-plus/skills/memory-management/tests/test_cli_scratch.py`

- [ ] **Step 1: Write the failing test**

```python
# Append to tests/test_cli_scratch.py
def test_scratch_clear_session_only(run_cli):
    run_cli("init", "--project", "demo", "--embedding", "skip", "--non-interactive")
    run_cli("scratch", "write", "--key", "s1", "--value", "x", "--ttl", "session")
    run_cli("scratch", "write", "--key", "p1", "--value", "y", "--ttl", "persist")
    r = run_cli("scratch", "clear", "--ttl", "session")
    assert json.loads(r.stdout)["ok"]
    r2 = run_cli("scratch", "list")
    entries = json.loads(r2.stdout)["data"]["entries"]
    assert len(entries) == 1
    assert entries[0]["key"] == "p1"

def test_scratch_clear_all(run_cli):
    run_cli("init", "--project", "demo", "--embedding", "skip", "--non-interactive")
    run_cli("scratch", "write", "--key", "a", "--value", "x")
    run_cli("scratch", "write", "--key", "b", "--value", "y")
    run_cli("scratch", "clear")
    r = run_cli("scratch", "list")
    assert json.loads(r.stdout)["data"]["count"] == 0
```

- [ ] **Step 2: Run, expect FAIL**

- [ ] **Step 3: Implement**

```python
@scratch_group.command("clear")
@click.option("--ttl", default=None, type=click.Choice(["session", "persist"]),
              help="Only clear entries with this TTL. Omit to clear all.")
def scratch_clear(ttl):
    """Clear scratchpad entries."""
    sp = _scratchpad()
    before = len(sp.list_all())
    sp.clear(ttl=ttl)
    after = len(sp.list_all())
    emit({"cleared": before - after, "remaining": after})
```

- [ ] **Step 4: Run, expect PASS**

- [ ] **Step 5: Commit**

```bash
git add -u
git commit -m "feat(memory-cli): add scratch clear command"
```

---

## Chunk 4: Skill — Value Classification & Pre-Decision Recall

### Task 6: Add Session Context Management section to `memory-management/SKILL.md`

**Files:**
- Modify: `superpowers-plus/skills/memory-management/SKILL.md`

- [ ] **Step 1: Append the new section**

```markdown
---

## Session Context Management

### When to Write to Scratchpad

After any tool call or user message that reveals non-obvious information, ask yourself:

| Signal | Category | Action |
|--------|----------|--------|
| User says "必须/不要/一定/约束/constraint" | `must_persist` | `scratch write --category must_persist --ttl persist` |
| Discovered code behavior differs from expectation | `must_persist` | `scratch write --category must_persist --ttl persist` |
| Found a hidden dependency or coupling | `must_persist` | `scratch write --category must_persist --ttl persist` |
| Code structure finding (module layout, key files) | `session_keep` | `scratch write --category session_keep` |
| API response shape, config values, env details | `session_keep` | `scratch write --category session_keep` |
| Intermediate grep/find output | — | Do NOT write. Summarize in your response if relevant. |
| Debugging steps that didn't pan out | — | Do NOT write. Dead ends are noise. |
| Information already in scratchpad | — | Do NOT write again. Check `scratch list` first. |

**The test**: "If context gets compacted right now, would losing this information force me to re-execute tool calls?" If yes → write it. If no → skip.

### Value Classification Rules (mechanical, not vibes)

```
AFTER any tool call that returned useful information:

1. Can I summarize the key finding in one sentence?
   - YES → write the summary (not the raw output) to scratch
   - NO → the finding is too vague to be useful, skip

2. Did the user express a preference or constraint?
   - YES → must_persist, ttl=persist
   - NO → continue

3. Would this information change an architectural decision?
   - YES → must_persist, ttl=persist
   - NO → session_keep, ttl=session

NEVER write raw tool output. Always summarize first.
```

### Pre-Decision Recall Gate

**BEFORE** any of these actions:
- `node create`
- `decision store`
- Answering an architecture question
- Proposing a decomposition split
- Committing code

Execute this checklist:

```bash
# 1. Check session findings
scratch list

# 2. Check persistent memory
memory recall --query "<what you're about to decide>" --k 3

# 3. Check ancestor context (if in decomposition)
query ancestors --id <current-node> --summary
```

Synthesize all three sources BEFORE acting. If any source contains information that contradicts or constrains your planned action, address it explicitly.

**Skipping any step = potentially missing critical context. This is non-negotiable.**

### Cache-Friendly Rules

1. **Load pyramid context ONCE at session start** — call `memory context` or `memory recall` once, then rely on scratchpad for new findings. Do NOT re-call `memory context` every turn.
2. **Scratchpad reads are cheap** — `scratch list` returns a small JSON. Call it freely.
3. **Never inject dynamic content into system prompt** — skills are static, system prompt is static. This preserves prefix cache.
4. **Append-only pattern** — new findings go to scratchpad (end of context). Never try to "insert" information into earlier conversation turns.
5. **Summarize, don't dump** — when reporting tool results, give a 1-2 sentence summary. The raw output lives in tool call history; your summary is what gets cached in the growing conversation prefix.

### When to Promote

At natural breakpoints (completing a decomposition level, finishing a task, before switching topics):

```bash
# Check what should be persisted
scratch list --category must_persist

# Promote each to pyramid memory
scratch promote --key <key> --node <relevant-node> --as decision
# or
scratch promote --key <key> --node <relevant-node> --as interface

# Clean up session entries
scratch clear --ttl session
```

Don't wait until session end — promote as you go. Context compaction can happen at any time.
```

- [ ] **Step 2: Verify the SKILL.md reads coherently end-to-end**

Read the full file. Ensure no duplication with existing sections.

- [ ] **Step 3: Commit**

```bash
git add superpowers-plus/skills/memory-management/SKILL.md
git commit -m "feat(skill): add Session Context Management to memory-management SKILL.md"
```

---

### Task 7: Add pre-decision recall step to `pyramid-decomposition/SKILL.md`

**Files:**
- Modify: `superpowers-plus/skills/pyramid-decomposition/SKILL.md`

- [ ] **Step 1: Insert recall step into Phase 1 BFS Loop**

In the BFS Loop section (Phase 1), before "2. Decide: can N be a leaf?", insert:

```markdown
        1.5. **Pre-decision recall** (MANDATORY):
             ```bash
             scratch list
             memory recall --query "<N.description>" --k 3
             ```
             Check: does any scratchpad entry or recalled memory constrain this node's decomposition?
             If yes: incorporate the constraint before proceeding.
```

Also add to Phase 0.5 (Impact Analysis), before "Confirm with user":

```markdown
Before confirming affected modules, run pre-decision recall:
```bash
scratch list
memory recall --query "<change description>" --k 3
```
Check for prior findings that affect impact scope.
```

- [ ] **Step 2: Verify consistency**

Read full SKILL.md. Ensure recall steps don't conflict with existing context budget rules (scratch list is small, recall --k 3 is bounded).

- [ ] **Step 3: Commit**

```bash
git add superpowers-plus/skills/pyramid-decomposition/SKILL.md
git commit -m "feat(skill): add pre-decision recall gate to pyramid-decomposition"
```

---

## Chunk 5: Integration Test

### Task 8: Pre-decision recall integration test

Proves that scratchpad findings survive across a multi-step session and are available for recall.

**Files:**
- Create: `superpowers-plus/skills/memory-management/tests/test_pre_decision_recall.py`

- [ ] **Step 1: Write the test**

```python
# tests/test_pre_decision_recall.py
"""
Simulate a multi-step session:
1. LLM discovers something → scratch write
2. Multiple tool calls happen (context grows)
3. Before a decision → scratch list recovers the finding
4. promote → finding persists in pyramid memory
"""
import json

def test_scratch_survives_and_informs_decision(run_cli):
    cli = run_cli
    cli("init", "--project", "demo", "--embedding", "skip", "--non-interactive")
    cli("node", "create", "--id", "root", "--name", "system", "--type", "root",
        "--level", "0", "--description", "e-commerce system", "--origin", "user_stated")

    # Step 1: LLM discovers a constraint
    cli("scratch", "write", "--key", "no-redis",
        "--value", "User constraint: no Redis, use Postgres-backed cache",
        "--category", "must_persist", "--ttl", "persist")

    # Step 2: LLM discovers code structure
    cli("scratch", "write", "--key", "cache-module",
        "--value", "Existing cache at src/cache/lru.py, 200 lines, LRU in-memory",
        "--category", "session_keep")

    # Step 3: More work happens... simulate with unrelated operations
    cli("node", "create", "--id", "auth", "--name", "auth", "--type", "branch",
        "--level", "1", "--description", "authentication module", "--origin", "user_stated")
    cli("edge", "add", "--kind", "hierarchy", "--from", "root", "--to", "auth")
    cli("decision", "store", "--id", "d1", "--node", "root",
        "--question", "how to split?", "--options", "[]",
        "--chosen", "by domain", "--reasoning", "natural boundaries")

    # Step 4: Before making a cache-related decision, recall
    r = cli("scratch", "list")
    entries = json.loads(r.stdout)["data"]["entries"]
    assert len(entries) == 2

    # Find the constraint
    constraints = [e for e in entries if e["category"] == "must_persist"]
    assert len(constraints) == 1
    assert "Redis" in constraints[0]["value"]

    # Also check persistent memory recall
    r2 = cli("memory", "recall", "--query", "cache", "--k", "3")
    # This may or may not find results depending on node descriptions,
    # but the scratch list definitely has it

    # Step 5: Promote the constraint to a decision
    r3 = cli("scratch", "promote", "--key", "no-redis", "--node", "root",
             "--as", "decision")
    assert json.loads(r3.stdout)["ok"]

    # Verify it's now in pyramid memory
    r4 = cli("decision", "list", "--node", "root")
    decisions = json.loads(r4.stdout)["data"]["decisions"]
    redis_decisions = [d for d in decisions if "Redis" in d.get("reasoning", "")]
    assert len(redis_decisions) >= 1

    # Verify scratch entry was cleaned up
    r5 = cli("scratch", "list", "--category", "must_persist")
    assert json.loads(r5.stdout)["data"]["count"] == 0
```

- [ ] **Step 2: Run, expect PASS**

```bash
uv run pytest tests/test_pre_decision_recall.py -v
```

- [ ] **Step 3: Commit**

```bash
git add tests/test_pre_decision_recall.py
git commit -m "test(memory-cli): pre-decision recall integration test"
```

---

## Chunk 6: Full Test + Tag

### Task 9: Run full test suite + tag M5

- [ ] **Step 1: Run all tests**

```bash
cd superpowers-plus/skills/memory-management
uv run pytest -v
```

Expected: All M1 + M2 + M3 + M4 + M5 tests PASS.

- [ ] **Step 2: Tag**

```bash
git tag -a m5-session-context -m "Milestone 5: session context management — scratchpad, value classification, pre-decision recall"
```

- [ ] **Step 3: Update spec §11.5**

Add: `**Status: Shipped 2026-MM-DD (tag: m5-session-context)**`

- [ ] **Step 4: Commit**

```bash
git add docs/superpowers/specs/2026-04-07-pyramid-memory-skill-design.md
git commit -m "docs: mark Milestone 5 as shipped"
```

---

## Self-Review

### Spec coverage

| Spec M5 scope item | Plan task |
|---|---|
| `ScratchEntry` data model | Task 1 |
| `scratchpad.py` JSON backend | Task 2 |
| `scratch write` CLI | Task 3 |
| `scratch list` CLI | Task 3 |
| `scratch promote` CLI | Task 4 |
| `scratch clear` CLI | Task 5 |
| Value classification criteria in SKILL.md | Task 6 |
| Pre-decision recall gate in SKILL.md | Task 6 |
| Pre-decision recall in pyramid-decomposition | Task 7 |
| Cache-friendly design rules | Task 6 |
| Context management guidance | Task 6 |

### Exit criteria mapping

| Criterion | Verified by |
|---|---|
| Scratchpad survives context compaction | Task 2 (file-backed persistence), Task 8 (integration) |
| Pre-decision recall catches prior findings | Task 8 (multi-step integration test) |
| `scratch write` + `scratch list` < 50ms | Task 2 (JSON read/write, trivially fast) |
| Prefix cache hit rate > 80% | Task 6 (skill rules prevent cache-breaking patterns; manual verification) |

### Dependency order

```
Task 1 (ScratchEntry model)
Task 2 (ScratchpadStore — depends on Task 1)
Task 3 (scratch write/list CLI — depends on Task 2)
Task 4 (scratch promote — depends on Task 3)
Task 5 (scratch clear — depends on Task 2)
Task 6 (SKILL.md — independent of CLI, but references commands)
Task 7 (pyramid-decomposition SKILL.md — independent)
Task 8 (integration test — depends on Tasks 3-5)
Task 9 (full test + tag — depends on all)
```

### Task execution order (recommended)

1. Task 1 (ScratchEntry dataclass)
2. Task 2 (ScratchpadStore)
3. Task 3 (scratch write/list CLI)
4. Task 5 (scratch clear CLI)
5. Task 4 (scratch promote CLI)
6. Task 6 (memory-management SKILL.md)
7. Task 7 (pyramid-decomposition SKILL.md)
8. Task 8 (integration test)
9. Task 9 (full test + tag)
