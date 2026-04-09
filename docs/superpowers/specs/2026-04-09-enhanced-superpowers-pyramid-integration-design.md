# Enhanced Superpowers Pyramid Integration Design

**Status:** Draft for implementation

## Goal

Turn pyramid memory from an optional add-on into a first-class Superpowers workflow capability that routes tasks by complexity:
- simple tasks stay lightweight
- medium tasks use existing brainstorm/plan/execute flows
- large or ambiguous tasks automatically escalate into pyramid decomposition with persistent context

The end state is an enhanced Superpowers core workflow, not just two extra skills.

## Problem Statement

The current M1-M5 pyramid stack is functional, but it is not yet integrated as a coherent part of the main Superpowers workflow.

Current issues:
- multiple skills reference pyramid memory inconsistently
- some skills still assume old storage paths (`~/.pyramid-memory/`)
- command invocation depends on the model correctly reconstructing long `uv run ... memory_cli.py` calls
- workspace-local memory and workspace-local `uv` cache are not derived from the same root
- simple tasks and complex tasks are not routed through a unified decision model
- skill content is too verbose in repeated command blocks and too weak in stop/go rules

## Design Principles

### 1. Pyramid is an escalation path, not the default path

Most tasks should not pay the complexity cost of decomposition.

The system should prefer the lightest workflow that can safely handle the task:
- simple/local task -> existing direct implementation workflow
- multi-step but bounded task -> brainstorming -> writing-plans -> execution
- oversized, fuzzy, cross-boundary, or context-risky task -> pyramid decomposition

### 2. One runtime entrypoint

All pyramid-related skills must use one shared launcher instead of repeating direct `uv run skills/memory-management/scripts/memory_cli.py ...` commands.

The launcher must handle:
- locating the installed skill root
- resolving workspace root
- setting workspace-local `UV_CACHE_DIR`
- setting index mirror defaults
- invoking the CLI reliably from any target project directory

### 3. One workspace root model

Memory store, `uv` cache, and related runtime artifacts must derive from the same workspace root.

Canonical paths:
- memory store: `<workspace-root>/.superpowers/pyramid-memory/`
- uv cache: `<workspace-root>/.superpowers/uv-cache/`

### 4. Hard routing rules beat soft suggestions

Routing into pyramid decomposition should not depend on vague judgment alone.

We need an explicit escalation rubric that can be embedded into process skills.

### 5. Skills are behavior code

Any change to skill wording that changes behavior must be evaluated like a code change.

The enhanced flow must preserve strong guardrails:
- do not decompose simple tasks
- do not skip pyramid for clearly oversized tasks
- do not hand full-tree context to implementers when a leaf package exists
- do not proceed through stale or missing context silently

## Target Workflow

### Route A: Simple Task

Use direct existing workflows when all of the following are true:
- one clear outcome
- one bounded subsystem
- no cross-session memory needed
- no more than a few files or one tight bugfix area
- no obvious multi-agent decomposition benefit

Expected flow:
- optional `brainstorming` for local design clarification
- `writing-plans` only if the work is truly multi-step
- implementation via existing TDD/execution skills

Pyramid should not activate.

### Route B: Medium Task

Use standard Superpowers workflow when the work is multi-step but still bounded.

Expected flow:
- `brainstorming`
- `writing-plans`
- `subagent-driven-development` or `executing-plans`

Pyramid may supply context if the task already came from a decomposed leaf, but it should not be mandatory.

### Route C: Large / Fuzzy / Cross-Boundary Task

Escalate to pyramid when any of these are true:
- requirement spans multiple subsystems or boundaries
- the user cannot provide a clean implementation spec up front
- the work would likely require more than one plan or multiple independent leaves
- existing-project changes require persistent structural mapping
- context risk is high enough that one agent should not hold the whole design at once

Expected flow:
- `brainstorming` identifies that the task exceeds a normal spec/plan cycle
- `pyramid-decomposition` constructs the decomposition graph
- `memory-management` stores decisions, interfaces, file refs, scratch notes
- `writing-plans` consumes one leaf context package at a time
- `subagent-driven-development` or `executing-plans` implements leaf-by-leaf

## Escalation Rubric

Introduce a reusable rubric that skills can follow before choosing pyramid:

Escalate when at least one of these is true:
- `scope_large`: requirement naturally breaks into multiple independently implementable units
- `spec_unclear`: user intent is too fuzzy for one implementation plan
- `context_risky`: likely context package would exceed safe working set if treated monolithically
- `existing_project_mapping_needed`: real codebase exploration and boundary mapping are prerequisite to safe planning

