# Pyramid Memory Skill Design

**Date**: 2026-04-07
**Status**: Draft (pending self-review + user review)
**Form factor**: Two new skills inside the `superpowers-plus` plugin
**Authors**: brainstormed with user

---

## 1. Problem & Goals

### Three core problems
1. **大型工程上下文崩溃** — Single-context windows cannot hold a full system's design + code + decisions. Subagents repeatedly re-derive context. Decisions evaporate between sessions.
2. **用户无法结构化清楚地描述需求设计** — Users start with fuzzy requirements ("做一个 XX 系统"). They cannot articulate complete designs upfront, and ad-hoc Q&A produces inconsistent, incomplete specs that later cause rework.
3. **职责拆分不够细，解耦不好** — Without a forcing function, decomposition stops too early: leaves are too coarse, responsibilities overlap, hidden coupling sneaks in. Subagents then collide on shared state and produce code that won't compose.

### Goals (mapped to problems)
1. **Pyramid decomposition with enforced independence criteria** — solves #2 + #3. The skill drives an interactive top-down clarification flow where each split must pass 5 independence checks before being accepted. Users don't write specs; they answer micro-questions and the pyramid emerges. Coarse leaves are rejected by the criteria, forcing finer cuts until coupling disappears.
2. **Persistent memory across sessions** — solves #1. Store nodes, decisions, interfaces, and dependencies. Retrieve the *minimum sufficient* context per leaf so each subagent works from a self-contained package.
3. **Pluggable backend** — `MemoryStore` Protocol so the storage engine can be swapped without touching skill logic.
4. **Skill-plugin form factor** — ship as part of `superpowers-plus`, not a standalone service.
5. **Cross-harness** — Claude Code, Codex CLI/App, OpenCode, Cursor, Windsurf, Gemini CLI, Copilot CLI.
6. **Zero-friction install** — one hard dependency (`uv`); all Python deps managed by PEP 723 inline metadata; no global pip pollution.

### How each problem is concretely addressed

| Problem | Mechanism | Where in spec |
|---|---|---|
| 上下文崩溃 | `memory context --node <leaf>` returns minimum sufficient package; CozoDB stores everything; cross-session persistence | §3, §4, §6 |
| 需求描述不清 | `pyramid-decomposition` skill conducts top-down interactive clarification; each level asks targeted questions; users never write a spec, they confirm splits | §6 Phase 1 |
| 拆分不细 / 解耦差 | 5 independence criteria must pass before a node is marked `leaf`; criteria check single responsibility, interface clarity, testability, token budget, dependency closure; violations force further decomposition | §6, decomposition-guide.md |

### Non-goals
- Not a code-context tool. Code-level context (symbols, references) stays with Serena / LSP-based tools. This skill manages **decision memory + decomposition graph**, which is a separate layer.
- Not a backend service. No FastAPI, no daemon, no MCP server.
- Not opinionated about embedding provider. Embedding is optional.

---

## 2. Approach Overview

Two new skills under `superpowers-plus/skills/`:

```
pyramid-decomposition/   # orchestration: how to break down + when to call memory
└── SKILL.md
└── decomposition-guide.md   # 5 independence criteria, examples

memory-management/       # capability: graph + decision storage CLI
├── SKILL.md
└── scripts/
    ├── memory_cli.py    # PEP 723 entry point
    ├── db.py            # CozoStore(MemoryStore Protocol)
    ├── embedding.py     # EmbeddingProvider implementations
    └── models.py        # dataclasses
```

The LLM is the orchestrator. Python CLI is the executor. SKILL.md tells the LLM **when** to call which CLI command; the CLI does the storage / query / context-assembly work and returns JSON.

---

## 3. Storage Backend: CozoDB

### Why CozoDB
| Need | CozoDB capability |
|---|---|
| Graph (hierarchy + deps) | Native relations + recursive Datalog |
| Vector (semantic recall) | Built-in HNSW index |
| Embedded (no server) | SQLite backend, single file |
| Single query for graph + vector | Datalog can join HNSW results with graph traversal |
| License | MPL-2.0 |
| Maturity | 3.9k★, pre-1.0 but stable for embedded use |

### Pluggability
All access goes through a `MemoryStore` Protocol in `db.py`. CozoStore is the default impl. Swapping to DuckDB+pgvector / SQLite+sqlite-vec / a remote service requires only a new impl class. The Protocol shape is the only contract skills depend on.

### Schema (Datalog)

