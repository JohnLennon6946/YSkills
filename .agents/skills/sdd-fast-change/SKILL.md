---
name: sdd-fast-change
description: 快速模式变更流程 - 适用于小改动（bug fix、配置变更、文案修改、单文件重构等）。将完整 SDD 的 5 个 artifact 压缩为 1 个 CHANGE.md，从描述到实现 5 分钟内完成。英文：Fast mode for small changes. Use when the user wants a lightweight workflow for bug fixes, config changes, copy edits, or single-file refactors. Compresses full SDD into a single CHANGE.md. Use proactively whenever the change sounds small, simple, or quick - even if the user doesn't explicitly say "fast mode".
license: MIT
compatibility: Requires raven CLI.
metadata:
  author: raven
  version: "1.0"
  generatedBy: "1.0.2"
---

Fast mode for small changes — explore, plan, confirm, implement, and wrap up in one streamlined flow.

**Input**: The user's request should include a change name (kebab-case) OR a description of what they want to fix/change.

**Steps**

1. **If no clear input provided, ask what they want to change**

   Use the **AskUserQuestion tool** (open-ended, no preset options) to ask:
   > "What do you want to fix or change? Describe the issue or improvement."

   From their description, derive a kebab-case name (e.g., "fix login button in dark mode" → `fix-dark-mode-login-btn`).

   **IMPORTANT**: Do NOT proceed without understanding what the user wants to change.

2. **Create the change directory**
   ```bash
   raven spec new change "<name>" --schema fast
   ```
   This creates a scaffolded change at `ravenspec/changes/<name>/` with the `fast` schema.

   **If the change already exists**: Check if it uses the `fast` schema. If yes, suggest continuing that change. If it uses a different schema, inform the user and ask how to proceed.

3. **Explore the codebase (automatic, read-only)**

   Based on the user's description, search for related code to understand the current state:

   a. **Code search**: Use Grep/Glob to find files related to the issue
   b. **Context collection**: Read relevant code snippets to understand the current implementation
   c. **Impact assessment**: Identify which files will likely need changes and how many

   Keep this phase focused and quick — spend at most a few searches. The goal is to inform the plan, not to exhaustively map the codebase.

4. **Complexity check**

   After exploration, assess whether FastMode is appropriate for this change:

   **FastMode is a good fit when:**
   - Estimated files to change ≤ 5
   - Changes are within a single module or closely related modules
   - No new public APIs needed
   - The fix/change is well-understood after exploration

   **If the change looks too complex** (estimated files > 5, cross-module changes, new public APIs, or architectural decisions needed):

   Use the **AskUserQuestion tool** to present:
   > "This change appears more complex than typical FastMode scope (involves N files across M modules). How would you like to proceed?"

   Options:
   - "Continue with FastMode" — proceed as-is
   - "Upgrade to full SDD workflow" — see Upgrade Flow below

   If the user chooses to upgrade, follow the **Upgrade Flow** at the bottom of this document.

5. **Generate CHANGE.md**

   Get the artifact instructions:
   ```bash
   raven spec instructions change --change "<name>" --json
   ```

   The instructions JSON includes:
   - `context`: Project background (constraints for you - do NOT include in output)
   - `rules`: Artifact-specific rules (constraints for you - do NOT include in output)
   - `template`: The structure to use for your output file
   - `instruction`: Schema-specific guidance for this artifact type
   - `outputPath`: Where to write the artifact

   Based on exploration results and the template, fill in CHANGE.md:

   - **What**: One clear sentence describing the change — no ambiguity
   - **Why**: Background and motivation, link to issue/feedback if available
   - **How**: 1-5 concrete implementation steps, each naming specific files or modules
   - **Specs Changed**: List affected specs if the change modifies existing spec behavior. Format: `<spec-name>` (MODIFIED/REMOVED). Write "无" if no specs are affected
   - **Files Changed**: Predicted files with brief descriptions (will be updated after implementation)
   - **Verification**: Checkbox items that can be independently verified

   **IMPORTANT**: `context` and `rules` are constraints for YOU, not content for the file. Do NOT copy `<context>`, `<rules>`, `<project_context>` blocks into CHANGE.md.

