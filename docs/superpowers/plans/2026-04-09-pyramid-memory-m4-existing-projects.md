# Pyramid Memory — Milestone 4: Existing Project Support

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enable the pyramid memory system to work on existing codebases (not just greenfield). The LLM should automatically explore unfamiliar code, keep memory fresh as code changes, scope changes via impact analysis, and decompose *modifications* — all without user-initiated triggers.

**Architecture:** Three extensions: (1) `FileRef` data model + CRUD in both store impls, (2) `memory freshness/refresh` CLI for git-diff-based stale detection, (3) new `codebase-exploration` skill + impact-analysis phase in `pyramid-decomposition`. Config gains `[scan]` section. `assemble_context` extended to include file-refs.

**Tech Stack:** Same as M1-M3. Python CLI + CozoDB. Git integration via `subprocess` calls to `git diff/log`. No new hard dependencies.

**Spec:** `docs/superpowers/specs/2026-04-07-pyramid-memory-skill-design.md` — Milestone 4 (§11.5).

**Prerequisite:** M3 shipped.

---

## File Map

```
superpowers-plus/skills/memory-management/
├── scripts/
│   ├── memory_cli.py              # MODIFY: add file-ref, freshness, refresh commands
│   ├── models.py                  # MODIFY: add FileRef dataclass
│   ├── store.py                   # MODIFY: add FileRef methods to Protocol + InMemoryStore
│   ├── cozo_store.py              # MODIFY: add FileRef methods to CozoStore
│   ├── config.py                  # MODIFY: add [scan] section (last_commit, project_root)
│   └── git_utils.py              # NEW: git diff/log helpers
└── tests/
    ├── test_models.py             # MODIFY: add FileRef tests
    ├── test_file_ref_store.py     # NEW: FileRef CRUD across both store impls
    ├── test_cli_file_ref.py       # NEW: file-ref add/list/check CLI tests
    ├── test_cli_freshness.py      # NEW: memory freshness CLI test
    ├── test_cli_refresh.py        # NEW: memory refresh CLI test
    ├── test_git_utils.py          # NEW: git helper unit tests
    ├── test_context_with_file_refs.py  # NEW: assemble_context includes file_refs
    └── test_auto_trigger_protocol.py   # NEW: freshness + refresh integration

superpowers-plus/skills/codebase-exploration/
├── SKILL.md                       # NEW: codebase-exploration skill
└── exploration-guide.md           # NEW: module-scan strategy + auto-trigger protocol

superpowers-plus/skills/pyramid-decomposition/
├── SKILL.md                       # MODIFY: add Phase 0.5 (impact analysis for existing projects)
└── decomposition-guide.md         # MODIFY: add "Existing Projects" section
```

---

## Chunk 1: Data Model — `FileRef` dataclass

### Task 1: Add `FileRef` dataclass to `models.py`

**Files:**
- Modify: `superpowers-plus/skills/memory-management/scripts/models.py`
- Modify: `superpowers-plus/skills/memory-management/tests/test_models.py`

- [ ] **Step 1: Write the failing test**

```python
# Append to tests/test_models.py
from models import FileRef

def test_file_ref_dataclass():
    fr = FileRef(
        id="fr-1", node_id="leaf-1", path="src/payment/service.py",
        lines="45-120", role="modify", content_hash="abc123",
        scanned_at="2026-04-09T00:00:00Z", status="current",
    )
    d = fr.to_dict()
    assert d["id"] == "fr-1"
    assert d["role"] == "modify"
    assert d["status"] == "current"
    fr2 = FileRef.from_dict(d)
    assert fr2 == fr
```

- [ ] **Step 2: Run, expect FAIL**

```bash
uv run pytest tests/test_models.py::test_file_ref_dataclass -v
```

- [ ] **Step 3: Implement**

Add to `models.py`:
```python
@dataclass
class FileRef:
    id: str
    node_id: str
    path: str           # relative to project root
    lines: str          # "45-120" or "*" for whole file
    role: str           # modify | read | test | create
    content_hash: str   # sha256 of file content at scan time
    scanned_at: str
    status: str         # current | stale | deleted

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "FileRef":
        return cls(**{k: d[k] for k in cls.__dataclass_fields__})
```

- [ ] **Step 4: Run, expect PASS**

- [ ] **Step 5: Commit**

```bash
git add -u
git commit -m "feat(models): add FileRef dataclass for code pointers"
```

---

### Task 2: Extend `ContextPackage` to include `file_refs`

**Files:**
- Modify: `superpowers-plus/skills/memory-management/scripts/models.py`
- Modify: `superpowers-plus/skills/memory-management/tests/test_models.py`

- [ ] **Step 1: Write the failing test**

```python
# Append to tests/test_models.py
def test_context_package_includes_file_refs():
    pkg = ContextPackage(
        node={"id": "x"}, ancestors=[], decisions=[], interfaces=[], deps=[],
        tokens_estimate=100, file_refs=[{"id": "fr-1", "path": "a.py", "status": "current"}],
    )
    d = pkg.to_dict()
    assert len(d["file_refs"]) == 1
    assert d["file_refs"][0]["path"] == "a.py"
```

