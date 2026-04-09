# Enhanced Superpowers Pyramid Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Integrate pyramid memory into the Superpowers main workflow so simple tasks stay lightweight while large or fuzzy tasks automatically escalate into bounded, persistent decomposition.

**Architecture:** First preserve and verify an integration baseline on top of latest `origin/main`. Then add a shared pyramid runtime launcher, refactor all related skills to use one routing model, and validate the result with code tests, routing evals, and a fresh-workspace smoke path.

**Tech Stack:** Markdown skills, Python CLI/runtime helpers, pytest, eval markdown scenarios, git branch integration.

---

### Task 1: Lock Integration Baseline

**Files:**
- Modify: `skills/subagent-driven-development/SKILL.md`
- Modify: `skills/writing-plans/SKILL.md`
- Modify: `skills/pyramid-decomposition/tests/evals/results.md`
- Test: `skills/memory-management/tests/`

- [ ] **Step 1: Write the failing assertions as a review checklist**

Document these expected failures before changing files:
- `subagent-driven-development` still references `~/.pyramid-memory/`
- `writing-plans` still uses raw `uv run ... memory_cli.py` invocation
- eval docs still mention old shared-memory path

- [ ] **Step 2: Apply minimal baseline corrections**

Update the three files so the integration baseline no longer contradicts workspace-local memory.

- [ ] **Step 3: Run baseline memory tests**

Run:
```bash
cd /Users/jimmy/coding/AI/straw/skills-explore/superpowers-plus
UV_CACHE_DIR=/tmp/uv-cache \
UV_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple \
UV_INDEX_STRATEGY=unsafe-best-match \
uv run --with pytest --with 'pycozo[embedded]>=0.7' --with click --with tomli \
  python -m pytest skills/memory-management/tests -q
```
Expected: all existing memory-management tests pass, or any mirror-specific blocker is explicitly captured.

- [ ] **Step 4: Commit baseline cleanup**

```bash
git add skills/subagent-driven-development/SKILL.md \
        skills/writing-plans/SKILL.md \
        skills/pyramid-decomposition/tests/evals/results.md

git commit -m "chore(pyramid): align integration baseline with workspace-local runtime"
```

### Task 2: Add Shared Pyramid Runtime Launcher

**Files:**
- Create: `skills/memory-management/scripts/runtime.py`
- Create: `skills/memory-management/scripts/run_memory_cli.py`
- Modify: `skills/memory-management/scripts/config.py`
- Test: `skills/memory-management/tests/test_runtime.py`
- Test: `skills/memory-management/tests/test_run_memory_cli.py`

- [ ] **Step 1: Write failing runtime tests**

Add tests covering:
- workspace root resolution from nested cwd
- canonical `.superpowers/uv-cache` derivation
- launcher locating `memory_cli.py` from the installed skill directory
- launcher honoring `--workspace-root`

- [ ] **Step 2: Run the new tests and confirm failure**

Run:
```bash
cd /Users/jimmy/coding/AI/straw/skills-explore/superpowers-plus
UV_CACHE_DIR=/tmp/uv-cache \
UV_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple \
UV_INDEX_STRATEGY=unsafe-best-match \
uv run --with pytest --with 'pycozo[embedded]>=0.7' --with click --with tomli \
  python -m pytest skills/memory-management/tests/test_runtime.py \
                   skills/memory-management/tests/test_run_memory_cli.py -q
```
Expected: FAIL because launcher/runtime files do not exist yet.

- [ ] **Step 3: Implement the runtime layer**

Implement `runtime.py` to expose deterministic helpers for:
- resolving workspace root
- deriving `.superpowers/pyramid-memory`
- deriving `.superpowers/uv-cache`
- building runtime env defaults

Implement `run_memory_cli.py` to:
- parse pass-through args
- compute env and target script path
- invoke `memory_cli.py` robustly

- [ ] **Step 4: Re-run launcher tests**

