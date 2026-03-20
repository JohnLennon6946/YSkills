---
name: sdd-feedback
description: Submit feedback about SDD workflow issues (skill inaccuracies, MCP errors, workflow design problems) to help improve quality
user_invocable: true
args: "[change-name]"
---

# sdd-feedback — SDD Workflow Feedback

This skill collects and submits feedback about problems encountered during SDD workflow execution. It helps improve skill instructions, MCP tools, and workflow design by reporting issues to the platform.

## Two Trigger Scenarios

### Scenario A — Manual Invocation (after archive)

User explicitly runs `/sdd-feedback [change-name]` to report issues found during a change.

### Scenario B — Automatic Failure Feedback

When an sdd-* skill encounters unexpected errors and cannot complete, it suggests running `/sdd-feedback` with failure context.

---

## Scenario A — Manual Feedback from Archived Change

### Step 1 — Select the change

If `<change-name>` is provided, use it directly.

Otherwise, run:

```bash
raven spec list --json
```

Filter to show only changes with status `archived` or `verified`. Present the list and ask the user to select one.

### Step 2 — Read FINDINGS artifact

Read the change's `FINDINGS.md` artifact:

```
.ravenspec/changes/<change-name>/FINDINGS.md
```

Extract the **踩坑记录 (Pitfalls / Lessons Learned)** section. If no such section exists or the file is empty, inform the user there are no findings to report and exit.

### Step 3 — Analyze findings

For each pitfall entry, determine if it involves:
- **Skill issue** — skill instructions were inaccurate, missing, or misleading
- **MCP issue** — an MCP tool returned errors, unexpected results, or was unavailable
- **Workflow issue** — the SDD workflow steps themselves were poorly designed or ordered
- **Knowledge issue** — AI 消费的知识条目（rule/solution/doc/runbook）内容有误、过时或缺失
- **Other** — not related to SDD infrastructure (skip these)

Filter out entries that are project-specific and not related to SDD workflow/skills/MCP/knowledge.

### Step 4 — Generate feedback drafts

For each relevant finding, generate a feedback draft:

- **Title**: concise summary of the issue
- **Description**: what happened, what was expected, what the actual behavior was
- **Type**: `issue`
- **Labels**: always include `sdd-workflow`, plus:
  - `skill:<skill-name>` if a specific skill was involved
  - `mcp:<mcp-name>` if a specific MCP tool was involved
  - `knowledge:<type>` if a knowledge entry was involved (e.g., `knowledge:rule`, `knowledge:solution`)
  - `knowledge-id:<id>` if the specific knowledge entry ID is known

For **Knowledge issue** drafts, the description should additionally include:
- Knowledge entry ID and title (if known)
- Knowledge type (rule/solution/doc/runbook)
- What was wrong or outdated
- Suggested correction (if available)

Present all drafts to the user for review.

### Step 5 — User confirmation

Ask the user to confirm, edit, or skip each feedback item.

### Step 6 — Submit feedback

For each confirmed item, run:

```bash
raven tickets create --type issue --title "<title>" --body "<description>" --labels "<comma-separated-labels>"
```

Report the results (ticket URLs or errors) to the user.

---

## Scenario B — Automatic Failure Feedback

This scenario is triggered when an sdd-* skill fails and the user accepts the suggestion to run `/sdd-feedback`.

### Step 1 — Gather failure context

Collect from the conversation:
- Which skill failed (e.g., `sdd-apply-change`, `sdd-continue-change`, `sdd-ff-change`)
- What step it was on when it failed
- The error message or unexpected behavior
- The change name (if available)

### Step 2 — Read related artifacts (if change name available)

If a change name is available, read relevant artifacts to supplement context:

```
.ravenspec/changes/<change-name>/PLAN.md
.ravenspec/changes/<change-name>/FINDINGS.md
```

### Step 3 — Generate feedback draft

Create a single feedback item:

- **Title**: `[Failure] <skill-name>: <brief error summary>`
- **Description**: Include:
  - Failed skill name and step
  - Error message or unexpected behavior
  - Change name and relevant artifact excerpts
  - Environment context (if relevant)
- **Type**: `issue`
- **Labels**: `sdd-failure`, `skill:<failed-skill-name>`, `sdd-workflow`

Present the draft to the user.

### Step 4 — User confirmation

Ask the user to confirm or edit the feedback.

### Step 5 — Submit feedback

Run:

```bash
raven tickets create --type issue --title "<title>" --body "<description>" --labels "<comma-separated-labels>"
```

Report the result to the user.

---

## Scenario C — Knowledge Quality Feedback

When AI consumes knowledge (rule/solution/doc/runbook) during SDD and the user indicates the knowledge is wrong, outdated, or incomplete.

### Trigger Conditions

- User says the rule is wrong/outdated (e.g., "this rule doesn't apply anymore")
- A retrieved solution didn't work or had side effects
- A doc was inaccurate or out of date
- A runbook step failed or is no longer valid
- AI proactively notices consumed knowledge conflicts with actual behavior

### Step 1 — Gather knowledge context

Collect from the conversation:
- Knowledge type (rule/solution/doc/runbook)
- Knowledge entry ID and title (if available, from search/retrieval context)
- What was wrong — the specific inaccuracy, outdated info, or missing content
- What the correct behavior/info should be (if known)
- How the knowledge was consumed (CLAUDE.md, skill search, manual lookup)

### Step 2 — Generate feedback draft

Create a feedback item:

- **Title**: `[Knowledge] <type>: <brief issue summary>`
- **Description**: Include:
  - Knowledge type and entry info (ID/title if known)
  - Consumption context (which SDD step, how it was loaded)
  - What was wrong or outdated
  - Expected/correct information (if known)
  - Impact on the SDD workflow
- **Type**: `issue`
- **Labels**: `knowledge-quality`, `knowledge:<type>`, `sdd-workflow`, and optionally `knowledge-id:<id>`

Present the draft to the user.

### Step 3 — User confirmation and optional direct fix

Ask the user:
1. Confirm or edit the feedback
2. (Optional) If the correct content is known, offer to directly update the knowledge entry:

```bash
# 单文件更新
raven knowledge update --id <id> --content "$(cat /tmp/raven-knowledge-fix.md)"

# 目录模式更新（适用于 skill 等多文件类型）
raven knowledge update --id <id> --dir /tmp/raven-knowledge-fix
```

### Step 4 — Submit feedback

Run:

```bash
raven tickets create --type issue --title "<title>" --body "<description>" --labels "<comma-separated-labels>"
```

Report the result to the user.

---

## Guardrails

- Never submit feedback without explicit user confirmation.
- Always include the `sdd-workflow` label so feedback is routed correctly.
- Keep descriptions factual — describe what happened, not opinions.
- If `raven tickets create` fails, show the error and suggest the user try again or file manually.
- Do not include sensitive code or credentials in feedback descriptions.