```datalog
:create node {
  id: String,
  project: String,
  name: String,
  node_type: String,    -- root | branch | leaf
  level: Int,           -- 0 = L0, increases downward
  description: String,
  status: String,       -- draft | confirmed | in_progress | done | failed
  origin: String,       -- user_stated | skill_inferred (for AC #6 stats)
  tokens_estimate: Int default 0,
  created_at: String,
  updated_at: String,
  =>
  embedding: <F32; 1024>?    -- nullable; absent when embedding disabled
}

:create edge_hierarchy {
  parent_id: String,
  child_id: String,
  order_idx: Int default 0
}

:create edge_dependency {
  from_id: String,
  to_id: String,
  dep_type: String default 'requires'   -- requires | blocks | references
}

:create decision {
  id: String,
  node_id: String,
  question: String,
  options: String,        -- JSON-encoded list
  chosen: String,
  reasoning: String,
  tradeoffs: String,
  created_at: String
}

:create interface_def {
  id: String,
  node_id: String,
  name: String,
  description: String,
  spec: String,           -- free-form: signature / schema / OpenAPI fragment
  created_at: String
}

:create config {
  key: String,
  value: String
}

::hnsw create node:embedding_idx {
  dim: 1024,
  m: 16,
  ef_construction: 200,
  fields: [embedding],
  distance: Cosine,
  filter: status != 'failed'
}
```

### Storage location
- **Database**: `~/.pyramid-memory/data.cozo` (single file, project field for namespace)
- **Config**: `~/.pyramid-memory/config.toml`
- **Logs**: `~/.pyramid-memory/logs/`

Stored *outside* any project directory so the same memory works across git checkouts and harnesses.

---

## 4. Python CLI Architecture

### Entry point
`memory_cli.py` with PEP 723 inline metadata:

```python
#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "pycozo[embedded]>=0.7",
#   "tomli>=2.0; python_version<'3.11'",
#   "voyageai>=0.3",
#   "fastembed>=0.4",
# ]
# ///
```

Run as `uv run memory_cli.py <command>`. First call downloads + caches deps to an isolated environment; later calls are instant.

### Command groups

| Group | Commands | Purpose |
|---|---|---|
| `init` | `init`, `config show`, `config set` | First-time setup, capability inspection |
| `node` | `create`, `get`, `update`, `list`, `delete` | CRUD on pyramid nodes |
| `edge` | `add`, `remove` | Hierarchy + dependency edges |
| `query` | `ancestors`, `children`, `subtree`, `deps`, `status` | Graph traversal (no embedding) |
| `decision` | `store`, `list`, `get` | Decision logging |
| `interface` | `add`, `list` | Interface capture |
| `memory` | `recall`, `context`, `doctor`, `reindex`, `export` | Semantic + assembly + maintenance |

### Output contract
Every command supports `--json` and returns:
```json
{
  "ok": true,
  "data": {...},
  "warnings": [...],
  "degraded": false
}
```
`degraded: true` signals a fallback path was used (e.g. embedding unavailable → BM25). LLM decides whether to surface to the user.

### Protocol abstractions

```python
class MemoryStore(Protocol):
    def create_node(self, ...) -> Node: ...
    def add_edge(self, ...) -> None: ...
    def query_subtree(self, root_id: str) -> list[Node]: ...
    def recall(self, query: str, k: int, semantic: bool) -> list[ScoredNode]: ...
    def assemble_context(self, leaf_id: str) -> ContextPackage: ...
    # ... full surface defined in db.py

class EmbeddingProvider(Protocol):
    name: str
    dim: int
    def embed(self, texts: list[str]) -> list[list[float]]: ...
```

---

## 5. Embedding Strategy

### Default: zero-config (no embedding)
Following CodeGraphContext's precedent, embedding is **opt-in**. The default install offers full graph + BM25/string matching, which covers ~70% of recall scenarios (structural queries, name-based lookup).

### Optional providers (chosen at `init` time)
| Provider | Cost | Setup | Network |
|---|---|---|---|
| `skip` | none | none | no |
| `fastembed` (bge-small-en-v1.5) | ~130MB local model, CPU OK | one-time download | only first run |
| `voyage` (voyage-code-3) | 200M tokens free tier | API key | yes |
| `openai` (text-embedding-3-large) | paid | API key | yes |
| `ollama` (any local model) | local | running ollama | no |

### Install-time decision, runtime zero-probe
The user picks once during `memory_cli.py init`. The choice is written to `config.toml`. Every subsequent CLI call:
1. Reads `config.toml` (~1 ms).
2. Uses the configured provider directly. No availability detection.
3. On runtime failure (model file gone, API down): silently falls back to BM25 + sets `degraded: true` in JSON output.