Run the same test command.
Expected: PASS.

- [ ] **Step 5: Commit runtime layer**

```bash
git add skills/memory-management/scripts/runtime.py \
        skills/memory-management/scripts/run_memory_cli.py \
        skills/memory-management/scripts/config.py \
        skills/memory-management/tests/test_runtime.py \
        skills/memory-management/tests/test_run_memory_cli.py

git commit -m "feat(pyramid): add shared runtime launcher for memory CLI"
```

### Task 3: Refactor Skills to Use Unified Runtime and Routing

**Files:**
- Modify: `skills/memory-management/SKILL.md`
- Modify: `skills/pyramid-decomposition/SKILL.md`
- Modify: `skills/pyramid-decomposition/decomposition-guide.md`
- Modify: `skills/brainstorming/SKILL.md`
- Modify: `skills/writing-plans/SKILL.md`
- Modify: `skills/subagent-driven-development/SKILL.md`
- Modify: `skills/codebase-exploration/SKILL.md`
- Test: `skills/memory-management/tests/test_auto_trigger_protocol.py`
- Test: `skills/memory-management/tests/test_pre_decision_recall.py`

- [ ] **Step 1: Write a routing checklist before editing**

The updated skill set must satisfy:
- simple tasks stay out of pyramid
- oversized tasks escalate into pyramid
- all pyramid invocations use the launcher contract
- no skill references `~/.pyramid-memory/`
- stop conditions are explicit

- [ ] **Step 2: Rewrite skill entry sections and command references**

Refactor the skill docs so they become shorter and more mechanical:
- add a minimal success path
- add hard escalation rules
- replace repeated raw command blocks with launcher-oriented usage
- add stop/go rules where the current docs are vague

- [ ] **Step 3: Update routing-sensitive tests if needed**

Adjust or extend existing tests to assert the new protocol language and handoff expectations.

- [ ] **Step 4: Run focused tests**

Run:
```bash
cd /Users/jimmy/coding/AI/straw/skills-explore/superpowers-plus
UV_CACHE_DIR=/tmp/uv-cache \
UV_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple \
UV_INDEX_STRATEGY=unsafe-best-match \
uv run --with pytest --with 'pycozo[embedded]>=0.7' --with click --with tomli \
  python -m pytest skills/memory-management/tests/test_auto_trigger_protocol.py \
                   skills/memory-management/tests/test_pre_decision_recall.py -q
```
Expected: PASS.

- [ ] **Step 5: Commit the workflow refactor**

```bash
git add skills/memory-management/SKILL.md \
        skills/pyramid-decomposition/SKILL.md \
        skills/pyramid-decomposition/decomposition-guide.md \
        skills/brainstorming/SKILL.md \
        skills/writing-plans/SKILL.md \
        skills/subagent-driven-development/SKILL.md \
        skills/codebase-exploration/SKILL.md

git commit -m "feat(pyramid): integrate adaptive routing into superpowers workflow"
```

### Task 4: Add Behavior Evals for Routing and Fresh Workspace Use

**Files:**
- Create: `skills/pyramid-decomposition/tests/evals/04_simple-task-no-pyramid.md`
- Create: `skills/pyramid-decomposition/tests/evals/05_large-task-escalates.md`
- Create: `skills/pyramid-decomposition/tests/evals/06_existing-project-routing.md`
- Modify: `skills/pyramid-decomposition/tests/evals/README.md`
- Modify: `skills/pyramid-decomposition/tests/evals/run_eval.py`
- Modify: `skills/pyramid-decomposition/tests/evals/results.md`

- [ ] **Step 1: Write the eval scenarios first**

Add explicit scenarios asserting:
- simple task remains on a lightweight route
- large fuzzy task escalates into pyramid decomposition
- existing-project task triggers freshness/exploration behavior

- [ ] **Step 2: Extend the eval runner if needed**

Update `run_eval.py` so the new assertions can be checked cleanly.

