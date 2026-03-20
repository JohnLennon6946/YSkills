---
name: sdd-onboard
description: 变更工作流引导上手：通过讲解与真实代码实践，完整走一遍工作流周期。英文：Guided onboarding for the change workflow - walk through a complete workflow cycle with narration and real codebase work.
license: MIT
compatibility: Requires raven CLI.
metadata:
  author: raven
  version: "1.0"
  generatedBy: "1.0.2"
---

Guide the user through their first complete RavenSpec workflow cycle. This is a teaching experience—you'll do real work in their codebase while explaining each step.

---

## Preflight

Before starting, check if RavenSpec is initialized:

```bash
ls ravenspec/config.yaml 2>/dev/null && echo "INITIALIZED" || echo "NOT_INITIALIZED"
```

**If not initialized:**
> RavenSpec isn't set up in this project yet. Run `raven spec init` first, then come back to `sdd-onboard`.

Stop here if not initialized.

---

## Phase 1: Welcome

Display:

```
## Welcome to RavenSpec!

I'll walk you through a complete change cycle—from idea to implementation—using a real task in your codebase. Along the way, you'll learn the workflow by doing it.

**What we'll do:**
1. Pick a small, real task in your codebase
2. Explore the problem briefly
3. Create a change (the container for our work)
4. Build the artifacts: PRD → FINDINGS → DESIGN → TASK
5. Implement the tasks
6. Archive the completed change

**Time:** ~15-20 minutes

Let's start by finding something to work on.
```

---

## Phase 2: Task Selection

### Codebase Analysis

Scan the codebase for small improvement opportunities. Look for:

1. **TODO/FIXME comments** - Search for `TODO`, `FIXME`, `HACK`, `XXX` in code files
2. **Missing error handling** - `catch` blocks that swallow errors, risky operations without try-catch
3. **Functions without tests** - Cross-reference `src/` with test directories
4. **Type issues** - `any` types in TypeScript files (`: any`, `as any`)
5. **Debug artifacts** - `console.log`, `console.debug`, `debugger` statements in non-debug code
6. **Missing validation** - User input handlers without validation

Also check recent git activity:
```bash
git log --oneline -10 2>/dev/null || echo "No git history"
```

### Present Suggestions

From your analysis, present 3-4 specific suggestions:

```
## Task Suggestions

Based on scanning your codebase, here are some good starter tasks:

**1. [Most promising task]**
   Location: `src/path/to/file.ts:42`
   Scope: ~1-2 files, ~20-30 lines
   Why it's good: [brief reason]

**2. [Second task]**
   Location: `src/another/file.ts`
   Scope: ~1 file, ~15 lines
   Why it's good: [brief reason]

**3. [Third task]**
   Location: [location]
   Scope: [estimate]
   Why it's good: [brief reason]

**4. Something else?**
   Tell me what you'd like to work on.

Which task interests you? (Pick a number or describe your own)
```

**If nothing found:** Fall back to asking what the user wants to build:
> I didn't find obvious quick wins in your codebase. What's something small you've been meaning to add or fix?

### Scope Guardrail

If the user picks or describes something too large (major feature, multi-day work):

```
That's a valuable task, but it's probably larger than ideal for your first RavenSpec run-through.

For learning the workflow, smaller is better—it lets you see the full cycle without getting stuck in implementation details.

**Options:**
1. **Slice it smaller** - What's the smallest useful piece of [their task]? Maybe just [specific slice]?
2. **Pick something else** - One of the other suggestions, or a different small task?
3. **Do it anyway** - If you really want to tackle this, we can. Just know it'll take longer.

What would you prefer?
```

Let the user override if they insist—this is a soft guardrail.

---

## Phase 3: Explore Demo

Once a task is selected, briefly demonstrate explore mode:

```
Before we create a change, let me quickly show you **explore mode**—it's how you think through problems before committing to a direction.
```

Spend 1-2 minutes investigating the relevant code:
- Read the file(s) involved
- Draw a quick ASCII diagram if it helps
- Note any considerations

```
## Quick Exploration

[Your brief analysis—what you found, any considerations]

┌─────────────────────────────────────────┐
│   [Optional: ASCII diagram if helpful]  │
└─────────────────────────────────────────┘

Explore mode (`sdd-explore`) is for this kind of thinking—investigating before implementing. You can use it anytime you need to think through a problem.

Now let's create a change to hold our work.
```