LLM agents call `memory config show` **once per session** to learn capabilities, then make recall decisions accordingly. No per-call probing.

---

## 6. Skill Workflows

### The 5 Independence Criteria (forcing function)

Every node proposed as a `leaf` must pass **all five** checks before being marked done. Failing any forces further decomposition. These criteria are the core mechanism for solving problem #3 (拆分不够细，解耦不好):

| # | Criterion | Concrete check | Failure mode it prevents |
|---|---|---|---|
| 1 | **Single responsibility** | Can the node be described in one sentence without "and"/"以及"/"同时"? | Coarse leaves bundling unrelated concerns |
| 2 | **Interface clarity** | Can inputs / outputs / side effects be enumerated as a typed signature or schema? | Hidden coupling through implicit shared state |
| 3 | **Independent testability** | Can it be tested with mocked dependencies only — no need to instantiate sibling nodes? | Tests that pass in isolation but fail when integrated |
| 4 | **Token budget** | Does `tokens_estimate` (description + interfaces + relevant decisions) fit a single subagent context (target ≤ 8k tokens of input)? | Subagent context overflow during implementation |
| 5 | **Closed dependencies** | Are all upstream dependencies either (a) already-leaves with stable interfaces or (b) external APIs with known contracts? No "we'll figure it out later" deps. | Circular dependencies, premature freezing of unstable interfaces |

The `pyramid-decomposition` skill checks these explicitly before accepting a leaf. If 1 or 2 fails → split the node. If 3 fails → likely missing an interface boundary, add it. If 4 fails → split. If 5 fails → decompose dependencies first, recurse later.

These criteria are also the **interactive clarification engine**: when criterion 2 fails, the skill asks the user "what does this node take in and produce?" — this is how fuzzy requirements get structured without the user having to write a spec upfront.

### Skill A: `pyramid-decomposition`

**Trigger**: user proposes a fuzzy large requirement that won't fit one context window.

```
Phase 0: Initialize
  - memory_cli.py config show           # learn capabilities once
  - memory_cli.py init --project <name> # ensure namespace exists
  - node create --level 0 --name "..." --description "<raw requirement>"

Phase 1: Recursive decomposition (per node N)
  1. Apply 5 independence criteria → leaf or branch?
  2. If branch:
     a. LLM proposes 3-5 children (pure reasoning, no CLI)
     b. memory recall --query "<child desc>"  → reuse historical decisions
     c. Confirm split with user (brainstorming-style micro-questions)
     d. node create + edge add --type hierarchy (per child)
     e. decision store --node N --question "..." --chosen "..." --reasoning "..."
     f. Recurse into each child
  3. If leaf: node update --status leaf

Phase 2: Dependency pass
  - Walk leaves, identify cross-branch deps → edge add --type dependency
  - query deps --check-cycles
  - Topological sort → implementation order

Phase 3: Hand off
  - query subtree --root <L0> → full pyramid JSON
  - For each leaf: memory context --node <leaf> → "implementation package"
  - Invoke subagent-driven-development with one subagent per leaf
```

### Skill B: `memory-management`

**Trigger**: invoked by other skills (`pyramid-decomposition`, `subagent-driven-development`, `writing-plans`, `brainstorming`) or directly by user.

Capabilities:
- **Store**: `decision store`, `interface add`, `node update --status`
- **Recall**: `memory recall --query` (semantic if enabled, else BM25), graph traversals
- **Assemble**: `memory context --node <leaf-id> --json` returns `{node, ancestors, decisions, interfaces, deps, tokens_estimate}` — the complete subagent work package
- **Maintain**: `memory doctor`, `memory reindex`, `memory export`

### Integration matrix

| Caller skill | When | Calls |
|---|---|---|
| `pyramid-decomposition` | before split / after split | `recall`, `decision store` |
| `subagent-driven-development` | before dispatching subagent | `memory context --node X` |
| `writing-plans` | before drafting plan | `memory context` + `query deps` |
| `brainstorming` | before proposing approaches | `recall --semantic` |

---

## 7. Cross-harness Compatibility

### Hard dependency
Just `uv`. Install once: `curl -LsSf https://astral.sh/uv/install.sh | sh`.

