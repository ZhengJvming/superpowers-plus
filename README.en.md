# Superpowers-Plus

[中文](README.md) | **English**

> 🚀 Give your coding agent a structured brain — not just tools, but **discipline**.

Superpowers-Plus is a structured workflow skill system designed for AI programming assistants, based on composable "skills" that trigger automatically. Your agent doesn't just write code — it designs, decomposes, plans, tests, reviews, and remembers.

> **Note**: This project is an enhanced version of [Superpowers](https://github.com/obra/superpowers), adding Pyramid Decomposition and Memory Management systems, specifically designed to handle complex, cross-session large-scale engineering tasks.

***

## 🚀 Quick Start

### Installation

Superpowers-Plus supports multiple AI programming assistant platforms. Choose your platform and follow the installation steps below:

***

#### Claude Code

**Method 1: Clone Installation (Recommended)**

```bash
# 1. Clone the repository
git clone https://github.com/jimmy/superpowers-plus.git ~/.claude/superpowers-plus

# 2. Create plugin reference in your project
# Create .claude/plugins.json in project root (if it doesn't exist)
echo '{"plugins": ["~/.claude/superpowers-plus"]}' > .claude/plugins.json

# 3. Restart Claude Code
```

**Method 2: Local Development Mode**

```bash
# Clone to local directory
git clone https://github.com/jimmy/superpowers-plus.git ~/coding/superpowers-plus

# Use absolute path in your project
echo '{"plugins": ["~/coding/superpowers-plus"]}' > .claude/plugins.json
```

**Verify Installation**:

```
Tell Claude Code: "List your skills"
```

You should see skills like `using-superpowers`, `brainstorming`, `pyramid-decomposition`, etc.

***

#### Cursor

**Method 1: Clone Installation**

```bash
# 1. Clone the repository
git clone https://github.com/jimmy/superpowers-plus.git ~/.cursor/superpowers-plus

# 2. Create .cursor/plugins.json in project root
echo '{"plugins": ["~/.cursor/superpowers-plus"]}' > .cursor/plugins.json

# 3. Restart Cursor
```

**Method 2: Project-Level Installation**

```bash
# Clone directly to project directory
git clone https://github.com/jimmy/superpowers-plus.git .cursor/plugins/superpowers-plus

# Cursor will automatically discover plugins in .cursor/plugins/ directory
```

**Verify Installation**:

```
Type in Cursor: "What development skills do you have?"
```

***

#### OpenAI Codex

**Installation Steps**:

```bash
# 1. Clone the repository
git clone https://github.com/jimmy/superpowers-plus.git ~/.codex/superpowers-plus

# 2. Create skills directory
mkdir -p ~/.agents/skills

# 3. Create symlink (Unix/macOS)
ln -s ~/.codex/superpowers-plus/skills ~/.agents/skills/superpowers-plus

# Windows PowerShell (no Developer Mode required):
# cmd /c mklink /J "$env:USERPROFILE\.agents\skills\superpowers-plus" "$env:USERPROFILE\.codex\superpowers-plus\skills"

# 4. Restart Codex
```

**Verify Installation**:

```bash
ls -la ~/.agents/skills/superpowers-plus
```

***

#### OpenCode

**Installation Steps**:

Add to `opencode.json` in your project root:

```json
{
  "plugin": ["superpowers-plus@git+https://github.com/jimmy/superpowers-plus.git"]
}
```

Restart OpenCode, and the plugin will install automatically.

**Verify Installation**:

```
Use skill tool to list skills
```

***

#### Other Platforms

For other AI programming assistants that support skill/plugin systems:

```bash
# 1. Clone the repository
git clone https://github.com/jimmy/superpowers-plus.git <platform-dir>/superpowers-plus

# 2. Configure skills directory according to platform documentation
# Usually needs to point to skills/ directory
```

***

### Initialize Pyramid Memory System (Optional)

For large enough projects, it's recommended to initialize the pyramid memory system:

```bash
# Execute in project root
python3 <skill-path>/memory-management/scripts/run_memory_cli.py init \
  --project my-project --embedding skip
```

Memory is stored at `<project-root>/.superpowers/pyramid-memory/` — a single SQLite file. Remember to add `.superpowers/` to `.gitignore`.

***

## ✨ Core Features

### 1. 📐 Pyramid Decomposition System

Handle large, fuzzy, cross-boundary complex requirements:

```
User Request: "Build an e-commerce platform"

AI automatically decomposes:
Level 0: E-commerce Platform
    │
    ├── Level 1: User Module | Product Module | Order Module | Payment Module
    │
    └── Level 2: (Continue decomposing)
        - User Module: Registration, Login, Permissions, Profile
        - Product Module: List, Details, Search, Inventory
        - Order Module: Create, Query, Modify, Cancel
        - Payment Module: Alipay, WeChat, Credit Card
```

Each leaf node is an independent business function unit, implemented by a separate Agent.

### 2. 🧠 Memory Management System

Persistent memory based on CozoDB graph database:

- **Node Management**: Store each node of the decomposition tree
- **Decision Storage**: Record context and rationale for each decomposition decision
- **Interface Contracts**: Manage input/output definitions for leaf nodes
- **File References**: Track associations between code files and nodes
- **Semantic Recall**: Historical decision retrieval based on vector similarity

### 3. 🎯 Adaptive Routing Gates

Automatically select the most suitable workflow based on task characteristics:

| Task Type              | Route                                                             | Example                                       |
| ---------------------- | ----------------------------------------------------------------- | --------------------------------------------- |
| **Simple/Local**       | `systematic-debugging` or `test-driven-development`               | "Fix null pointer", "Add helper function"     |
| **Bounded Multi-Step** | `brainstorming` → `writing-plans` → `subagent-driven-development` | "Add OAuth login", "Refactor config parser"   |
| **Large/Fuzzy**        | `pyramid-decomposition` → leaf handoff → `writing-plans`          | "Build payment system", "Redesign data layer" |
| **Analytical/Review**  | `codebase-exploration` (standalone)                               | "Review architecture", "Map dependencies"     |

***

## 📚 Skill Catalog

### Routing Layer

- **using-superpowers** — Entry router. Classifies tasks, dispatches to correct workflow.
- **writing-skills** — Meta-skill for authoring and testing new skills.

### Core Workflow Layer

- **brainstorming** — Turns fuzzy ideas into validated designs through Socratic dialogue.
- **pyramid-decomposition** — BFS decomposition of large requirements into independence-qualified leaves.
- **codebase-exploration** — Maps existing codebases: module structure, dependency graphs, change hotspots, architecture patterns.
- **memory-management** — Persistent graph + decision memory. CozoDB backend, Python CLI, JSON protocol.
- **writing-plans** — Creates bite-sized implementation plans. Every step has exact file paths, complete code, verification commands.
- **subagent-driven-development** — Executes plans by dispatching one subagent per task with two-stage review.
- **executing-plans** — Alternative execution for environments without subagent support.

### Discipline Layer

- **test-driven-development** — Strict RED-GREEN-REFACTOR. No production code without a failing test.
- **systematic-debugging** — Four-phase root cause investigation. Cross-module tracing via dependency graph.
- **verification-before-completion** — Evidence before claims, always.
- **requesting-code-review** / **receiving-code-review** — Structured review dispatch and response.
- **finishing-a-development-branch** — Merge, PR, keep, or discard — with safety verification.
- **using-git-worktrees** — Isolated development branches.
- **dispatching-parallel-agents** — Concurrent investigation of independent problems.

***

## 🎯 Design Philosophy

### Core Problems

Most coding agents fail the same way: they jump straight into writing code. Small tasks work, but anything beyond a single file becomes a mess — hallucinated interfaces, contradictory decisions, coarse decomposition where modules bleed into each other.

Three root causes:

1. **Context Collapse** — The context window is finite. For any non-trivial system, the full design + code + decisions cannot fit. Subagents re-derive context from scratch. Decisions evaporate between sessions.
2. **Users Cannot Articulate Complete Designs Upfront** — Requirements start fuzzy ("build me a payment system"). Ad-hoc Q\&A produces inconsistent specs. The agent fills gaps with assumptions that surface as bugs weeks later.
3. **Decomposition Stops Too Early** — Without a forcing function, agents split work into chunks that are still too coarse. Responsibilities overlap. Hidden coupling sneaks in. Parallel subagents collide on shared state and produce code that won't compose.

### The Superpowers Approach

**Discipline over intelligence.** A less capable agent following a rigorous process outperforms a brilliant agent winging it.

The system enforces three invariants:

- **No Code Without Design** — Every implementation starts from an approved spec. The agent asks micro-questions, proposes alternatives with trade-offs, and presents designs in digestible sections. You never write a spec — you confirm or reject one.
- **No Leaf Without Independence** — Every unit of work must pass five criteria (single responsibility, interface clarity, independent testability, token budget, closed dependencies) before implementation begins. Failing any criterion forces further decomposition until coupling disappears.
- **No Claim Without Evidence** — "Should work" is not allowed. Every completion claim requires a fresh verification command, full output read, and confirmed result. The agent cannot express satisfaction before running the test.

***

## 📖 Methodology

The workflow mirrors how senior engineers actually think:

```
Fuzzy Idea
  → Structured Design (Brainstorming)
    → Pyramid Decomposition (Large/Cross-Boundary Work)
      → Independence-Qualified Leaves
        → Bite-Sized Implementation Plans (2-5 min per task)
          → TDD Implementation (RED → GREEN → REFACTOR)
            → Two-Stage Code Review (Spec Compliance → Code Quality)
              → Verified Completion
```

Each stage has **hard gates** — you cannot proceed without satisfying the exit criteria. The agent cannot rationalize its way past these gates. If a test fails, it cannot claim success. If a leaf is too coarse, it cannot start implementation. If a design is unapproved, it cannot write code.

### The Five Independence Criteria

A node becomes a leaf only when it passes all five:

| Criterion                   | How It's Checked                  | What It Prevents                                   |
| --------------------------- | --------------------------------- | -------------------------------------------------- |
| **Single Responsibility**   | LLM judgment                      | God-modules that do too many things                |
| **Interface Clarity**       | At least one published interface  | Implicit contracts that break under change         |
| **Independent Testability** | LLM judgment                      | Units that can't be verified in isolation          |
| **Token Budget**            | Context package < 8000 tokens     | Leaves too large for a subagent to hold in context |
| **Closed Dependencies**     | All deps are explicit graph edges | Hidden coupling that causes integration failures   |

***

## 🧠 Memory Architecture

The persistent memory system solves context collapse:

```
┌─────────────────────────────────────────────────────┐
│                    Pyramid Memory                    │
│                                                      │
│  Nodes ─── hierarchy edges ─── dependency edges      │
│    │                                                 │
│    ├── Decisions (options, reasoning, trade-offs)     │
│    ├── Interfaces (contracts between leaves)          │
│    ├── File References (code pointers + staleness)    │
│    └── Scratchpad (session findings, hypotheses)      │
│                                                      │
│  Storage: CozoDB (graph + vector, single SQLite file) │
│  Access: Python CLI with JSON output                  │
│  Context: One leaf package at a time, never the       │
│           full pyramid                                │
└─────────────────────────────────────────────────────┘
```

When a subagent needs context for a leaf, it gets exactly what it needs — the node, its ancestor chain, relevant decisions, interfaces, dependencies, and file references — in a bounded package. Not the whole pyramid. Not the whole codebase. Just the minimum sufficient context.

***

## 💡 Technical Highlights

### PEP 723 Standalone Scripts

All CLI scripts are self-contained Python scripts using PEP 723 dependency declarations:

```python
# /// script
# dependencies = ["cozo-embedded", "numpy", "requests"]
# ///
```

**Advantages**:

- No global installation required, dependencies managed automatically via `uv` runtime
- Workspace-level UV\_CACHE\_DIR isolation
- Built-in mirror fallback (Tsinghua → Aliyun → PyPI)

### Protocol-Based Storage Layer

```python
# MemoryStore Protocol
class MemoryStore(Protocol):
    def create_node(self, node: Node) -> None: ...
    def add_edge(self, edge: Edge) -> None: ...
    def recall(self, query: str, k: int = 3) -> List[RecallResult]: ...

# Dual Implementation
- InMemoryStore: Testing and lightweight usage
- CozoStore: Production-grade persistent storage
```

***

## 🔄 Updating

```bash
# Navigate to installation directory
cd ~/.claude/superpowers-plus  # or other installation path

# Pull latest code
git pull
```

Skills update instantly through the symlink.

***

## 🗑️ Uninstalling

```bash
# 1. Remove plugin reference
rm .claude/plugins.json  # or edit to remove superpowers-plus

# 2. Remove installed repository
rm -rf ~/.claude/superpowers-plus

# 3. Clean project memory (optional)
rm -rf .superpowers/
```

***

## 🤝 Contributing

See `CLAUDE.md` for contributor guidelines. The short version: this repo has a 94% PR rejection rate. Read the guidelines. Follow `writing-skills`. Test with pressure scenarios. Show evidence of human involvement.

**Important**: Before contributing to this repository, please read `.github/PULL_REQUEST_TEMPLATE.md` and fill in every section. Do not leave any sections blank or use placeholder text.

***

## 🙏 Acknowledgments

Superpowers-Plus is built on the shoulders of giants:

- **Original Superpowers**: <https://github.com/obra/superpowers> by [Jesse Vincent](https://blog.fsck.com)

Special thanks to the Superpowers community for inspiring this enhanced version with pyramid decomposition and memory management capabilities.

***

## 📣 Community

Built by [Jesse Vincent](https://blog.fsck.com) and [Prime Radiant](https://primeradiant.com). Pyramid Memory system contributed by the community.

- **Discord**: [Join us](https://discord.gg/35wsABTejz)
- **Issues**: <https://github.com/obra/superpowers/issues>
- **Release Announcements**: [Sign up](https://primeradiant.com/superpowers/)

***

## 📄 License

MIT License — see LICENSE file for details.

***

## 💖 Sponsorship

If Superpowers helps you build things that make money, consider [sponsoring Jesse's opensource work](https://github.com/sponsors/obra).
