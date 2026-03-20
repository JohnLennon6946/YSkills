---
name: sdd-ff-change
description: 快速推进 artifact 创建。适用于用户希望不逐步交互，快速生成实现前所需全部 artifact 的场景。英文：Fast-forward through artifact creation. Use when the user wants to quickly create all artifacts needed for implementation without stepping through each one individually.
license: MIT
compatibility: Requires raven CLI.
metadata:
  author: raven
  version: "1.1"
  generatedBy: "1.0.2"
---

Fast-forward through artifact creation - generate everything needed to start implementation in one go.

**Input**: The user's request should include a change name (kebab-case) OR a description of what they want to build.

**Steps**

1. **If no clear input provided, ask what they want to build**

   Use the **AskUserQuestion tool** (open-ended, no preset options) to ask:
   > "What change do you want to work on? Describe what you want to build or fix."

   From their description, derive a kebab-case name (e.g., "add user authentication" → `add-user-auth`).

   **IMPORTANT**: Do NOT proceed without understanding what the user wants to build.

2. **Create the change directory**
   ```bash
   raven spec new change "<name>"
   ```
   This creates a scaffolded change at `ravenspec/changes/<name>/`.

3. **Register with Spec Tracker**

   Generate a unique spec-id and register this change:
   ```bash
   SPEC_ID=$(raven spec-tracker gen-id)
   raven spec-tracker create --spec-id "$SPEC_ID"
   raven spec-tracker transition --spec-id "$SPEC_ID" --to-stage "spec-new" --remark "change created"
   ```
   - If the command fails, log a warning and continue — do NOT block the workflow
   - Store the `SPEC_ID` for use in subsequent transition calls

4. **Get the artifact build order**
   ```bash
   raven spec status --change "<name>" --json
   ```
   Parse the JSON to get:
   - `applyRequires`: array of artifact IDs needed before implementation (e.g., `["tasks"]`)
   - `artifacts`: list of all artifacts with their status and dependencies

5. **Create artifacts in sequence until apply-ready**

   Use the **TodoWrite tool** to track progress through the artifacts.

   Loop through artifacts in dependency order (artifacts with no pending dependencies first):

   a. **For each artifact that is `ready` (dependencies satisfied)**:
      - Get instructions:
        ```bash
        raven spec instructions <artifact-id> --change "<name>" --json
        ```
      - The instructions JSON includes:
        - `context`: Project background (constraints for you - do NOT include in output)
        - `rules`: Artifact-specific rules (constraints for you - do NOT include in output)
        - `template`: The structure to use for your output file
        - `instruction`: Schema-specific guidance for this artifact type
        - `outputPath`: Where to write the artifact
        - `dependencies`: Completed artifacts to read for context
      - Read any completed dependency files for context
      - Create the artifact file using `template` as the structure
      - Apply `context` and `rules` as constraints - but do NOT copy them into the file
      - Show brief progress: "✓ Created <artifact-id>"
      - **Transition Spec Tracker**: If `SPEC_ID` was generated in step 3, transition to the corresponding stage:

        | Artifact ID | Stage |
        |-------------|-------|
        | `prd` | `spec-prd` |
        | `specs` | `spec-specs` |
        | `findings` | `spec-findings` |
        | `design` | `spec-design` |
        | `task` / `tasks` | `spec-task` |

        ```bash
        raven spec-tracker transition --spec-id "$SPEC_ID" --to-stage "<stage>" --remark "artifact: <artifact-id>"
        ```
        If the transition fails, log a warning and continue.

   b. **Continue until all `applyRequires` artifacts are complete**
      - After creating each artifact, re-run `raven spec status --change "<name>" --json`
      - Check if every artifact ID in `applyRequires` has `status: "done"` in the artifacts array
      - Stop when all `applyRequires` artifacts are done

   c. **If an artifact requires user input** (unclear context):
      - Use **AskUserQuestion tool** to clarify
      - Then continue with creation

6. **Show final status**
   ```bash
   raven spec status --change "<name>"
   ```

**Output**

After completing all artifacts, summarize:
- Change name and location
- List of artifacts created with brief descriptions
- What's ready: "All artifacts created! Ready for implementation."
- Include a `Spec Tracker Context` block if spec-id was generated:
  ```yaml
  Spec Tracker Context:
    spec-id: <the generated spec-id>
    change: <change-name>
    overmind-url: <empty>
  ```
- Prompt: "Run `sdd-apply-change` or ask me to implement to start working on the tasks."

**Artifact Creation Guidelines**

- Follow the `instruction` field from `raven spec instructions` for each artifact type
- The schema defines what each artifact should contain - follow it
- Read dependency artifacts for context before creating new ones
- Use `template` as the structure for your output file - fill in its sections
- **IMPORTANT**: `context` and `rules` are constraints for YOU, not content for the file
  - Do NOT copy `<context>`, `<rules>`, `<project_context>` blocks into the artifact
  - These guide what you write, but should never appear in the output

**Guardrails**
- Create ALL artifacts needed for implementation (as defined by schema's `apply.requires`)
- Always read dependency artifacts before creating a new one
- If context is critically unclear, ask the user - but prefer making reasonable decisions to keep momentum
- If a change with that name already exists, suggest continuing that change instead
- Verify each artifact file exists after writing before proceeding to next
- If this skill encounters unexpected errors or is unable to complete the workflow, suggest the user run `/sdd-feedback` to report the issue. Include context: which skill failed, what step it was on, the error message, and the change name if available.