Do not escalate when all of these are true:
- `single_outcome`
- `single_boundary`
- `bounded_context`
- `no_persistent_structure_needed`

This rubric should be embedded into:
- `brainstorming`
- `writing-plans`
- `subagent-driven-development`
- `memory-management`
- `pyramid-decomposition`

## Launcher Architecture

Create a small launcher layer for pyramid runtime calls.

Proposed files:
- `skills/memory-management/scripts/runtime.py`
- `skills/memory-management/scripts/run_memory_cli.py`

Responsibilities:
- detect workspace root using the same algorithm as config resolution
- compute canonical `.superpowers/` paths
- provide a stable command contract for other skills and docs
- optionally expose shell-safe examples for external manual use

Expected launcher behavior:
1. Determine workspace root from explicit arg or upward search.
2. Set `UV_CACHE_DIR=<workspace-root>/.superpowers/uv-cache`.
3. Set package index defaults.
4. Execute `memory_cli.py` from the installed skill directory, not the target project directory.

This removes the current path ambiguity.

## Skill Integration Changes

### brainstorming

Add a hard escalation section:
- if the task exceeds one normal spec/plan cycle, switch into pyramid decomposition
- do not continue asking local-detail questions for a structurally oversized problem

### writing-plans

Change pyramid integration from optional ad hoc retrieval to an explicit context handoff rule:
- if planning a pyramid leaf, fetch the leaf package through the launcher
- never reconstruct pyramid context manually

### subagent-driven-development

Update to:
- stop referencing `~/.pyramid-memory/`
- use workspace-local launcher
- mark leaf completion through launcher
- treat leaf package as authoritative task context

### memory-management

Refactor into a concise operator skill:
- short minimal-start section
- hard rules for stop/go
- launcher-first commands
- fewer repeated command blocks

### pyramid-decomposition

Refactor into a routing + decomposition skill:
- clear escalation criteria
- BFS decomposition loop
- leaf qualification gates
- explicit dependency/interface requirements
- strong closeout and handoff rules

### codebase-exploration

Formalize integration:
- when freshness is `unknown` or `stale`, exploration is not optional for existing-project structural work
- exploration output should produce file refs and boundary findings consumable by memory-management

## Documentation Changes

Update documentation to reflect the enhanced workflow:
- installation guide
- skill references to launcher usage
- fresh-workspace smoke test instructions
- `.gitignore` recommendation for `.superpowers/`
- session restart note after new skill installation or symlink changes

## Testing Strategy

### Code Tests

Add or update automated tests for:
- runtime root resolution
- launcher path resolution from arbitrary cwd
- consistent uv cache location under workspace root
- backward-safe CLI invocation through launcher

### Skill / Behavior Tests

Add eval-style scenarios for:
- simple task stays out of pyramid
- medium task uses normal plan workflow
- large fuzzy task escalates into pyramid
- existing-project task triggers freshness/exploration path
- leaf handoff into `writing-plans` / `subagent-driven-development`

### Smoke Tests

Create a fresh-workspace test procedure that verifies:
- installed skill can be discovered in a clean project
- first invocation creates `.superpowers/pyramid-memory/`
- runtime uses workspace-local cache
- no write occurs to `~/.pyramid-memory/`

## Migration Strategy

### Phase 1: Integration Baseline

Preserve current M1-M5 functionality but move it onto latest `origin/main`.

This branch should:
- retain current features
- absorb latest upstream guardrails
- remove obvious stale references
- establish a clean point for redesign

### Phase 2: Enhanced Redesign

Then refactor behavior, docs, routing, and launcher architecture.

This phase is intentionally allowed to be breaking relative to internal draft docs, but it must preserve end-user value and pass explicit tests/evals.

## Non-Goals

Not in scope for this redesign:
- replacing existing execution skills with pyramid-only flows
- making every task persistent by default
- adding new third-party runtime dependencies
- contributing upstream before eval evidence exists

## Acceptance Criteria

1. Latest main plus pyramid integration builds on a dedicated redesign branch.
2. A launcher exists and all pyramid-related skills use it or the equivalent runtime abstraction.
3. No core skill references `~/.pyramid-memory/`.
4. Workspace-local memory and workspace-local `uv` cache derive from the same resolved root.
5. Simple tasks do not unnecessarily route through pyramid.
6. Large/fuzzy tasks do route through pyramid with explicit criteria.
7. Existing-project workflows trigger freshness/exploration behavior consistently.
8. Leaf handoff into planning/execution uses bounded context packages only.
9. Docs describe `.superpowers/` management, session restart, and fresh-workspace setup.
10. Tests/evals cover routing, launcher behavior, and fresh-workspace behavior.
