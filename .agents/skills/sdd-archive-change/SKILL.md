---
name: sdd-archive-change
description: 在实验性工作流中归档已完成变更。适用于实现完成后需要收尾归档的场景。英文：Archive a completed change in the experimental workflow. Use when the user wants to finalize and archive a change after implementation is complete.
license: MIT
compatibility: Requires raven CLI.
metadata:
  author: raven
  version: "1.1"
  generatedBy: "1.0.2"
---

Archive a completed change in the experimental workflow.

**Input**: Optionally specify a change name. If omitted, check if it can be inferred from conversation context. If vague or ambiguous you MUST prompt for available changes.

**Steps**

1. **If no change name provided, prompt for selection**

   Run `raven spec list --json` to get available changes. Use the **AskUserQuestion tool** to let the user select.

   Show only active changes (not already archived).
   Include the schema used for each change if available.

   **IMPORTANT**: Do NOT guess or auto-select a change. Always let the user choose.

2. **Check artifact completion status**

   Run `raven spec status --change "<name>" --json` to check artifact completion.

   Parse the JSON to understand:
   - `schemaName`: The workflow being used
   - `artifacts`: List of artifacts with their status (`done` or other)

   **If any artifacts are not `done`:**
   - Display warning listing incomplete artifacts
   - Use **AskUserQuestion tool** to confirm user wants to proceed
   - Proceed if user confirms

3. **Check task completion status**

   Read the tasks file (typically `tasks.md`) to check for incomplete tasks.

   Count tasks marked with `- [ ]` (incomplete) vs `- [x]` (complete).

   **If incomplete tasks found:**
   - Display warning showing count of incomplete tasks
   - Use **AskUserQuestion tool** to confirm user wants to proceed
   - Proceed if user confirms

   **If no tasks file exists:** Proceed without task-related warning.

4. **Assess delta spec sync state**

   Check for delta specs at `ravenspec/changes/<name>/specs/`. If none exist, proceed without sync prompt.

   **If delta specs exist:**
   - Compare each delta spec with its corresponding main spec at `ravenspec/specs/<capability>/spec.md`
   - Determine what changes would be applied (adds, modifications, removals, renames)
   - Show a combined summary before prompting

   **Prompt options:**
   - If changes needed: "Sync now (recommended)", "Archive without syncing"
   - If already synced: "Archive now", "Sync anyway", "Cancel"

   If user chooses sync, execute `sdd-sync-specs` logic. Proceed to archive regardless of choice.

5. **Perform the archive**

   Create the archive directory if it doesn't exist:
   ```bash
   mkdir -p ravenspec/changes/archive
   ```

   Generate target name using current date: `YYYY-MM-DD-<change-name>`

   **Check if target already exists:**
   - If yes: Fail with error, suggest renaming existing archive or using different date
   - If no: Move the change directory to archive

   ```bash
   mv ravenspec/changes/<name> ravenspec/changes/archive/YYYY-MM-DD-<name>
   ```

6. **Transition Spec Tracker to completed (if context available)**

   Check the conversation for a `Spec Tracker Context` block from `sdd-new-change`.
   If found, transition to `spec-completed`:
   ```bash
   raven spec-tracker transition --spec-id "<spec-id>" --to-stage "spec-completed" --remark "change archived"
   ```
   - If the command fails, log a warning and continue — do NOT block the workflow
   - If no `Spec Tracker Context` is found, skip this step silently

7. **Display summary**

   Show archive completion summary including:
   - Change name
   - Schema that was used
   - Archive location
   - Whether specs were synced (if applicable)
   - Note about any warnings (incomplete artifacts/tasks)

**Output On Success**

```
## Archive Complete

**Change:** <change-name>
**Schema:** <schema-name>
**Archived to:** ravenspec/changes/archive/YYYY-MM-DD-<name>/
**Specs:** ✓ Synced to main specs (or "No delta specs" or "Sync skipped")

All artifacts complete. All tasks complete.
```

7. **Suggest Feedback**

   After archive completes successfully, suggest submitting feedback if issues were encountered:

   > 变更已归档。如果本次变更过程中遇到了问题（skill 指引不准、MCP 工具异常、工作流步骤设计不合理等），可以运行 `/sdd-feedback <change-name>` 将反馈提交给平台，帮助持续改进。

**Guardrails**
- Always prompt for change selection if not provided
- Use artifact graph (raven spec status --json) for completion checking
- Don't block archive on warnings - just inform and confirm
- Preserve .ravenspec.yaml when moving to archive (it moves with the directory)
- Show clear summary of what happened
- If sync is requested, use sdd-sync-specs approach (agent-driven)
- If delta specs exist, always run the sync assessment and show the combined summary before prompting