**PAUSE** - Wait for user acknowledgment before proceeding.

---

## Phase 4: Create the Change

**EXPLAIN:**
```
## Creating a Change

A "change" in RavenSpec is a container for all the thinking and planning around a piece of work. It lives in `ravenspec/changes/<name>/` and holds your artifacts—PRD, FINDINGS, DESIGN, TASK.

Let me create one for our task.
```

**DO:** Create the change with a derived kebab-case name:
```bash
raven spec new change "<derived-name>"
```

**SHOW:**
```
Created: `ravenspec/changes/<name>/`

The folder structure:
```
ravenspec/changes/<name>/
├── PRD.md         ← 产品需求文档（WHY）
├── FINDINGS.md    ← 发现与决策（持续更新）
├── DESIGN.md      ← 技术方案（HOW）
└── TASK.md        ← 实现任务（TODO）
```

Now let's fill in the first artifact—the PRD.
```

---

## Phase 5: PRD

**EXPLAIN:**
```
## PRD（产品需求文档）

PRD captures **why** we're making this change and **what** it involves. It defines the requirements, user scenarios, and boundary conditions.

I'll draft one based on our task.
```

**DO:** Draft the PRD content (don't save yet):

```
Here's a draft PRD:

---

## 需求概述

[1-2 sentences explaining the problem/opportunity]

## 核心功能

### [功能名称]
**描述**: [what it does]
**边界条件**: [normal and abnormal cases]

## 用户场景

### 场景1：[场景名]
**入口**: [where]
**触发条件**: [when]
**操作流程**: [steps]

## 边界条件

[Error cases, limits, edge cases]

---

Does this capture the intent? I can adjust before we save it.
```

**PAUSE** - Wait for user approval/feedback.

After approval, save the PRD:
```bash
raven spec instructions prd --change "<name>" --json
```
Then write the content to `ravenspec/changes/<name>/PRD.md`.

```
PRD saved. This is your "why" document—you can always come back and refine it as understanding evolves.

Next up: FINDINGS.
```

---

## Phase 6: FINDINGS

**EXPLAIN:**
```
## FINDINGS（发现与决策）

FINDINGS is a living document that captures **technical decisions** and **lessons learned** throughout the change. It starts with initial decisions and grows as you work.

For a small task, we'll seed it with decisions made so far.
```

**DO:** Draft the FINDINGS content:

```
Here's the initial FINDINGS:

---

## 技术决策

### [Decision title]
- **决策**: [what was chosen]
- **理由**: [why this approach]
- **放弃方案**: [alternatives considered]

## 踩坑记录

<!-- Fill in during development -->

## 变更摘要

| 日期 | 变更内容 | 原因 | 影响范围 |
|------|---------|------|---------|

---

This document grows as you work—add decisions when you make them, and pitfalls when you hit them.
```

Save to `ravenspec/changes/<name>/FINDINGS.md`.

---

## Phase 7: Design

**EXPLAIN:**
```
## Design

The design captures **how** we'll build it—technical decisions, tradeoffs, approach.

For small changes, this might be brief. That's fine—not every change needs deep design discussion.
```

**DO:** Draft design.md:

```
Here's the design:

---

## Context

[Brief context about the current state]

## Goals / Non-Goals

**Goals:**
- [What we're trying to achieve]

**Non-Goals:**
- [What's explicitly out of scope]

## Decisions

### Decision 1: [Key decision]

[Explanation of approach and rationale]

---

For a small task, this captures the key decisions without over-engineering.
```

Save to `ravenspec/changes/<name>/DESIGN.md`.

---

## Phase 8: TASK

**EXPLAIN:**
```
## TASK（实现任务）

Finally, we break the work into implementation tasks—checkboxes that drive the apply phase.

Tasks are grouped by Phase, with dependency tracking via `blockedBy`.
```

**DO:** Generate tasks based on FINDINGS and DESIGN:

```
Here are the implementation tasks:

---

## 1. [Category or file]

- [ ] 1.1 [Specific task]
- [ ] 1.2 [Specific task]

## 2. Verify

- [ ] 2.1 [Verification step]

---

Each checkbox becomes a unit of work in the apply phase. Ready to implement?
```

**PAUSE** - Wait for user to confirm they're ready to implement.

Save to `ravenspec/changes/<name>/TASK.md`.

---

## Phase 9: Apply (Implementation)

**EXPLAIN:**
```
## Implementation

Now we implement each task, checking them off as we go. I'll announce each one and occasionally note how the FINDINGS/DESIGN informed the approach.
```

**DO:** For each task:

1. Announce: "Working on task N: [description]"
2. Implement the change in the codebase
3. Reference FINDINGS/DESIGN naturally: "The design says X, so I'm doing Y"
4. Mark complete in TASK.md: `- [ ]` → `- [x]`
5. Brief status: "✓ Task N complete"

Keep narration light—don't over-explain every line of code.

After all tasks:

```
## Implementation Complete

All tasks done:
- [x] Task 1
- [x] Task 2
- [x] ...

The change is implemented! One more step—let's archive it.
```

---

## Phase 10: Archive

**EXPLAIN:**
```
## Archiving

When a change is complete, we archive it. This moves it from `ravenspec/changes/` to `ravenspec/changes/archive/YYYY-MM-DD-<name>/`.

Archived changes become your project's decision history—you can always find them later to understand why something was built a certain way.
```

**DO:**
```bash
raven spec archive "<name>"
```

**SHOW:**
```
Archived to: `ravenspec/changes/archive/YYYY-MM-DD-<name>/`

The change is now part of your project's history. The code is in your codebase, the decision record is preserved.
```

---

## Phase 11: Recap & Next Steps

```
## Congratulations!

You just completed a full RavenSpec cycle:

1. **Explore** - Thought through the problem
2. **New** - Created a change container
3. **PRD** - Captured WHY (requirements, scenarios, boundaries)
4. **FINDINGS** - Recorded decisions and lessons
5. **DESIGN** - Decided HOW
6. **TASK** - Broke it into steps
7. **Apply** - Implemented the work
8. **Archive** - Preserved the record

This same rhythm works for any size change—a small fix or a major feature.

---

## Skill Reference

| Skill | What it does |
|------|--------------|
| `sdd-explore` | Think through problems before/during work |
| `sdd-new-change` | Start a new change, step through artifacts |
| `sdd-ff-change` | Fast-forward: create all artifacts at once |
| `sdd-continue-change` | Continue working on an existing change |
| `sdd-apply-change` | Implement tasks from a change |
| `sdd-verify-change` | Verify implementation matches artifacts |
| `sdd-archive-change` | Archive a completed change |

---

## What's Next?

Try `sdd-new-change` or `sdd-ff-change` on something you actually want to build. You've got the rhythm now!
```

---

## Graceful Exit Handling

### User wants to stop mid-way

If the user says they need to stop, want to pause, or seem disengaged:

```
No problem! Your change is saved at `ravenspec/changes/<name>/`.

To pick up where we left off later:
- `sdd-continue-change <name>` - Resume artifact creation
- `sdd-apply-change <name>` - Jump to implementation (if tasks exist)

The work won't be lost. Come back whenever you're ready.
```

Exit gracefully without pressure.

### User just wants skill reference

If the user says they just want to see the skills or skip the tutorial:

```
## RavenSpec Quick Reference

| Skill | What it does |
|------|--------------|
| `sdd-explore` | Think through problems (no code changes) |
| `sdd-new-change <name>` | Start a new change, step by step |
| `sdd-ff-change <name>` | Fast-forward: all artifacts at once |
| `sdd-continue-change <name>` | Continue an existing change |
| `sdd-apply-change <name>` | Implement tasks |
| `sdd-verify-change <name>` | Verify implementation |
| `sdd-archive-change <name>` | Archive when done |

Try `sdd-new-change` to start your first change, or `sdd-ff-change` if you want to move fast.
```

Exit gracefully.

---

## Guardrails

- **Follow the EXPLAIN → DO → SHOW → PAUSE pattern** at key transitions (after explore, after PRD draft, after TASK, after archive)
- **Keep narration light** during implementation—teach without lecturing
- **Don't skip phases** even if the change is small—the goal is teaching the workflow
- **Pause for acknowledgment** at marked points, but don't over-pause
- **Handle exits gracefully**—never pressure the user to continue
- **Use real codebase tasks**—don't simulate or use fake examples
- **Adjust scope gently**—guide toward smaller tasks but respect user choice