### Skill install locations
| Harness | Path | Tool to invoke skill | Notes |
|---|---|---|---|
| Claude Code | `~/.claude/plugins/superpowers-plus/skills/` | `Skill` tool | native |
| Codex CLI | `~/.codex/skills/` | `skill` tool | verified |
| Codex App | same | `skill` tool | ⚠ Seatbelt sandbox blocks network → must use `skip` or pre-cached `fastembed` |
| OpenCode | `~/.config/opencode/skills/` | skill loader | needs `uv` in PATH |
| Cursor / Windsurf | `.cursor/skills/` (project) | rules + manual | weak integration |
| Gemini CLI | `~/.gemini/skills/` | `activate_skill` | verified |
| Copilot CLI | `~/.copilot/skills/` | `skill` tool | verified |

### First-time guidance
SKILL.md instructs the LLM: on first invocation, run `memory config show`. If output is `uninitialized`, prompt the user to run `memory_cli.py init` once.

---

## 8. Failure / Fallback Matrix

| Scenario | Detection point | Fallback | User-visible |
|---|---|---|---|
| `uv` not installed | first CLI call fails | none | SKILL.md prints install hint |
| `pycozo` build fails on platform | `init` | switch to pure-Python `cozo-lib` (slower) | warning |
| Embedding model download fails | `init` | force `provider=skip` | warning, ~70% capability retained |
| Voyage/OpenAI 429/timeout | single `recall` | BM25 + `degraded: true` | LLM decides whether to surface |
| DB file corrupted | startup schema check | no auto-delete; prompt `memory doctor --repair` | explicit |
| Cross-harness path mismatch | absolute path under `~/.pyramid-memory/` | n/a — single shared DB | seamless |
| Codex App sandboxed (no network) | `init` net check | force `fastembed` (if cached) or `skip` | one-time decision |
| Multi-project confusion | every command requires `--project` or cwd-derived | fail-fast on missing | explicit |

---

## 9. Invariants

1. Memory lives in `~/.pyramid-memory/`, never in project dir → no `.git` pollution, shared across harnesses.
2. `project` field namespaces a single shared DB → no per-project DB files.
3. Capability decisions are install-time, not runtime → CLI never probes providers on hot path.
4. Every command returns structured JSON → degraded paths never crash flows.
5. `uv` is the **only** non-stdlib dependency outside the PEP 723 cache.
6. LLM is orchestrator, CLI is executor → SKILL.md never embeds business logic.
7. Code-context tooling (Serena, LSP) is *separate* from this decision-memory layer — do not conflate.

---

## 10. Open Questions / Risks

- **CozoDB pre-1.0**: schema migration story is immature. Mitigation: `MemoryStore` Protocol allows swap; export/import via `memory export` for migration safety.
- ~~**HNSW filter on `status != 'failed'`**: requires verifying CozoDB filter syntax in current release.~~ Verified 2026-04-08 with pycozo 0.7.6: `filter` clause accepted and query excluded `status='failed'` rows.
- **`tokens_estimate`**: who maintains it? Initial plan: LLM updates on `node create` based on description length × heuristic; revisit if drift hurts context-assembly accuracy.
- **Decision dedup**: if the same decision recurs across projects, do we cross-link or duplicate? Initial plan: scope to project, allow `recall --all-projects` opt-in.
- **Concurrent access**: two harnesses writing simultaneously. CozoDB embedded mode is single-writer; need a file lock or accept last-write-wins. Initial plan: file lock with 5s timeout, fail-fast on contention.

---

## 11. Out of Scope (Explicitly)

- Real-time collaboration / team-shared memory (single user, single machine for v1).
- Code symbol / AST indexing (delegated to Serena or similar).
- Web UI / visualization (CLI + JSON only; users can build viz on top).
- Auto-decomposition without user confirmation (always interactive in v1).
- Migration from existing systems (greenfield).

---

## 11.5 Delivery Milestones

This spec is delivered in **two sequential plans**, each producing working, independently usable software.

### Milestone 1 — Storage + CLI (Plan 1)
**Plan file**: `docs/superpowers/plans/2026-04-07-pyramid-memory-m1-storage-cli.md`