- [ ] **Step 3: Run evals**

Run:
```bash
cd /Users/jimmy/coding/AI/straw/skills-explore/superpowers-plus
UV_CACHE_DIR=/tmp/uv-cache \
UV_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple \
UV_INDEX_STRATEGY=unsafe-best-match \
uv run --with pyyaml skills/pyramid-decomposition/tests/evals/run_eval.py \
  skills/pyramid-decomposition/tests/evals/04_simple-task-no-pyramid.md

UV_CACHE_DIR=/tmp/uv-cache \
UV_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple \
UV_INDEX_STRATEGY=unsafe-best-match \
uv run --with pyyaml skills/pyramid-decomposition/tests/evals/run_eval.py \
  skills/pyramid-decomposition/tests/evals/05_large-task-escalates.md

UV_CACHE_DIR=/tmp/uv-cache \
UV_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple \
UV_INDEX_STRATEGY=unsafe-best-match \
uv run --with pyyaml skills/pyramid-decomposition/tests/evals/run_eval.py \
  skills/pyramid-decomposition/tests/evals/06_existing-project-routing.md
```
Expected: PASS for all three scenarios.

- [ ] **Step 4: Commit routing eval coverage**

```bash
git add skills/pyramid-decomposition/tests/evals/04_simple-task-no-pyramid.md \
        skills/pyramid-decomposition/tests/evals/05_large-task-escalates.md \
        skills/pyramid-decomposition/tests/evals/06_existing-project-routing.md \
        skills/pyramid-decomposition/tests/evals/README.md \
        skills/pyramid-decomposition/tests/evals/run_eval.py \
        skills/pyramid-decomposition/tests/evals/results.md

git commit -m "test(pyramid): add adaptive routing eval scenarios"
```

### Task 5: Finish Installation and Fresh-Workspace Story

**Files:**
- Modify: `docs/superpowers/install-pyramid-memory.md`
- Create: `skills/memory-management/tests/test_fresh_workspace_smoke.py`
- Modify: `.gitignore` (if present and appropriate)

- [ ] **Step 1: Write the smoke test first**

Create a test or scripted smoke harness that verifies:
- first-use launcher invocation works from a clean workspace
- `.superpowers/pyramid-memory/` is created
- `.superpowers/uv-cache/` is used
- no write goes to `~/.pyramid-memory/`

- [ ] **Step 2: Update install documentation**

Document:
- launcher-first invocation
- `.gitignore` recommendation for `.superpowers/`
- session restart after installing or changing skill symlinks
- fresh-workspace smoke procedure

- [ ] **Step 3: Run smoke-focused verification**

Run:
```bash
cd /Users/jimmy/coding/AI/straw/skills-explore/superpowers-plus
UV_CACHE_DIR=/tmp/uv-cache \
UV_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple \
UV_INDEX_STRATEGY=unsafe-best-match \
uv run --with pytest --with 'pycozo[embedded]>=0.7' --with click --with tomli \
  python -m pytest skills/memory-management/tests/test_fresh_workspace_smoke.py -q
```
Expected: PASS.

- [ ] **Step 4: Run final regression suite**

Run:
```bash
cd /Users/jimmy/coding/AI/straw/skills-explore/superpowers-plus
UV_CACHE_DIR=/tmp/uv-cache \
UV_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple \
UV_INDEX_STRATEGY=unsafe-best-match \
uv run --with pytest --with 'pycozo[embedded]>=0.7' --with click --with tomli \
  python -m pytest skills/memory-management/tests -q
```
Expected: full memory-management suite passes.

- [ ] **Step 5: Commit installation and smoke coverage**

```bash
git add docs/superpowers/install-pyramid-memory.md \
        skills/memory-management/tests/test_fresh_workspace_smoke.py \
        .gitignore

git commit -m "docs(pyramid): harden fresh-workspace installation and smoke verification"
```