6. **Create delta specs (if needed)**

   If the Specs Changed section in CHANGE.md is not empty or "无", create delta spec files for each listed capability:

   a. Read the `specs` artifact's `instruction` and `template` from the spec-driven schema:
      ```bash
      raven spec instructions specs --change "<name>" --schema spec-driven --json
      ```
      Use the `instruction` field as your guide for delta spec format and the `template` field as the file structure.

   b. For each `<spec-name>` in Specs Changed, read the main spec at `ravenspec/specs/<spec-name>/spec.md` to understand existing requirements.

   c. Create the delta spec at `ravenspec/changes/<name>/specs/<spec-name>/spec.md` following the instruction.

   If Specs Changed is empty or "无", skip this step entirely.
   If creating delta specs fails, proceed anyway — delta specs are recommended but not blocking.

7. **Present plan and get user confirmation**

   Display the generated CHANGE.md content and ask the user to confirm.

   Use the **AskUserQuestion tool** with options:

   - "Confirm and implement" — proceed to implementation
   - "Edit the plan" — follow the **Edit Flow** below
   - "Upgrade to SDD" — follow the **Upgrade Flow** below
   - "Cancel" — delete the change directory and stop

   After edits (if any), re-read CHANGE.md before proceeding.

   **Edit Flow**:

   1. Check if the `/plannotator-annotate` skill is available in the current environment
   2. If available: invoke `/plannotator-annotate` on the CHANGE.md file for interactive annotation review
   3. If not available: show the file path (`ravenspec/changes/<name>/CHANGE.md`) and wait for the user to edit it manually
   4. After review/edit completes, re-read CHANGE.md, address any feedback, update the file if needed
   5. Re-present CHANGE.md for confirmation (loop back to the options above)

8. **Implement the change**

   After confirmation, execute the implementation:

   a. Follow the How steps in CHANGE.md sequentially
   b. Make the code changes required for each step
   c. Keep changes minimal and focused on the stated goal

   After implementation:
   d. Update the **Files Changed** section with actual files modified (paths, operations, line counts)
   e. Run through **Verification** items — check off items that can be verified automatically (e.g., tests pass, build succeeds)
   f. For items requiring manual verification, leave them unchecked and note they need manual check

   **If an issue arises during implementation:**
   - Pause and explain the issue to the user
   - If it's a minor obstacle, suggest a fix and continue
   - If it reveals the change is more complex than expected, offer to upgrade to SDD

9. **Wrap up**

   After implementation is complete, show a summary:

   ```
   ## FastMode Complete

   **Change:** <name>
   **Files Modified:**
     M path/to/file.ts (+N -M)
     M path/to/other.ts (+N -M)

   **Verification:**
     ✅ Test passes
     ⬜ Manual check needed: <description>
   ```

   Then use the **AskUserQuestion tool** to ask about next steps:

   - "Archive this change" — invoke `sdd-archive-change` for the change
   - "Delete change files (keep code changes only)" — run `rm -rf ravenspec/changes/<name>` to clean up the change directory while preserving the actual code changes
   - "Skip for now" — leave everything as-is for later handling

---

**Upgrade Flow**

When the user chooses to upgrade from FastMode to full SDD at any point:

1. Read the current CHANGE.md content (if it exists) and save it as context
2. Delete the fast change directory:
   ```bash
   rm -rf ravenspec/changes/<name>
   ```
3. Pass the CHANGE.md content as context and invoke `sdd-ff-change` with the same change name:
   - The What/Why sections inform the PRD
   - The How/Files Changed sections inform the DESIGN
   - The Specs Changed section informs the capability declarations
4. Inform the user: "Upgraded to SDD workflow. The FastMode plan has been carried over as context."

This reuses the existing SDD creation flow entirely — no manual field mapping needed.

---

**Guardrails**

- Always use `--schema fast` when creating the change
- CHANGE.md is the only required artifact — keep the process lightweight
- If Specs Changed lists affected specs, create delta spec files in Step 6 before confirmation. Archive will auto-discover and sync them. Don't block on failure.
- Prefer making reasonable decisions over asking too many questions — this is fast mode, momentum matters
- If a change with that name already exists, suggest continuing it rather than creating a new one
- Verify CHANGE.md exists after writing before proceeding to implementation
- The upgrade path should feel seamless — the user shouldn't have to re-explain anything
