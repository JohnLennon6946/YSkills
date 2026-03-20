---
name: sdd-continue-change
description: 通过创建下一个 artifact 继续推进变更。适用于用户希望继续推进当前变更流程的场景。英文：Continue working on a change by creating the next artifact. Use when the user wants to progress their change, create the next artifact, or continue their workflow.
license: MIT
compatibility: Requires raven CLI.
metadata:
  author: raven
  version: "1.4"
  generatedBy: "1.0.2"
---

Continue working on a change by creating the next artifact.

**Input**: Optionally specify a change name. If omitted, check if it can be inferred from conversation context. If vague or ambiguous you MUST prompt for available changes.

**Steps**

1. **If no change name provided, prompt for selection**

   Run `raven spec list --json` to get available changes sorted by most recently modified. Then use the **AskUserQuestion tool** to let the user select which change to work on.

   Present the top 3-4 most recently modified changes as options, showing:
   - Change name
   - Schema (from `schema` field if present, otherwise "spec-driven")
   - Status (e.g., "0/5 tasks", "complete", "no tasks")
   - How recently it was modified (from `lastModified` field)

   Mark the most recently modified change as "(Recommended)" since it's likely what the user wants to continue.

   **IMPORTANT**: Do NOT guess or auto-select a change. Always let the user choose.

2. **Check current status**
   ```bash
   raven spec status --change "<name>" --json
   ```
   Parse the JSON to understand current state. The response includes:
   - `schemaName`: The workflow schema being used (e.g., "spec-driven")
   - `artifacts`: Array of artifacts with their status ("done", "ready", "blocked")
   - `isComplete`: Boolean indicating if all artifacts are complete

3. **Act based on status**:

   ---

   **If all artifacts are complete (`isComplete: true`)**:
   - Congratulate the user
   - Show final status including the schema used
   - Suggest: "All artifacts created! You can now implement this change or archive it."
   - STOP

   ---

   **If artifacts are ready to create** (status shows artifacts with `status: "ready"`):
   - Pick the FIRST artifact with `status: "ready"` from the status output
   - Get its instructions:
     ```bash
     raven spec instructions <artifact-id> --change "<name>" --json
     ```
   - Parse the JSON. The key fields are:
     - `context`: Project background (constraints for you - do NOT include in output)
     - `rules`: Artifact-specific rules (constraints for you - do NOT include in output)
     - `template`: The structure to use for your output file
     - `instruction`: Schema-specific guidance
     - `outputPath`: Where to write the artifact
     - `dependencies`: Completed artifacts to read for context
   - **Create the artifact file**:
     - Read any completed dependency files for context
     - If the ready artifact ID is `prd`, first inspect the recent conversation context for an `Overmind Context` block produced by `sdd-new-change`
     - Only use that block if its `change` field matches the current change name
     - If matched, treat `title`, `summary`, `detail`, and `child_issues` as primary requirement input for `PRD.md`
     - Briefly announce: `Using retained Overmind context for <name>.`
     - Use `template` as the structure - fill in its sections
     - Apply `context` and `rules` as constraints when writing - but do NOT copy them into the file
     - For Overmind-seeded `PRD.md`, create a best-effort draft immediately; use `[待补充]` to标记未知细节，而不是因为信息不完整而停住
     - Do NOT paste the raw `Overmind Context` block into the artifact; synthesize it into the PRD sections
     - Write to the output path specified in instructions
   - Show what was created and what's now unlocked
   - STOP after creating ONE artifact

   ---

   **If no artifacts are ready (all blocked)**:
   - This shouldn't happen with a valid schema
   - Show status and suggest checking for issues

4. **Transition Spec Tracker stage (if context available)**

   After creating the artifact, check the conversation for a `Spec Tracker Context` block from `sdd-new-change`.
   If found, transition to the corresponding stage based on the artifact just created:

   | Artifact ID | Stage |
   |-------------|-------|
   | `prd` | `spec-prd` |
   | `specs` | `spec-specs` |
   | `findings` | `spec-findings` |
   | `design` | `spec-design` |
   | `task` / `tasks` | `spec-task` |

   ```bash
   raven spec-tracker transition --spec-id "<spec-id>" --to-stage "<stage>" --remark "artifact: <artifact-id>"
   ```
   - If the transition command fails, log a warning and continue — do NOT block the workflow
   - If no `Spec Tracker Context` is found, skip this step silently

5. **After creating an artifact, show progress**
   ```bash
   raven spec status --change "<name>"
   ```

**Output**

After each invocation, show:
- Which artifact was created
- Schema workflow being used
- Current progress (N/M complete)
- What artifacts are now unlocked
- Prompt: "Want to continue? Just ask me to continue or tell me what to do next."

**Artifact Creation Guidelines**

The artifact types and their purpose depend on the schema. Use the `instruction` field from the instructions output to understand what to create.

Common artifact patterns:

**Repository `sdd` schema** (`prd` → `specs` → `findings` → `design` → `task`):
- **PRD.md**: Ask user about the change if not clear. Fill in 需求概述、核心功能、用户场景、边界条件、验收标准、Capabilities.
  - If a matched `Overmind Context` block is available, use it as the primary input when drafting `PRD.md`
  - Use `detail` to inform需求背景、核心功能、用户场景 and边界条件
  - Use `child_issues` to help identify concrete功能点 and candidate Capabilities
  - If the Overmind material is incomplete but scope is still understandable, draft the PRD now and mark unresolved items as `[待补充]`
- **specs/<capability>/spec.md**: Create one spec per capability listed in the PRD Capabilities section (use the capability name, not the change name).
- **FINDINGS.md**: Record technical decisions, pitfalls, and change notes discovered while planning and implementation progress.
- **DESIGN.md**: Document technical decisions, architecture, and implementation approach.
- **TASK.md**: Break down implementation into checkboxed tasks.

For other schemas, follow the `instruction` field from the CLI output.

**Guardrails**
- Create ONE artifact per invocation
- Always read dependency artifacts before creating a new one
- Never skip artifacts or create out of order
- If context is unclear, ask the user before creating
- Verify the artifact file exists after writing before marking progress
- Use the schema's artifact sequence, don't assume specific artifact names
- **IMPORTANT**: `context` and `rules` are constraints for YOU, not content for the file
  - Do NOT copy `<context>`, `<rules>`, `<project_context>` blocks into the artifact
  - These guide what you write, but should never appear in the output
- If this skill encounters unexpected errors or is unable to complete the workflow, suggest the user run `/sdd-feedback` to report the issue. Include context: which skill failed, what step it was on, the error message, and the change name if available.