**Scope**:
- §3 CozoDB schema (all 6 relations + HNSW index)
- §4 Python CLI — all 8 command groups (`init`, `node`, `edge`, `query`, `decision`, `interface`, `memory`, plus `validate`/`stats` for AC #5/#6)
- §5 Embedding strategy — provider abstraction + at least `skip` and `fastembed` impls
- §3 `MemoryStore` Protocol with two impls: `CozoStore` (default) + `InMemoryStore` (for tests)
- §8 fallback matrix — all 8 rows tested
- AC #1, #3, #5, #6, #7, #8, #9, #10, #11, #12, #13

**Out of scope for M1**: SKILL.md files, decomposition-guide.md, 5 independence criteria enforcement at the *skill* level (the CLI exposes `memory validate` but the skill orchestration is M2)

**Exit criteria**:
- `uv run memory_cli.py init` works on macOS + Linux
- A human can manually drive a full pyramid via CLI: create nodes, add edges, store decisions, recall, assemble context
- `MemoryStore` Protocol verified by passing the same test suite against both `CozoStore` and `InMemoryStore`
- CozoDB HNSW filter spike confirmed working (or fallback path documented)
- All §8 fallbacks tested

### Milestone 2 — Skills + Install (Plan 2)
**Plan file**: `docs/superpowers/plans/2026-04-07-pyramid-memory-m2-skills.md` *(written after M1 ships)*

**Scope**:
- §6 `pyramid-decomposition/SKILL.md` + `decomposition-guide.md` (5 independence criteria with examples)
- §6 `memory-management/SKILL.md`
- §7 Cross-harness install instructions (per-harness path + first-time `init` guidance)
- Integration with `subagent-driven-development` and `writing-plans` (handoff flows)
- AC #2, #4 (the user-facing acceptance criteria that exercise the full skill experience)

**Why M2 is written after M1 ships**: The CLI's actual ergonomics and the CozoDB performance characteristics will inform how SKILL.md should orchestrate calls. Writing M2 prematurely risks specifying flows that don't match real CLI behavior.

**Exit criteria**:
- A user can take a fuzzy 1-paragraph requirement, invoke `pyramid-decomposition`, and end up with a confirmed pyramid in the DB without writing a spec themselves
- The skill enforces 5 independence criteria at leaf-marking time (rejects via `memory validate`)
- Cross-harness install verified on at least 3 harnesses

---

## 12. Acceptance Criteria

A successful v1 ships when **all three core problems are demonstrably solved**:

### Problem #1: 上下文崩溃
1. `memory context --node <leaf>` returns a JSON package ≤ 8k tokens that lets a fresh subagent implement the leaf without re-reading the pyramid or any project files outside its declared deps.
2. The same `~/.pyramid-memory/` is readable by Claude Code, Codex CLI, and one other harness without modification — proving cross-session persistence works across tools.
3. A pyramid with ≥ 100 leaves can be queried without loading the full graph into the LLM context (per-call queries only fetch local neighborhoods).

### Problem #2: 需求描述不清
4. `pyramid-decomposition` skill can take a 1-paragraph fuzzy requirement and, through interactive Q&A, produce a confirmed pyramid where every leaf has a one-sentence description, typed interface, and linked decisions — **without the user ever writing a spec document themselves**.
5. **Structural completeness gate** (`memory validate --project X` must pass):
   - Every non-leaf node has ≥ 1 `decision` record (proves the split was justified through Q&A, not invented)
   - Every leaf node has ≥ 1 `interface_def` record (proves inputs/outputs were elicited, not assumed)
6. **Clarification effectiveness signal** (`memory stats --project X` reports):
   - `skill_inferred_node_ratio ≥ 0.3` — at least 30% of nodes were tagged `origin: skill_inferred` (surfaced by skill questioning) rather than `origin: user_stated` (present in the user's original requirement). This proves the clarification flow surfaced things the user did not initially articulate, without requiring the user to verbally acknowledge it.
   - Implementation: `node create` accepts `--origin {user_stated|skill_inferred}`; the LLM tags each node based on whether the concept appeared in the original requirement text or emerged from a clarification round.

### Problem #3: 拆分不够细 / 解耦不好
7. Every leaf passes all 5 independence criteria; the CLI rejects `node update --status leaf` if any criterion fails (mechanically enforced, not just guidance).
8. A pyramid with N leaves produces N implementation packages with **zero shared mutable state references** — each leaf's `memory context` package is fully self-contained.
9. Cross-leaf dependencies are explicit edges, not implicit imports; `query deps --check-cycles` returns 0 cycles for any accepted pyramid.

### Engineering quality
10. `uv run memory_cli.py init` works on macOS + Linux with no manual Python setup.
11. Recall works in two modes: semantic (when embedding enabled) and BM25 (default), with `degraded` flag honored.
12. All eight fallback rows in §8 are exercised by tests.
13. `MemoryStore` Protocol has a second reference impl (in-memory dict store) used in tests, proving the abstraction is real.
