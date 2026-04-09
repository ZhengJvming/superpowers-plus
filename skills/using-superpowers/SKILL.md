---
name: using-superpowers
description: Use when starting any conversation to identify the smallest correct workflow skill before responding or acting
---

<SUBAGENT-STOP>
If you were dispatched as a subagent to execute a specific task, skip this skill.
</SUBAGENT-STOP>

<EXTREMELY-IMPORTANT>
If you think there is even a 1% chance a skill might apply to what you are doing, you ABSOLUTELY MUST invoke the skill.

IF A SKILL APPLIES TO YOUR TASK, YOU DO NOT HAVE A CHOICE. YOU MUST USE IT.

This is not negotiable. This is not optional. You cannot rationalize your way out of this.
</EXTREMELY-IMPORTANT>

## Instruction Priority

Superpowers skills override default system prompt behavior, but **user instructions always take precedence**:

1. **User's explicit instructions** (CLAUDE.md, GEMINI.md, AGENTS.md, direct requests) — highest priority
2. **Superpowers skills** — override default system behavior where they conflict
3. **Default system prompt** — lowest priority

If CLAUDE.md, GEMINI.md, or AGENTS.md says "don't use TDD" and a skill says "always use TDD," follow the user's instructions. The user is in control.

## How to Access Skills

**In Claude Code:** Use the `Skill` tool. When you invoke a skill, its content is loaded and presented to you—follow it directly. Never use the Read tool on skill files.

**In Copilot CLI:** Use the `skill` tool. Skills are auto-discovered from installed plugins. The `skill` tool works the same as Claude Code's `Skill` tool.

**In Gemini CLI:** Skills activate via the `activate_skill` tool. Gemini loads skill metadata at session start and activates the full content on demand.

**In other environments:** Check your platform's documentation for how skills are loaded.

## Platform Adaptation

Skills use Claude Code tool names. Non-CC platforms: see `references/copilot-tools.md` (Copilot CLI), `references/codex-tools.md` (Codex) for tool equivalents. Gemini CLI users get the tool mapping loaded automatically via GEMINI.md.

# Using Skills

## The Rule

**Invoke relevant or requested skills BEFORE any response or action.** Even a 1% chance a skill might apply means that you should invoke the skill to check. If an invoked skill turns out to be wrong for the situation, you don't need to use it.

**Use the lightest workflow that can safely handle the task.** Do not force simple work through heavyweight routing, and do not force oversized work through a local workflow.

## Route by Task Size

### Simple / Local

Use the direct path when all of these are true:
- one clear outcome
- one bounded subsystem or bug area
- no architectural uncertainty
- no persistent decomposition state needed

Typical route:
- `systematic-debugging` for bugs
- `test-driven-development` for small feature or refactor work

Do not invoke `pyramid-decomposition` for this class of task.

### Bounded Multi-Step

Use the normal design and planning path when the task is real project work but still fits one coherent spec and one implementation plan.

Typical route:
- `brainstorming`
- `writing-plans`
- `subagent-driven-development` or `executing-plans`

### Large / Fuzzy / Cross-Boundary

Escalate when any of these are true:
- the requirement naturally splits into multiple independently implementable units
- the user intent is too fuzzy for one clean plan
- the work spans multiple subsystems or boundaries
- an existing codebase must be structurally mapped before safe planning

Typical route:
- `brainstorming` only long enough to confirm that escalation is needed
- `pyramid-decomposition`
- `memory-management`
- leaf handoff into `writing-plans` or `subagent-driven-development`

```dot
digraph skill_flow {
    "User message received" [shape=doublecircle];
    "Might any skill apply?" [shape=diamond];
    "Invoke Skill tool" [shape=box];
    "Announce: 'Using [skill] to [purpose]'" [shape=box];
    "Classify task size" [shape=diamond];
    "Direct workflow\n(debugging/TDD)" [shape=box];
    "Normal workflow\n(brainstorming -> writing-plans)" [shape=box];
    "Escalate workflow\n(pyramid-decomposition)" [shape=box];
    "Has checklist?" [shape=diamond];
    "Create TodoWrite todo per item" [shape=box];
    "Follow skill exactly" [shape=box];
    "Respond (including clarifications)" [shape=doublecircle];

    "User message received" -> "Might any skill apply?";
    "Might any skill apply?" -> "Invoke Skill tool" [label="yes, even 1%"];
    "Might any skill apply?" -> "Respond (including clarifications)" [label="definitely not"];
    "Invoke Skill tool" -> "Announce: 'Using [skill] to [purpose]'";
    "Announce: 'Using [skill] to [purpose]'" -> "Classify task size";
    "Classify task size" -> "Direct workflow\n(debugging/TDD)" [label="simple/local"];
    "Classify task size" -> "Normal workflow\n(brainstorming -> writing-plans)" [label="bounded multi-step"];
    "Classify task size" -> "Escalate workflow\n(pyramid-decomposition)" [label="large/fuzzy"];
    "Direct workflow\n(debugging/TDD)" -> "Has checklist?";
    "Normal workflow\n(brainstorming -> writing-plans)" -> "Has checklist?";
    "Escalate workflow\n(pyramid-decomposition)" -> "Has checklist?";
    "Has checklist?" -> "Create TodoWrite todo per item" [label="yes"];
    "Has checklist?" -> "Follow skill exactly" [label="no"];
    "Create TodoWrite todo per item" -> "Follow skill exactly";
}
```

## Red Flags

These thoughts mean STOP—you're rationalizing:

| Thought | Reality |
|---------|---------|
| "This is just a simple question" | Questions are tasks. Check for skills. |
| "I need more context first" | Skill check comes BEFORE clarifying questions. |
| "Let me explore the codebase first" | Skills tell you HOW to explore. Check first. |
| "I can check git/files quickly" | Files lack conversation context. Check for skills. |
| "Let me gather information first" | Skills tell you HOW to gather information. |
| "This doesn't need a formal skill" | If a skill exists, use it. |
| "I remember this skill" | Skills evolve. Read current version. |
| "This doesn't count as a task" | Action = task. Check for skills. |
| "The big workflow is overkill" | Route to the smallest workflow that safely fits. |
| "I'll just do this one thing first" | Check BEFORE doing anything. |
| "This feels productive" | Undisciplined action wastes time. Skills prevent this. |
| "I know what that means" | Knowing the concept ≠ using the skill. Invoke it. |

## Skill Priority

When multiple skills could apply, use this order:

1. **Routing/process skills first** (brainstorming, debugging, pyramid-decomposition) - these determine HOW to approach the task
2. **Implementation skills second** (frontend-design, mcp-builder) - these guide execution

"Let's build X" → classify first, then choose the smallest correct workflow.
"Fix this bug" → debugging first, then domain-specific skills.

## Skill Types

**Rigid** (TDD, debugging): Follow exactly. Don't adapt away discipline.

**Flexible** (patterns): Adapt principles to context.

The skill itself tells you which.

## User Instructions

Instructions say WHAT, not HOW. "Add X" or "Fix Y" doesn't mean skip workflows.
