---
name: feedback
description: 帮助用户总结当前遇到的问题或收集改进建议，通过对话引导收集上下文后提交反馈工单。适用于用户在编码过程中遇到问题或有改进想法时使用。英文：Help users summarize their current problem or collect improvement suggestions, guide context collection through conversation and submit feedback tickets. Use when users encounter issues or have improvement ideas during coding.
license: MIT
compatibility: Requires raven CLI.
metadata:
  author: raven
  version: "1.0"
  generatedBy: "1.0.2"
---

Help the user submit a feedback ticket by collecting context through conversation.

**This skill guides, not interrogates.** Collect information naturally from the conversation, auto-detect what you can, and only ask for what's missing.

---

## Step 1: Identify feedback type

Determine whether this is an **issue** (bug/problem) or a **suggestion** (feature request/improvement) based on the conversation context and what the user said. You should be able to judge this automatically in most cases — do NOT ask the user to classify it. Only if the context is truly ambiguous and you cannot determine it at all, then ask.

---

## Step 2: Collect context

**For issues:**

1. Auto-detect environment info by running:
   ```bash
   echo "OS: $(uname -s) $(uname -m)" && echo "Node: $(node -v 2>/dev/null || echo 'N/A')" && echo "raven: $(raven --version 2>/dev/null || echo 'N/A')"
   ```
2. From the conversation, extract or ask for:
   - What happened (actual behavior)
   - What was expected
   - Steps to reproduce (if not obvious)
   - Any error messages or logs
3. Assess severity based on user's description:
   - `critical` — system crash, data loss
   - `major` — key feature broken, no workaround
   - `minor` — feature broken but has workaround
   - `trivial` — cosmetic issue

**For suggestions:**
1. Understand what the user wants improved or added
2. Ask for context on why this would be useful (if not already clear)

---

## Step 3: Draft the ticket

Compose a structured summary:

- **Title**: Concise, under 100 characters (Chinese OK)
- **Description**: Markdown-formatted, including:
  - For issues: environment, reproduction steps, expected vs actual behavior, error logs
  - For suggestions: current situation, proposed improvement, expected benefit
- **Priority**: Suggest based on impact:
  - `P0` — production down, affects all users
  - `P1` — major feature broken, affects many users
  - `P2` — normal issue or useful suggestion (default)
  - `P3` — minor/cosmetic issue or nice-to-have suggestion
- **Tags**: Relevant labels (e.g., `raven-cli`, `skills`, `web`, `server`)

---

## Step 4: Confirm with user

Use the **AskUserQuestion tool** to present the draft and ask for confirmation:

> **即将提交以下反馈工单：**
>
> - 类型：issue / suggestion
> - 标题：{title}
> - 优先级：{priority}
> - 标签：{tags}
>
> **描述：**
> {description}
>
> 请确认是否提交？你也可以告诉我需要修改的地方。

If the user wants changes, adjust and re-confirm. If the user wants to cancel, stop here.

---

## Step 5: Submit via CLI

Once confirmed, run:

```bash
raven tickets create \
  --type {issue|suggestion} \
  --title "{title}" \
  --description "{description}" \
  --priority {P0|P1|P2|P3} \
  --tags "{tag1},{tag2}"
```

After successful submission, show the ticket number and a link to view it:
> 工单已提交！工单号：{ticket_no}
> 查看详情：https://raven.hz.netease.com/st/sdd/feedback/detail?id={id}

---

## Guardrails

- **NEVER submit a ticket without user confirmation** — always go through Step 4
- Do NOT ask the user to fill in a form — extract information from conversation naturally
- For issues, always attempt auto-detection of environment info before asking
- Default priority is P2 unless the situation clearly warrants higher/lower
- Title must be under 200 characters
- If `raven tickets` command fails (auth error), guide the user to run `raven login` first