- [ ] **Step 2: Run, expect FAIL** (ContextPackage doesn't accept `file_refs` yet)

- [ ] **Step 3: Implement**

In `models.py`, add `file_refs` field to `ContextPackage`:
```python
@dataclass
class ContextPackage:
    node: dict[str, Any]
    ancestors: list[dict[str, Any]]
    decisions: list[dict[str, Any]]
    interfaces: list[dict[str, Any]]
    deps: list[dict[str, Any]]
    tokens_estimate: int
    file_refs: list[dict[str, Any]] = field(default_factory=list)
```

Add `from dataclasses import asdict, dataclass, field` import.

- [ ] **Step 4: Run, expect PASS**

- [ ] **Step 5: Commit**

```bash
git add -u
git commit -m "feat(models): extend ContextPackage with file_refs"
```

---

## Chunk 2: Store Protocol — FileRef CRUD

### Task 3: Add FileRef methods to `MemoryStore` Protocol + `InMemoryStore`

**Files:**
- Modify: `superpowers-plus/skills/memory-management/scripts/store.py`
- Create: `superpowers-plus/skills/memory-management/tests/test_file_ref_store.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_file_ref_store.py
import pytest
from models import FileRef, Node
from store import InMemoryStore

@pytest.fixture
def store_with_node():
    s = InMemoryStore()
    s.create_node(Node(
        id="leaf-1", project="demo", name="leaf", node_type="leaf",
        level=1, description="a leaf", status="leaf", origin="user_stated",
        tokens_estimate=0, created_at="t", updated_at="t",
    ))
    return s

def test_add_and_list_file_refs(store_with_node):
    s = store_with_node
    fr = FileRef(id="fr-1", node_id="leaf-1", path="src/a.py", lines="1-50",
                 role="modify", content_hash="abc", scanned_at="t", status="current")
    s.add_file_ref(fr)
    refs = s.list_file_refs("demo", "leaf-1")
    assert len(refs) == 1
    assert refs[0].path == "src/a.py"

def test_update_file_ref_status(store_with_node):
    s = store_with_node
    fr = FileRef(id="fr-1", node_id="leaf-1", path="src/a.py", lines="*",
                 role="read", content_hash="abc", scanned_at="t", status="current")
    s.add_file_ref(fr)
    s.update_file_ref("fr-1", status="stale", content_hash="def")
    refs = s.list_file_refs("demo", "leaf-1")
    assert refs[0].status == "stale"
    assert refs[0].content_hash == "def"

def test_delete_file_ref(store_with_node):
    s = store_with_node
    fr = FileRef(id="fr-1", node_id="leaf-1", path="src/a.py", lines="*",
                 role="read", content_hash="abc", scanned_at="t", status="current")
    s.add_file_ref(fr)
    s.delete_file_ref("fr-1")
    assert s.list_file_refs("demo", "leaf-1") == []

def test_check_file_refs_returns_stale(store_with_node):
    s = store_with_node
    fr1 = FileRef(id="fr-1", node_id="leaf-1", path="src/a.py", lines="*",
                  role="modify", content_hash="abc", scanned_at="t", status="current")
    fr2 = FileRef(id="fr-2", node_id="leaf-1", path="src/b.py", lines="*",
                  role="read", content_hash="abc", scanned_at="t", status="stale")
    s.add_file_ref(fr1)
    s.add_file_ref(fr2)
    report = s.check_file_refs("demo", "leaf-1")
    assert report["total"] == 2
    assert report["stale"] == 1
    assert report["stale_paths"] == ["src/b.py"]
```

- [ ] **Step 2: Run, expect FAIL**

```bash
uv run pytest tests/test_file_ref_store.py -v
```

- [ ] **Step 3: Add to Protocol + implement in InMemoryStore**

Protocol additions in `store.py`:
```python
class MemoryStore(Protocol):
    # ... existing methods ...
    def add_file_ref(self, file_ref: "FileRef") -> None: ...
    def list_file_refs(self, project: str, node_id: str) -> list["FileRef"]: ...
    def update_file_ref(self, file_ref_id: str, **fields) -> "FileRef": ...
    def delete_file_ref(self, file_ref_id: str) -> None: ...
    def check_file_refs(self, project: str, node_id: str) -> dict: ...
```

InMemoryStore implementation:
```python
def __init__(self):
    # ... existing ...
    self._file_refs: list[FileRef] = []

def add_file_ref(self, file_ref: FileRef) -> None:
    self._file_refs.append(file_ref)

def list_file_refs(self, project: str, node_id: str) -> list[FileRef]:
    # node_id links to project via self._nodes
    return [fr for fr in self._file_refs if fr.node_id == node_id]

def update_file_ref(self, file_ref_id: str, **fields) -> FileRef:
    for fr in self._file_refs:
        if fr.id == file_ref_id:
            for k, v in fields.items():
                setattr(fr, k, v)
            return fr
    raise StoreError(f"file_ref not found: {file_ref_id}")

def delete_file_ref(self, file_ref_id: str) -> None:
    self._file_refs = [fr for fr in self._file_refs if fr.id != file_ref_id]

def check_file_refs(self, project: str, node_id: str) -> dict:
    refs = self.list_file_refs(project, node_id)
    stale = [fr for fr in refs if fr.status == "stale"]
    return {
        "total": len(refs),
        "current": len(refs) - len(stale),
        "stale": len(stale),
        "stale_paths": [fr.path for fr in stale],
    }
```

- [ ] **Step 4: Run, expect PASS**

- [ ] **Step 5: Commit**

```bash
git add -u && git add tests/test_file_ref_store.py
git commit -m "feat(store): add FileRef CRUD to Protocol + InMemoryStore"
```

---

### Task 4: Add FileRef methods to `CozoStore`

**Files:**
- Modify: `superpowers-plus/skills/memory-management/scripts/cozo_store.py`
- Modify: `superpowers-plus/skills/memory-management/tests/test_file_ref_store.py`

- [ ] **Step 1: Extend test_file_ref_store.py with a CozoStore parametrize**

Follow the same pattern as `test_store_protocol_compliance.py`: parametrize the fixture to run against both InMemoryStore and CozoStore.

```python
# Add at top of test_file_ref_store.py
import pytest
from cozo_store import CozoStore
from store import InMemoryStore

@pytest.fixture(params=["memory", "cozo"])
def store_with_node(request, tmp_path):
    if request.param == "memory":
        s = InMemoryStore()
    else:
        s = CozoStore(db_path=str(tmp_path / "test.cozo"), embedding_provider=None)
        s.ensure_schema()
    s.create_node(Node(
        id="leaf-1", project="demo", name="leaf", node_type="leaf",
        level=1, description="a leaf", status="leaf", origin="user_stated",
        tokens_estimate=0, created_at="t", updated_at="t",
    ))
    return s
```

- [ ] **Step 2: Run, expect FAIL for cozo param**

```bash
uv run pytest tests/test_file_ref_store.py -v
```

- [ ] **Step 3: Implement CozoStore FileRef methods**

CozoStore — `ensure_schema()` already creates `file_ref` relation (from M1 schema). Implement the 5 methods using Datalog:

```python
def add_file_ref(self, file_ref: FileRef) -> None:
    self._run("""
        ?[id, node_id, path, lines, role, content_hash, scanned_at, status] <- [[
            $id, $node_id, $path, $lines, $role, $hash, $scanned, $status
        ]]
        :put file_ref {id, node_id, path, lines, role, content_hash, scanned_at, status}
    """, {
        "id": file_ref.id, "node_id": file_ref.node_id,
        "path": file_ref.path, "lines": file_ref.lines,
        "role": file_ref.role, "hash": file_ref.content_hash,
        "scanned": file_ref.scanned_at, "status": file_ref.status,
    })

def list_file_refs(self, project: str, node_id: str) -> list[FileRef]:
    rows = self._run("""
        ?[id, node_id, path, lines, role, content_hash, scanned_at, status] :=
            *file_ref{id, node_id, path, lines, role, content_hash, scanned_at, status},
            node_id = $nid
    """, {"nid": node_id})
    return [FileRef(*row) for row in rows]

def update_file_ref(self, file_ref_id: str, **fields) -> FileRef:
    # Read current, merge fields, put back
    rows = self._run("""
        ?[id, node_id, path, lines, role, content_hash, scanned_at, status] :=
            *file_ref{id, node_id, path, lines, role, content_hash, scanned_at, status},
            id = $id
    """, {"id": file_ref_id})
    if not rows:
        raise StoreError(f"file_ref not found: {file_ref_id}")
    current = FileRef(*rows[0])
    for k, v in fields.items():
        setattr(current, k, v)
    self.add_file_ref(current)  # :put is upsert
    return current

def delete_file_ref(self, file_ref_id: str) -> None:
    self._run("""
        ?[id] <- [[$id]]
        :rm file_ref {id}
    """, {"id": file_ref_id})

def check_file_refs(self, project: str, node_id: str) -> dict:
    refs = self.list_file_refs(project, node_id)
    stale = [fr for fr in refs if fr.status == "stale"]
    return {
        "total": len(refs),
        "current": len(refs) - len(stale),
        "stale": len(stale),
        "stale_paths": [fr.path for fr in stale],
    }
```

- [ ] **Step 4: Run, expect PASS for both params**

- [ ] **Step 5: Commit**

```bash
git add -u
git commit -m "feat(cozo-store): implement FileRef CRUD in CozoStore"
```

---

## Chunk 3: Git Utilities

### Task 5: Create `git_utils.py` — git diff/log helpers

**Files:**
- Create: `superpowers-plus/skills/memory-management/scripts/git_utils.py`
- Create: `superpowers-plus/skills/memory-management/tests/test_git_utils.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_git_utils.py
import subprocess
from pathlib import Path
from git_utils import git_head_sha, git_changed_files, compute_file_hash

def _init_repo(tmp_path: Path) -> Path:
    """Create a git repo with one committed file."""
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "t@t.com"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=tmp_path, check=True, capture_output=True)
    (tmp_path / "a.py").write_text("print('hello')\n")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=tmp_path, check=True, capture_output=True)
    return tmp_path

def test_git_head_sha(tmp_path):
    repo = _init_repo(tmp_path)
    sha = git_head_sha(repo)
    assert len(sha) == 40

def test_git_changed_files_after_edit(tmp_path):
    repo = _init_repo(tmp_path)
    first_sha = git_head_sha(repo)
    (repo / "a.py").write_text("print('changed')\n")
    (repo / "b.py").write_text("new file\n")
    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "edit"], cwd=repo, check=True, capture_output=True)
    changed = git_changed_files(repo, first_sha)
    assert "a.py" in changed
    assert "b.py" in changed

def test_git_changed_files_same_commit(tmp_path):
    repo = _init_repo(tmp_path)
    sha = git_head_sha(repo)
    changed = git_changed_files(repo, sha)
    assert changed == []

def test_compute_file_hash(tmp_path):
    f = tmp_path / "x.txt"
    f.write_text("hello")
    h = compute_file_hash(f)
    assert len(h) == 64  # sha256 hex
    # Same content = same hash
    f2 = tmp_path / "y.txt"
    f2.write_text("hello")
    assert compute_file_hash(f2) == h
```

- [ ] **Step 2: Run, expect FAIL**

```bash
uv run pytest tests/test_git_utils.py -v
```

- [ ] **Step 3: Implement**

```python
# scripts/git_utils.py
"""Git integration helpers for pyramid memory freshness tracking."""
from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path


def git_head_sha(project_root: Path) -> str:
    """Return the current HEAD commit SHA."""
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=project_root, capture_output=True, text=True, check=True,
    )
    return result.stdout.strip()


def git_changed_files(project_root: Path, since_commit: str) -> list[str]:
    """Return list of files changed since a given commit (relative paths)."""
    result = subprocess.run(
        ["git", "diff", "--name-only", since_commit, "HEAD"],
        cwd=project_root, capture_output=True, text=True, check=True,
    )
    return [line for line in result.stdout.strip().splitlines() if line]


def compute_file_hash(file_path: Path) -> str:
    """SHA-256 hash of file contents."""
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()
```

- [ ] **Step 4: Run, expect PASS**

- [ ] **Step 5: Commit**

```bash
git add scripts/git_utils.py tests/test_git_utils.py
git commit -m "feat(memory-cli): add git_utils for freshness tracking"
```

---

## Chunk 4: Config Extension — `[scan]` Section

### Task 6: Extend `Config` with `[scan]` section

**Files:**
- Modify: `superpowers-plus/skills/memory-management/scripts/config.py`
- Modify: `superpowers-plus/skills/memory-management/tests/test_config.py`

- [ ] **Step 1: Write the failing test**

```python
# Append to tests/test_config.py
def test_config_scan_section(tmp_path):
    path = tmp_path / "config.toml"
    cfg = Config(
        initialized=True,
        default_project="demo",
        scan_last_commit="abc123",
        scan_project_root="/home/user/project",
    )
    save_config(path, cfg)
    loaded = load_config(path)
    assert loaded.scan_last_commit == "abc123"
    assert loaded.scan_project_root == "/home/user/project"
```

- [ ] **Step 2: Run, expect FAIL**

- [ ] **Step 3: Implement**

Add to `Config` dataclass:
```python
@dataclass
class Config:
    embedding_provider: str = "skip"
    db_path: str = str(PYRAMID_MEMORY_DIR / "data.cozo")
    default_project: Optional[str] = None
    initialized: bool = False
    scan_last_commit: Optional[str] = None
    scan_project_root: Optional[str] = None
```

Update `load_config` to read `[scan]` section:
```python
    scan = data.get("scan", {})
    return Config(
        # ... existing ...
        scan_last_commit=scan.get("last_commit"),
        scan_project_root=scan.get("project_root"),
    )
```

Update `save_config` to write `[scan]` section:
```python
    if cfg.scan_last_commit or cfg.scan_project_root:
        lines.append("")
        lines.append("[scan]")
        if cfg.scan_last_commit:
            lines.append(f'last_commit = "{cfg.scan_last_commit}"')
        if cfg.scan_project_root:
            lines.append(f'project_root = "{cfg.scan_project_root}"')
```

- [ ] **Step 4: Run, expect PASS**

- [ ] **Step 5: Commit**

```bash
git add -u
git commit -m "feat(config): add [scan] section for freshness tracking"
```

---

## Chunk 5: CLI Commands — `file-ref`, `freshness`, `refresh`

### Task 7: Add `file-ref add/list/check` CLI commands

**Files:**
- Modify: `superpowers-plus/skills/memory-management/scripts/memory_cli.py`
- Create: `superpowers-plus/skills/memory-management/tests/test_cli_file_ref.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_cli_file_ref.py
import json

def test_file_ref_add_and_list(run_cli):
    run_cli("init", "--project", "demo", "--embedding", "skip", "--non-interactive")
    run_cli("node", "create", "--id", "leaf-1", "--name", "leaf", "--type", "leaf",
            "--level", "1", "--description", "a leaf", "--origin", "user_stated")
    # Add a file-ref
    r = run_cli("file-ref", "add", "--id", "fr-1", "--node", "leaf-1",
                "--path", "src/a.py", "--lines", "1-50", "--role", "modify",
                "--content-hash", "abc123")
    assert json.loads(r.stdout)["ok"]
    # List
    r = run_cli("file-ref", "list", "--node", "leaf-1")
    refs = json.loads(r.stdout)["data"]["file_refs"]
    assert len(refs) == 1
    assert refs[0]["path"] == "src/a.py"
    assert refs[0]["status"] == "current"

def test_file_ref_check_reports_stale(run_cli):
    run_cli("init", "--project", "demo", "--embedding", "skip", "--non-interactive")
    run_cli("node", "create", "--id", "leaf-1", "--name", "leaf", "--type", "leaf",
            "--level", "1", "--description", "a leaf", "--origin", "user_stated")
    run_cli("file-ref", "add", "--id", "fr-1", "--node", "leaf-1",
            "--path", "src/a.py", "--lines", "*", "--role", "modify",
            "--content-hash", "abc", "--status", "stale")
    run_cli("file-ref", "add", "--id", "fr-2", "--node", "leaf-1",
            "--path", "src/b.py", "--lines", "*", "--role", "read",
            "--content-hash", "def")
    r = run_cli("file-ref", "check", "--node", "leaf-1")
    report = json.loads(r.stdout)["data"]
    assert report["total"] == 2
    assert report["stale"] == 1
    assert "src/a.py" in report["stale_paths"]
```

- [ ] **Step 2: Run, expect FAIL**

```bash
uv run pytest tests/test_cli_file_ref.py -v
```

- [ ] **Step 3: Implement CLI commands**

Add a `file_ref` group to `memory_cli.py`:

```python
@cli.group("file-ref")
def file_ref_group():
    """Manage code file references attached to nodes."""
    pass

@file_ref_group.command("add")
@click.option("--id", "ref_id", required=True)
@click.option("--node", "node_id", required=True)
@click.option("--path", "file_path", required=True)
@click.option("--lines", default="*")
@click.option("--role", required=True, type=click.Choice(["modify", "read", "test", "create"]))
@click.option("--content-hash", required=True)
@click.option("--status", default="current", type=click.Choice(["current", "stale", "deleted"]))
@click.option("--project")
def file_ref_add(ref_id, node_id, file_path, lines, role, content_hash, status, project):
    s, cfg = _store()
    p = _project(project, cfg)
    fr = FileRef(
        id=ref_id, node_id=node_id, path=file_path, lines=lines,
        role=role, content_hash=content_hash, scanned_at=_now(), status=status,
    )
    s.add_file_ref(fr)
    emit({"file_ref_id": ref_id})

@file_ref_group.command("list")
@click.option("--node", "node_id", required=True)
@click.option("--project")
def file_ref_list(node_id, project):
    s, cfg = _store()
    p = _project(project, cfg)
    refs = s.list_file_refs(p, node_id)
    emit({"file_refs": [fr.to_dict() for fr in refs]})

@file_ref_group.command("check")
@click.option("--node", "node_id", required=True)
@click.option("--project")
def file_ref_check(node_id, project):
    s, cfg = _store()
    p = _project(project, cfg)
    report = s.check_file_refs(p, node_id)
    emit(report)
```

- [ ] **Step 4: Run, expect PASS**

- [ ] **Step 5: Commit**

```bash
git add -u && git add tests/test_cli_file_ref.py
git commit -m "feat(memory-cli): add file-ref add/list/check commands"
```

---

### Task 8: Add `memory freshness` command

**Files:**
- Modify: `superpowers-plus/skills/memory-management/scripts/memory_cli.py`
- Create: `superpowers-plus/skills/memory-management/tests/test_cli_freshness.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_cli_freshness.py
import json
import subprocess
from pathlib import Path

def _init_git_repo(path: Path):
    subprocess.run(["git", "init"], cwd=path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "t@t.com"], cwd=path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=path, check=True, capture_output=True)
    (path / "a.py").write_text("x = 1\n")
    subprocess.run(["git", "add", "."], cwd=path, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=path, check=True, capture_output=True)

def test_memory_freshness_no_changes(run_cli_with_workspace, tmp_path):
    """When last_commit == HEAD, freshness reports 'fresh'."""
    _init_git_repo(tmp_path)
    cli = run_cli_with_workspace(tmp_path)
    cli("init", "--project", "demo", "--embedding", "skip", "--non-interactive")
    # Store current HEAD as last_commit
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=tmp_path,
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    cli("config", "set", "--key", "scan.last_commit", "--value", head)
    cli("config", "set", "--key", "scan.project_root", "--value", str(tmp_path))
    r = cli("memory", "freshness")
    data = json.loads(r.stdout)["data"]
    assert data["status"] == "fresh"
    assert data["changed_files"] == []

def test_memory_freshness_with_changes(run_cli_with_workspace, tmp_path):
    """After new commits, freshness reports changed files."""
    _init_git_repo(tmp_path)
    head_before = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=tmp_path,
        capture_output=True, text=True, check=True,
    ).stdout.strip()

    cli = run_cli_with_workspace(tmp_path)
    cli("init", "--project", "demo", "--embedding", "skip", "--non-interactive")
    cli("config", "set", "--key", "scan.last_commit", "--value", head_before)
    cli("config", "set", "--key", "scan.project_root", "--value", str(tmp_path))

    # Make changes
    (tmp_path / "a.py").write_text("x = 2\n")
    (tmp_path / "b.py").write_text("new\n")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "edit"], cwd=tmp_path, check=True, capture_output=True)

    r = cli("memory", "freshness")
    data = json.loads(r.stdout)["data"]
    assert data["status"] == "stale"
    assert "a.py" in data["changed_files"]
    assert "b.py" in data["changed_files"]

def test_memory_freshness_no_scan_config(run_cli):
    """When scan config is missing, freshness reports 'unknown'."""
    run_cli("init", "--project", "demo", "--embedding", "skip", "--non-interactive")
    r = run_cli("memory", "freshness")
    data = json.loads(r.stdout)["data"]
    assert data["status"] == "unknown"
```

- [ ] **Step 2: Run, expect FAIL**

```bash
uv run pytest tests/test_cli_freshness.py -v
```

- [ ] **Step 3: Implement**

```python
@memory.command("freshness")
@click.option("--project")
def memory_freshness(project):
    """Compare last_scan_commit vs git HEAD, report stale status."""
    s, cfg = _store()
    p = _project(project, cfg)

    if not cfg.scan_last_commit or not cfg.scan_project_root:
        emit({"status": "unknown", "reason": "no scan config", "changed_files": []})
        return

    from pathlib import Path
    from git_utils import git_head_sha, git_changed_files

    project_root = Path(cfg.scan_project_root)
    current_head = git_head_sha(project_root)
    if current_head == cfg.scan_last_commit:
        emit({"status": "fresh", "last_commit": cfg.scan_last_commit,
              "head": current_head, "changed_files": []})
        return

    changed = git_changed_files(project_root, cfg.scan_last_commit)
    emit({
        "status": "stale",
        "last_commit": cfg.scan_last_commit,
        "head": current_head,
        "changed_files": changed,
        "changed_count": len(changed),
    })
```

Note: The test uses a `run_cli_with_workspace` fixture that sets `--workspace-root`. Add this fixture in `conftest.py` if not already present.

- [ ] **Step 4: Run, expect PASS**

- [ ] **Step 5: Commit**

```bash
git add -u && git add tests/test_cli_freshness.py
git commit -m "feat(memory-cli): add memory freshness command"
```

---

### Task 9: Add `memory refresh` command

**Files:**
- Modify: `superpowers-plus/skills/memory-management/scripts/memory_cli.py`
- Create: `superpowers-plus/skills/memory-management/tests/test_cli_refresh.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_cli_refresh.py
import json
import subprocess
from pathlib import Path

def _init_git_repo(path: Path):
    subprocess.run(["git", "init"], cwd=path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "t@t.com"], cwd=path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=path, check=True, capture_output=True)
    (path / "src").mkdir()
    (path / "src" / "a.py").write_text("x = 1\n")
    subprocess.run(["git", "add", "."], cwd=path, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=path, check=True, capture_output=True)

def test_memory_refresh_marks_stale(run_cli_with_workspace, tmp_path):
    """refresh marks file_refs whose files changed as stale and updates last_commit."""
    _init_git_repo(tmp_path)
    head_before = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=tmp_path,
        capture_output=True, text=True, check=True,
    ).stdout.strip()

    cli = run_cli_with_workspace(tmp_path)
    cli("init", "--project", "demo", "--embedding", "skip", "--non-interactive")
    cli("config", "set", "--key", "scan.last_commit", "--value", head_before)
    cli("config", "set", "--key", "scan.project_root", "--value", str(tmp_path))
    cli("node", "create", "--id", "leaf-1", "--name", "leaf", "--type", "leaf",
        "--level", "1", "--description", "d", "--origin", "user_stated")
    cli("file-ref", "add", "--id", "fr-1", "--node", "leaf-1",
        "--path", "src/a.py", "--lines", "*", "--role", "modify",
        "--content-hash", "old_hash")

    # Change the file and commit
    (tmp_path / "src" / "a.py").write_text("x = 2\n")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "edit"], cwd=tmp_path, check=True, capture_output=True)

    r = cli("memory", "refresh")
    data = json.loads(r.stdout)["data"]
    assert data["marked_stale"] == 1
    assert "src/a.py" in data["stale_paths"]

    # Verify file-ref is now stale
    r2 = cli("file-ref", "check", "--node", "leaf-1")
    assert json.loads(r2.stdout)["data"]["stale"] == 1

    # Verify last_commit was updated
    r3 = cli("config", "show")
    cfg_data = json.loads(r3.stdout)["data"]
    new_head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=tmp_path,
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    assert cfg_data.get("scan_last_commit") == new_head or cfg_data.get("scan", {}).get("last_commit") == new_head
```

- [ ] **Step 2: Run, expect FAIL**

```bash
uv run pytest tests/test_cli_refresh.py -v
```

- [ ] **Step 3: Implement**

```python
@memory.command("refresh")
@click.option("--project")
def memory_refresh(project):
    """Git-diff based incremental stale-marking. Updates scan.last_commit after."""
    s, cfg = _store()
    p = _project(project, cfg)

    if not cfg.scan_last_commit or not cfg.scan_project_root:
        emit_error("no scan config — run freshness first or set scan.last_commit + scan.project_root",
                   code="no_scan_config")
        return

    from pathlib import Path
    from git_utils import git_head_sha, git_changed_files

    project_root = Path(cfg.scan_project_root)
    current_head = git_head_sha(project_root)
    if current_head == cfg.scan_last_commit:
        emit({"marked_stale": 0, "stale_paths": [], "message": "already fresh"})
        return

    changed_files = set(git_changed_files(project_root, cfg.scan_last_commit))

    # Walk all nodes, check their file_refs against changed_files
    marked_stale = 0
    stale_paths = []
    for node in s.list_nodes(p):
        for fr in s.list_file_refs(p, node.id):
            if fr.status == "current" and fr.path in changed_files:
                s.update_file_ref(fr.id, status="stale", scanned_at=_now())
                marked_stale += 1
                stale_paths.append(fr.path)

    # Update config with new HEAD
    cfg.scan_last_commit = current_head
    save_config(_config_path(), cfg)

    emit({
        "marked_stale": marked_stale,
        "stale_paths": stale_paths,
        "new_last_commit": current_head,
    })
```

- [ ] **Step 4: Run, expect PASS**

- [ ] **Step 5: Commit**

```bash
git add -u && git add tests/test_cli_refresh.py
git commit -m "feat(memory-cli): add memory refresh command for incremental stale-marking"
```

---

## Chunk 6: Extended `assemble_context` with File Refs

### Task 10: Extend `assemble_context` to include `file_refs` with stale warnings

**Files:**
- Modify: `superpowers-plus/skills/memory-management/scripts/store.py`
- Modify: `superpowers-plus/skills/memory-management/scripts/cozo_store.py`
- Create: `superpowers-plus/skills/memory-management/tests/test_context_with_file_refs.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_context_with_file_refs.py
import pytest
from models import FileRef, Node
from store import InMemoryStore

@pytest.fixture
def store_with_refs():
    s = InMemoryStore()
    s.create_node(Node(
        id="root", project="demo", name="root", node_type="root",
        level=0, description="r", status="done", origin="user_stated",
        tokens_estimate=0, created_at="t", updated_at="t",
    ))
    s.create_node(Node(
        id="leaf-1", project="demo", name="leaf", node_type="leaf",
        level=1, description="a leaf", status="leaf", origin="user_stated",
        tokens_estimate=0, created_at="t", updated_at="t",
    ))
    from models import Edge
    s.add_edge(Edge(kind="hierarchy", from_id="root", to_id="leaf-1"))
    s.add_file_ref(FileRef(
        id="fr-1", node_id="leaf-1", path="src/a.py", lines="1-50",
        role="modify", content_hash="abc", scanned_at="t", status="current",
    ))
    s.add_file_ref(FileRef(
        id="fr-2", node_id="leaf-1", path="src/b.py", lines="*",
        role="read", content_hash="def", scanned_at="t", status="stale",
    ))
    return s

def test_assemble_context_includes_file_refs(store_with_refs):
    pkg = store_with_refs.assemble_context("demo", "leaf-1")
    assert len(pkg.file_refs) == 2
    stale = [fr for fr in pkg.file_refs if fr.get("status") == "stale"]
    assert len(stale) == 1
    assert stale[0]["path"] == "src/b.py"

def test_assemble_context_tokens_include_file_ref_chars(store_with_refs):
    pkg = store_with_refs.assemble_context("demo", "leaf-1")
    # tokens_estimate should be > 0 and should account for file_ref data
    assert pkg.tokens_estimate > 0

def test_assemble_context_stale_ref_has_warning(store_with_refs):
    pkg = store_with_refs.assemble_context("demo", "leaf-1")
    stale_ref = [fr for fr in pkg.file_refs if fr["path"] == "src/b.py"][0]
    assert "warning" in stale_ref
    assert "stale" in stale_ref["warning"].lower()
```

- [ ] **Step 2: Run, expect FAIL**

- [ ] **Step 3: Implement**

In `InMemoryStore.assemble_context`, add after existing code:

```python
    # Gather file_refs for the leaf
    file_refs_raw = self.list_file_refs(project, leaf_id)
    file_refs = []
    for fr in file_refs_raw:
        d = fr.to_dict()
        if fr.status == "stale":
            d["warning"] = f"STALE: {fr.path} has changed since last scan. Re-read before modifying."
        file_refs.append(d)

    # Include file_ref chars in token estimate
    file_ref_chars = sum(len(fr.path) + len(fr.lines) + len(fr.role) for fr in file_refs_raw)
    total_chars += file_ref_chars

    return ContextPackage(
        node=leaf.to_dict(),
        ancestors=ancestors,
        decisions=decisions,
        interfaces=interfaces,
        deps=[{"id": d["id"], "name": d["name"], "status": d["status"]} for d in deps],
        tokens_estimate=total_chars // 4,
        file_refs=file_refs,
    )
```

Apply same change to `CozoStore.assemble_context`.

- [ ] **Step 4: Run, expect PASS**

- [ ] **Step 5: Commit**

```bash
git add -u && git add tests/test_context_with_file_refs.py
git commit -m "feat(store): assemble_context includes file_refs with stale warnings"
```

---

## Chunk 7: Auto-Trigger Protocol Integration Test

### Task 11: Auto-trigger protocol integration test

Proves the end-to-end flow: freshness check → detect stale → refresh → file_refs marked stale → assemble_context warns subagent.

**Files:**
- Create: `superpowers-plus/skills/memory-management/tests/test_auto_trigger_protocol.py`

- [ ] **Step 1: Write the test**

```python
# tests/test_auto_trigger_protocol.py
"""
Prove the auto-trigger protocol works end-to-end:
1. Session starts → freshness check → "stale"
2. refresh → marks file_refs stale
3. assemble_context → includes stale warnings
This is the flow the LLM executes at session start.
"""
import json
import subprocess
from pathlib import Path

def _init_repo(path):
    subprocess.run(["git", "init"], cwd=path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "t@t.com"], cwd=path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=path, check=True, capture_output=True)
    (path / "src").mkdir()
    (path / "src" / "payment.py").write_text("class Payment: pass\n")
    subprocess.run(["git", "add", "."], cwd=path, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=path, check=True, capture_output=True)

def test_auto_trigger_full_cycle(run_cli_with_workspace, tmp_path):
    repo = tmp_path
    _init_repo(repo)
    head_v1 = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo,
        capture_output=True, text=True, check=True,
    ).stdout.strip()

    cli = run_cli_with_workspace(repo)
    cli("init", "--project", "demo", "--embedding", "skip", "--non-interactive")
    cli("config", "set", "--key", "scan.last_commit", "--value", head_v1)
    cli("config", "set", "--key", "scan.project_root", "--value", str(repo))

    # Create a node with file-ref pointing at payment.py
    cli("node", "create", "--id", "root", "--name", "root", "--type", "root",
        "--level", "0", "--description", "r", "--origin", "user_stated")
    cli("node", "create", "--id", "pay-leaf", "--name", "payment", "--type", "leaf",
        "--level", "1", "--description", "payment module", "--origin", "user_stated")
    cli("edge", "add", "--kind", "hierarchy", "--from", "root", "--to", "pay-leaf")
    cli("file-ref", "add", "--id", "fr-pay", "--node", "pay-leaf",
        "--path", "src/payment.py", "--lines", "*", "--role", "modify",
        "--content-hash", "original_hash")

    # === Simulate code change between sessions ===
    (repo / "src" / "payment.py").write_text("class Payment:\n    def charge(self): ...\n")
    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "add charge method"], cwd=repo, check=True, capture_output=True)

    # === LLM session start: Step 1 — freshness check ===
    r = cli("memory", "freshness")
    freshness = json.loads(r.stdout)["data"]
    assert freshness["status"] == "stale"
    assert "src/payment.py" in freshness["changed_files"]

    # === LLM session start: Step 2 — refresh ===
    r = cli("memory", "refresh")
    refresh = json.loads(r.stdout)["data"]
    assert refresh["marked_stale"] == 1
    assert "src/payment.py" in refresh["stale_paths"]

    # === LLM working: Step 3 — assemble_context for subagent ===
    r = cli("memory", "context", "--node", "pay-leaf")
    ctx = json.loads(r.stdout)["data"]
    assert len(ctx["file_refs"]) == 1
    fr = ctx["file_refs"][0]
    assert fr["status"] == "stale"
    assert "warning" in fr
    assert "stale" in fr["warning"].lower()
```

- [ ] **Step 2: Run, expect PASS**

```bash
uv run pytest tests/test_auto_trigger_protocol.py -v
```

- [ ] **Step 3: Commit**

```bash
git add tests/test_auto_trigger_protocol.py
git commit -m "test(memory-cli): auto-trigger protocol integration test"
```

---

## Chunk 8: `config set` Command (prerequisite)

### Task 12: Add `config set` CLI command

The freshness/refresh tests depend on `config set --key scan.last_commit --value X`. If this command doesn't exist yet, it needs to be added.

**Files:**
- Modify: `superpowers-plus/skills/memory-management/scripts/memory_cli.py`
- Modify: `superpowers-plus/skills/memory-management/tests/test_config.py` (or `test_cli_config.py`)

- [ ] **Step 1: Check if `config set` exists**

If it already exists, skip this task entirely. If not:

- [ ] **Step 2: Write the failing test**

```python
def test_config_set_dotted_key(run_cli):
    run_cli("init", "--project", "demo", "--embedding", "skip", "--non-interactive")
    r = run_cli("config", "set", "--key", "scan.last_commit", "--value", "abc123")
    assert json.loads(r.stdout)["ok"]
    r2 = run_cli("config", "show")
    # Verify the key was persisted (exact structure depends on config show output)
```

- [ ] **Step 3: Implement**

```python
@config_group.command("set")
@click.option("--key", required=True, help="Dotted key like 'scan.last_commit'")
@click.option("--value", required=True)
def config_set(key, value):
    """Set a config value by dotted key."""
    cfg = _load()
    parts = key.split(".")
    if len(parts) == 2:
        section, field = parts
        attr = f"{section}_{field}"
        if hasattr(cfg, attr):
            setattr(cfg, attr, value)
        else:
            emit_error(f"unknown config key: {key}", code="unknown_key")
            return
    elif len(parts) == 1:
        if hasattr(cfg, key):
            setattr(cfg, key, value)
        else:
            emit_error(f"unknown config key: {key}", code="unknown_key")
            return
    else:
        emit_error(f"unsupported key depth: {key}", code="bad_key")
        return

    save_config(_config_path(), cfg)
    emit({"key": key, "value": value})
```

- [ ] **Step 4: Run, expect PASS**

- [ ] **Step 5: Commit**

```bash
git add -u
git commit -m "feat(memory-cli): add config set command for dotted keys"
```

---

## Chunk 9: Skill Files

### Task 13: Create `codebase-exploration` skill

**Files:**
- Create: `superpowers-plus/skills/codebase-exploration/SKILL.md`
- Create: `superpowers-plus/skills/codebase-exploration/exploration-guide.md`

- [ ] **Step 1: Write SKILL.md**

```markdown
---
name: codebase-exploration
description: Auto-triggered by LLM when working on an existing codebase. Scans modules, stores findings as existing_module nodes with file-refs in pyramid memory. Never user-initiated.
---

# Codebase Exploration

## When This Skill Activates

This skill is **auto-triggered**, never user-initiated. It activates when:

1. **Session start**: `memory freshness` returns `unknown` (no prior scan) or `stale` (code changed)
2. **Recall miss**: `memory recall --query "..."` returns 0 results for a concept that should exist in the codebase
3. **User describes a change to an existing system**: LLM recognizes the target system isn't yet mapped in pyramid memory

**DO NOT** ask the user "should I explore the codebase?" — just do it. The user should not need to know this step exists.

## Phase 1 — Freshness Check

At the start of every session where pyramid memory is initialized:

```bash
memory freshness
```

| Result | Action |
|--------|--------|
| `fresh` | Skip to normal workflow |
| `stale` | Run `memory refresh`, then proceed to Phase 2 if new areas need mapping |
| `unknown` | No prior scan. Proceed to Phase 2 for initial exploration |

## Phase 2 — Module Discovery

Scan the project structure to identify top-level modules. Use the LLM's code reading ability — this is NOT a blind `find` command.

Strategy:
1. Read the project's entry points (package.json, setup.py, Cargo.toml, go.mod, etc.)
2. Identify the source directory layout
3. For each major module/package/directory:
   - Read its primary files (index, __init__, mod.rs, etc.)
   - Determine its responsibility in ONE sentence
   - Note key exports/interfaces

For each discovered module:
```bash
node create --id "existing-<module-name>" --name "<module-name>" \
  --type existing_module --level 1 \
  --description "<one-sentence responsibility>" \
  --origin skill_inferred

file-ref add --id "fr-<module>-entry" --node "existing-<module-name>" \
  --path "<entry-file-path>" --lines "*" --role read \
  --content-hash "<sha256>"
```

**Budget**: Spend no more than ~5 minutes on initial exploration. Map the TOP LEVEL only — do not recurse into every subdirectory. Deeper exploration happens on-demand when the user targets a specific area.

## Phase 3 — Stale Refresh

When `memory refresh` marks file-refs as stale:

1. For each stale file-ref on an `existing_module` node:
   - Re-read the file
   - If the module's responsibility changed: update the node description
   - Update `content_hash` via `file-ref add` (upsert)
   - Mark `status: current`
2. For stale file-refs on `change_*` nodes: add a warning to the context package — the subagent will re-read the file

## Phase 4 — On-Demand Deep Dive

When the user targets a specific module for modification:

1. Read beyond the entry point — trace key code paths
2. Add `file-ref` entries for specific files/line ranges the change will touch
3. Note internal dependencies between modules

This phase feeds into `pyramid-decomposition`'s impact-analysis (see that skill).

## Context Budget

Same rules as BFS decomposition — never load more than ~2k tokens of exploration context at a time. Use `--summary` mode for sibling modules. Only load full detail for the module being explored.
```

- [ ] **Step 2: Write exploration-guide.md**

```markdown
# Codebase Exploration Guide

## Module-Scan Strategy

### What to Look For

When scanning an unfamiliar codebase, focus on:

1. **Entry points**: Where does execution start? (main, index, app, server)
2. **Module boundaries**: What are the top-level packages/directories?
3. **Dependency graph**: Which modules import which?
4. **Data flow**: Where does data enter, transform, and exit?
5. **Configuration**: How is the system configured? (env vars, config files)

### What NOT to Do

- Don't read every file
- Don't try to understand implementation details of every module
- Don't map internal functions — only public interfaces
- Don't spend more than ~5 minutes on initial scan

### Node Types for Existing Code

| node_type | When to use |
|-----------|-------------|
| `existing_module` | A module/package that exists in the codebase and may be affected by changes |
| `change_root` | The root of a change tree — "what we're modifying" |
| `change_branch` | A grouping of related changes within the modification |
| `change_leaf` | An atomic change unit — one file/function/component to modify |

### File-Ref Roles

| Role | Meaning |
|------|---------|
| `modify` | This file will be directly edited |
| `read` | This file is read for context only (e.g., an interface the change must conform to) |
| `test` | This is a test file that exercises the changed code |
| `create` | This file doesn't exist yet and will be created |

## Auto-Trigger Protocol

### Session Start

Every session where pyramid memory is initialized:

```
memory freshness → stale? → memory refresh → check for unmapped areas → explore
```

The LLM performs this check SILENTLY. The user sees no output unless something significant changed.

### Recall Miss

If `memory recall --query "payment processing"` returns 0 results but the user is clearly talking about an existing system component:

1. The LLM recognizes the miss
2. Explores the relevant area of the codebase
3. Stores findings as `existing_module` nodes
4. Retries the recall

### Lazy Validation

When `assemble_context` returns a file-ref with `status: stale`:

1. The LLM (or subagent) re-reads the actual file
2. If content matches expectations: update hash, mark `current`
3. If content has diverged: flag to user, update description if needed
```

- [ ] **Step 3: Commit**

```bash
git add superpowers-plus/skills/codebase-exploration/
git commit -m "feat(skill): add codebase-exploration skill for existing project support"
```

---

### Task 14: Add impact-analysis phase to `pyramid-decomposition`

**Files:**
- Modify: `superpowers-plus/skills/pyramid-decomposition/SKILL.md`
- Modify: `superpowers-plus/skills/pyramid-decomposition/decomposition-guide.md`

- [ ] **Step 1: Add Phase 0.5 — Impact Analysis to SKILL.md**

Insert between Phase 0 (Clarify the Goal) and Phase 1 (BFS Decomposition):

```markdown
### Phase 0.5 — Impact Analysis (existing projects only)

**Skip this phase for greenfield projects** (no `existing_module` nodes in memory).

When modifying an existing codebase, the pyramid should decompose THE CHANGE, not the entire system. This phase identifies what the change touches.

#### 0.5.1 Check if existing modules are mapped

```bash
node list --level 1 --summary
```

If no `existing_module` nodes exist, the `codebase-exploration` skill should have run first. If it hasn't, trigger it now (invoke `codebase-exploration` implicitly — do not ask the user).

#### 0.5.2 Identify affected modules

Based on the user's change request + existing module map:
1. Which modules will be MODIFIED?
2. Which modules will be READ (interfaces the change must conform to)?
3. Which modules are UNAFFECTED?

Confirm with user: "This change primarily affects modules A and B, and must conform to C's interface. Modules D, E, F are unaffected. Sound right?"

#### 0.5.3 Create the change tree root

```bash
node create --id "change-<feature>" --name "<feature-name>" \
  --type change_root --level 0 \
  --description "<what is being changed and why>" \
  --origin user_stated
```

Add dependency edges to affected existing modules:
```bash
edge add --kind dependency --from "change-<feature>" --to "existing-<module>" --dep-type affects
```

#### 0.5.4 Attach file-refs

For each affected module, identify specific files:
```bash
file-ref add --id "fr-<file>" --node "change-<feature>" \
  --path "<file-path>" --lines "<line-range>" --role <modify|read|test|create> \
  --content-hash "<sha256>"
```

**Then proceed to Phase 1** — BFS decomposition now decomposes the change tree, not the whole system.
```

- [ ] **Step 2: Add "Existing Projects" section to decomposition-guide.md**

```markdown
---

## Working with Existing Projects

### Decomposing Changes, Not Systems

For existing codebases, the pyramid does NOT represent the entire system. It represents THE CHANGE:

```
change_root: "Add payment retry logic"
├── change_branch: "Retry mechanism"
│   ├── change_leaf: "Add RetryPolicy config"
│   └── change_leaf: "Implement retry loop in PaymentService.charge()"
├── change_branch: "Observability"
│   ├── change_leaf: "Add retry metrics to Prometheus"
│   └── change_leaf: "Update Grafana dashboard config"
└── change_leaf: "Integration tests for retry scenarios"
```

The `existing_module` nodes sit OUTSIDE this tree — they represent the pre-existing codebase that the change interacts with. Link them via `dependency` edges.

### When to Use Which node_type

- Starting a new project from scratch → `root`, `branch`, `leaf`
- Mapping an existing codebase's structure → `existing_module`
- Modifying existing code → `change_root`, `change_branch`, `change_leaf`

### File-Refs as the Bridge

`file-ref` connects the abstract pyramid to concrete code:

- `change_leaf` → `file-ref (role: modify)` → the exact files/lines to edit
- `existing_module` → `file-ref (role: read)` → entry points for context
- `change_leaf` → `file-ref (role: test)` → test files to update/create

When `assemble_context` is called for a `change_leaf`, the subagent receives:
1. The change description
2. Ancestor decisions (why this change was scoped this way)
3. Interface definitions (what the change must conform to)
4. `file_refs` — exact files to read and modify, with stale warnings if code has changed since scan
```

- [ ] **Step 3: Commit**

```bash
git add superpowers-plus/skills/pyramid-decomposition/
git commit -m "feat(skill): add impact-analysis phase + existing-project guidance to pyramid-decomposition"
```

---

## Chunk 10: Protocol Compliance + Full Test

### Task 15: Add FileRef to protocol compliance tests

**Files:**
- Modify: `superpowers-plus/skills/memory-management/tests/test_store_protocol_compliance.py`

- [ ] **Step 1: Add FileRef compliance tests**

Extend the existing parametrized test suite to verify `add_file_ref`, `list_file_refs`, `update_file_ref`, `delete_file_ref`, `check_file_refs` work identically across InMemoryStore and CozoStore.

```python
def test_file_ref_crud(store):
    # ... same tests from Task 3, but running against both impls via parametrize
```

- [ ] **Step 2: Run, expect PASS**

- [ ] **Step 3: Commit**

```bash
git add -u
git commit -m "test(store): add FileRef to protocol compliance suite"
```

---

### Task 16: Run full test suite + tag M4

- [ ] **Step 1: Run all tests**

```bash
cd superpowers-plus/skills/memory-management
uv run pytest -v
```

Expected: All M1 + M2 + M3 + M4 tests PASS.

- [ ] **Step 2: Tag**

```bash
git tag -a m4-existing-projects -m "Milestone 4: existing project support — file-ref, freshness, refresh, codebase-exploration skill, impact-analysis"
```

- [ ] **Step 3: Update spec §11.5**

Add: `**Status: Shipped 2026-MM-DD (tag: m4-existing-projects)**`

- [ ] **Step 4: Commit**

```bash
git add docs/superpowers/specs/2026-04-07-pyramid-memory-skill-design.md
git commit -m "docs: mark Milestone 4 as shipped"
```

---

## Self-Review

### Spec coverage

| Spec M4 scope item | Plan task |
|---|---|
| `FileRef` data model | Task 1, 2 |
| `node_type` extensions (existing_module, change_*) | Task 13 (skill), Task 14 (guide) — types already in schema from M1 |
| `file-ref add/list/check` CLI | Task 7 |
| `memory freshness` CLI | Task 8 |
| `memory refresh` CLI | Task 9 |
| Config `[scan]` section | Task 6 |
| `codebase-exploration` skill | Task 13 |
| Impact-analysis in pyramid-decomposition | Task 14 |
| LLM auto-trigger protocol | Task 13 (SKILL.md), Task 11 (integration test) |
| `assemble_context` extended with file_refs | Task 10 |
| Lazy validation (stale returns warning) | Task 10 |

### Exit criteria mapping

| Criterion | Verified by |
|---|---|
| LLM auto-explores unfamiliar codebase | Task 13 (skill design), Task 11 (integration test proves the CLI flow) |
| `memory refresh` on 50 changed files < 2s | Task 9 (test proves correctness; perf is a manual check — git diff + loop is O(n) and fast) |
| Stale detection after `git commit` | Task 8 (freshness), Task 9 (refresh), Task 11 (end-to-end) |
| `change_leaf`'s context includes file_refs | Task 10 |

### Dependency order

```
Task 1  → Task 2  (FileRef → ContextPackage extension)
Task 3  → Task 4  (InMemoryStore → CozoStore)
Task 5  (independent: git_utils)
Task 6  (independent: config extension)
Task 12 → Task 7  (config set → file-ref CLI)
Task 7  → Task 8  → Task 9  (file-ref → freshness → refresh)
Task 10 (depends on Task 3/4)
Task 11 (depends on Tasks 7-10)
Task 13, 14 (independent: skill files, can parallel with CLI tasks)
Task 15 → Task 16 (compliance → final test + tag)
```

### Task execution order (recommended)

1. Task 1 (FileRef dataclass)
2. Task 2 (ContextPackage extension)
3. Task 5 (git_utils — independent)
4. Task 6 (config extension — independent)
5. Task 3 (FileRef Protocol + InMemoryStore)
6. Task 4 (FileRef CozoStore)
7. Task 12 (config set command — prerequisite for freshness tests)
8. Task 7 (file-ref CLI)
9. Task 8 (memory freshness)
10. Task 9 (memory refresh)
11. Task 10 (assemble_context with file_refs)
12. Task 11 (auto-trigger integration test)
13. Task 13 (codebase-exploration skill)
14. Task 14 (impact-analysis in pyramid-decomposition)
15. Task 15 (protocol compliance)
16. Task 16 (full test + tag)
