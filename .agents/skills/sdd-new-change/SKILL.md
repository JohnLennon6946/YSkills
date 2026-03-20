---
name: sdd-new-change
description: 基于实验性 artifact 工作流创建新的变更。适用于用户希望以结构化步骤创建新功能、修复或修改的场景。英文：Start a new change using the experimental artifact workflow. Use when the user wants to create a new feature, fix, or modification with a structured step-by-step approach.
license: MIT
compatibility: Requires raven CLI.
metadata:
  author: raven
  version: "1.7"
  generatedBy: "1.0.2"
---

Start a new change using the experimental artifact-driven approach.

**Input**: The user's request should include one of:
- A change name (kebab-case)
- A description of what they want to build
- An Overmind requirement URL like `https://music-overmind.hz.netease.com/1/requirement/issues/OMMUSIC-3327089`
- A Popo document link like `https://docs.popo.netease.com/...`

**Steps**

1. **Detect whether the input is an Overmind requirement URL**

   If the input matches:
   `https://music-overmind.hz.netease.com/1/requirement/issues/OMMUSIC-<digits>`

   then follow the Overmind flow below:

   a. Extract `issueKey` from the URL, for example `OMMUSIC-3327089`.

   b. Use the Bash tool to call the Raven API to fetch issue detail:
      ```bash
      curl -s "https://raven.netease.com/api/raven/monitor/overmind/issue-detail?issueKey=<issueKey>"
      ```
      The response JSON contains: `title`, `desc` (HTML), `statusName`, `sprintName`, etc.
      - Use `title` as the issue title
      - Convert `desc` from HTML to plain text for the Overmind Context `detail` field
      - `child_issues` should be left empty (the API does not return child issues)

   c. Derive a kebab-case change name from the issue title.
      Example: `UI 截图能力补充` → `ui-screenshot-update`

   d. If the title cannot be read or the derived name is unclear, ask the user for a kebab-case change name.

   e. Create the change directory:
   ```bash
   raven spec new change "<name>"
   ```

   Add `--schema <name>` only if the user explicitly requested a non-default workflow.

   f. Update `ravenspec/changes/<name>/.ravenspec.yaml` by preserving existing fields and appending:
   ```yaml
   source:
     type: overmind
     issueKey: OMMUSIC-3327089
     url: https://music-overmind.hz.netease.com/1/requirement/issues/OMMUSIC-3327089
   ```

   g. If `<name>` already exists:
   - read `ravenspec/changes/<name>/.ravenspec.yaml`
   - if `source.url` matches the current Overmind URL, suggest continuing that change instead of creating a new one
   - otherwise ask the user for another kebab-case name and retry

   h. Continue with Step 5 below.

2. **Detect whether the input contains a Popo document link**

   If the input contains a URL matching `https://docs.popo.netease.com/...`, use the `popo-doc-read` skill to read the document content. The extracted text can serve as supplementary requirement context:
   - If combined with an Overmind URL, append the document content to the `detail` field of the Overmind Context block.
   - If used alone (no Overmind URL), derive a kebab-case change name from the document title or content, then continue with Step 4 below.

3. **If no clear input provided, ask what they want to build**

   Use the **AskUserQuestion tool** (open-ended, no preset options) to ask:
   > "What change do you want to work on? Describe what you want to build or fix."

   From their description, derive a kebab-case name (e.g., "add user authentication" → `add-user-auth`).

   **IMPORTANT**: Do NOT proceed without understanding what the user wants to build.

4. **Determine the workflow schema**

   Use the default schema (omit `--schema`) unless the user explicitly requests a different workflow.

   **Use a different schema only if the user mentions:**
   - A specific schema name → use `--schema <name>`
   - "show workflows" or "what workflows" → run `raven spec schemas --json` and let them choose

   **Otherwise**: Omit `--schema` to use the default.

5. **Create the change directory**
   ```bash
   raven spec new change "<name>"
   ```
   Add `--schema <name>` only if the user requested a specific workflow.
   This creates a scaffolded change at `ravenspec/changes/<name>/` with the selected schema.

6. **Show the artifact status**
   ```bash
   raven spec status --change "<name>"
   ```
   This shows which artifacts need to be created and which are ready (dependencies satisfied).

7. **Register with Spec Tracker**

   Generate a unique spec-id and register this change with the spec tracker:
   ```bash
   SPEC_ID=$(raven spec-tracker gen-id)
   raven spec-tracker create --spec-id "$SPEC_ID" [--overmind-url "<url>"]
   raven spec-tracker transition --spec-id "$SPEC_ID" --to-stage "spec-new" --remark "change created"
   ```
   - Always generate a new spec-id per change (even if the same Overmind URL was used before)
   - Include `--overmind-url` only if this change was created from an Overmind URL
   - If the command fails (e.g., not logged in), log a warning and continue — do NOT block the workflow

8. **Get instructions for the first artifact**
   The first artifact depends on the schema (e.g., `prd` in this repository's `sdd` schema).
   Check the status output to find the first artifact with status "ready".
   ```bash
   raven spec instructions <first-artifact-id> --change "<name>" --json
   ```
   This outputs the template and context for creating the first artifact.

9. **STOP and wait for user direction**

**Output**

After completing the steps, summarize:
- Change name and location
- Schema/workflow being used and its artifact sequence
- Overmind source link if this change was created from an Overmind URL
- Current status (0/N artifacts complete)
- The template for the first artifact
- If created from Overmind URL, include a structured `Overmind Context` block for the next skill call in the same conversation. Use this exact field layout:
  ```yaml
  Overmind Context:
    change: <change-name>
    issueKey: <issue-key>
    url: <overmind-url>
    title: <requirement-title-or-empty>
    summary: <short-summary-or-empty>
    detail: |
      <normalized requirement detail for downstream PRD creation>
    child_issues:
      - <type>: <title> [<status>]
    artifact_target: prd
  ```
  - `detail` should be normalized plain text, not raw API JSON
  - `child_issues` may be empty if nothing is returned
  - State explicitly that this block is intended for the next `sdd-continue-change` call in the same conversation, and that `sdd-continue-change` will prioritize it when creating `PRD.md`
- Prompt: "Ready to create the first artifact? Just describe what this change is about and I'll draft it, or ask me to continue."
- Always include a structured `Spec Tracker Context` block for downstream skills in the same conversation:
  ```yaml
  Spec Tracker Context:
    spec-id: <the generated spec-id>
    change: <change-name>
    overmind-url: <overmind-url or empty>
  ```
  - This block is used by `sdd-continue-change`, `sdd-apply-change`, `sdd-verify-change`, `sdd-archive-change` to automatically transition spec-tracker stages
  - State explicitly that downstream skills should read this block to track progress

**Guardrails**
- Do NOT create any artifacts yet - just show the instructions
- Do NOT advance beyond showing the first artifact template
- If the name is invalid (not kebab-case), ask for a valid name
- If a change with that name already exists, suggest continuing that change instead
- For Overmind input, only support the full requirement URL format above; do not accept a bare issueKey in this workflow
- Only emit the `Overmind Context` block for Overmind-based input
- Do NOT dump raw Overmind JSON; summarize it into stable plain-text fields that the next skill can reuse
- Pass --schema if using a non-default workflow
