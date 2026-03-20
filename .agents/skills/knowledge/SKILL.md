---
name: knowledge
description: 将对话中的经验沉淀为团队知识（rule / solution / doc / runbook / skill）
user_invocable: true
---

# Knowledge 沉淀流程

当用户希望将对话中的经验、解决方案或最佳实践保存为团队知识时，按以下流程执行。

## 长文本参数处理

当 `--content`、`--summary`、`--new-scope` 等参数内容较长时，先写入临时文件再用 `@filepath` 语法引用，避免命令行过长被 Claude Code 拦截：

1. 将长文本内容写入临时文件（如 `/tmp/kb-content.md`）
2. 使用 `@` 前缀引用：`--content @/tmp/kb-content.md`

## 知识类型

共 5 种类型，按「生效方式」区分：

| 类型 | 用途 | 生效方式 |
|------|------|----------|
| `rule` | 编码约束、架构决策、团队规范 | 常驻生效，写入 CLAUDE.md |
| `solution` | 问题的解法，统一为「问题 → 解法」结构 | 按需检索 |
| `doc` | 参考文档：架构说明、API 速查、模块介绍 | 按需阅读 |
| `runbook` | 标准化操作步骤 | 逐步执行 |
| `skill` | 可复用的 agent skill，多文件打包 | 安装扩展 |

## 执行步骤

### Step 0: 回顾本地 instinct（可选）

在从对话中提取知识之前，先检查是否有已积累的本地 instinct 可以提炼：

```bash
raven instinct status
```

如果有高置信度（≥70%）的 instinct：

1. 按 `promotion_hint` 分组展示：
   - 🏠 **project-rule** — 项目特定的模式，适合提炼为本地 rule
   - 🌐 **cross-project** — 跨项目共性，适合上传团队知识库

2. 询问用户是否要从 instinct 提炼知识：
   - **是** → 选择一条或一组相关 instinct，进入提炼流程：
     - AI 基于 instinct 的 trigger/action/evidence 生成结构化 rule 或 skill
     - 用户确认/编辑内容
     - project-rule → 写入 `.claude/rules/<name>.md` 或追加到 CLAUDE.md
     - cross-project → 先写入本地，然后用 `raven knowledge create` 提交到团队知识库
   - **否** → 继续 Step 1，从当前对话中提取知识

如果没有 instinct 或用户跳过，直接进入 Step 1。

#### instinct 提炼为 rule 示例

```bash
# 1. 查看 instinct 详情
raven instinct status --json

# 2. 提炼为 rule 草案
raven instinct evolve --generate

# 3. 确认后上传团队知识库
raven knowledge create --type rule --title "<title>" --content "$(cat /tmp/rule-draft.md)" --scope "<scope>"
```

#### instinct 提炼为 skill 示例

```bash
# 1. 基于多个相关 instinct 构建 skill 目录
mkdir -p /tmp/my-skill
# ... 编写 SKILL.md 和辅助文件 ...

# 2. 提交
raven knowledge create --type skill --dir /tmp/my-skill
```

### Step 1: 分析知识来源

回顾当前对话，识别可沉淀的知识点：
- 解决了什么问题？
- 采用了什么方案？
- 有哪些关键决策或约束？
- 是否有可复用的模式？

### Step 2: 用户选择

向用户确认：
1. 要沉淀的知识点是什么？
2. 建议的知识类型（从 5 种中推荐最合适的）
3. 建议的标题

### Step 3: 结构化整理

根据用户选择的类型，按对应格式整理内容：

**rule** — 编码约束、架构决策、团队规范：
```markdown
## 规则名称

**约束**: 简明描述必须遵守的规则

**原因**: 为什么要这样做

**示例**:
// 正确
...
// 错误
...
```

**solution** — 问题 → 解法：
```markdown
## 问题描述

简明描述遇到的问题和上下文。

## 解法

具体的解决步骤和代码。

## 原理

为什么这个解法有效。
```

**doc** — 参考文档：
```markdown
## 概述

模块/API/架构的简要说明。

## 详细内容

...

## 常见用法

...
```

**runbook** — 标准化操作步骤：
```markdown
## 目标

本 runbook 完成什么任务。

## 前置条件

- ...

## 步骤

1. ...
2. ...
3. ...

## 验证

如何确认操作成功。
```

**skill** — 可复用的 agent skill（多文件打包）：
```markdown
# Skill 名称

## 功能描述

...

## 包含文件

- SKILL.md — 主入口
- helper.md — 辅助说明
- ...
```

### Step 4: 确认内容

将整理好的内容展示给用户，确认：
- 内容是否准确完整
- 类型是否正确
- 标题是否合适
- 是否需要补充或修改

### Step 4.5: 查重（Upsert 判断）

在提交前，先查找是否已有相似知识条目：

```bash
raven knowledge match --type <type> --title "<title>" --summary "<summary>" --json
```

根据返回结果：

**如果 `matched: true`**（找到相似条目）：

向用户展示匹配结果列表（ID、标题、摘要、状态），并询问：

> 发现以下相似知识条目，请选择操作：
> - A) **更新条目 #<id>** — 将新内容合并到已有条目（调用 `raven knowledge update`）
> - B) **新建条目** — 确认这是不同的知识，继续新建
> - C) **放弃** — 取消本次沉淀

- 选择 A：跳到 Step 5 的「更新模式」
- 选择 B：跳到 Step 5 的「新建模式」
- 选择 C：结束流程

**如果 `matched: false`**（无相似条目）：

直接进入 Step 5 新建模式。

### Step 5: 提交知识

**重要：内容较长时，必须先写入临时文件再提交，避免命令行参数中的特殊字符（如 `#`、换行）触发安全检查。**

#### 方式一：目录模式（推荐，适用于所有类型）

所有知识类型均支持 `--dir` 模式。目录中包含 `raven.json` 时，可从中自动读取 title/summary/tags/repo 等元数据。

```bash
# 1. 准备目录结构
mkdir -p /tmp/raven-knowledge

# 2. 写入元数据文件 raven.json
cat > /tmp/raven-knowledge/raven.json << 'EOF'
{
  "kb": {
    "type": "<type>",
    "title": "<title>",
    "summary": "<summary>",
    "tags": ["tag1", "tag2"]
  }
}
EOF

# 3. 写入内容文件（非 skill 类型用 content.md，skill 类型用 SKILL.md）
cat > /tmp/raven-knowledge/content.md << 'EOF'
知识正文内容...
EOF

# 4. 提交（有 raven.json 时 title/summary/tags 可省略）
raven knowledge create --type <type> --dir /tmp/raven-knowledge

# 5. 清理
rm -rf /tmp/raven-knowledge
```

#### 方式二：单文件模式（简单场景）

推荐方式（Write 工具写临时文件 + `$(cat)` 读取）：

```bash
# 1. 先用 Write 工具将内容写入临时文件 /tmp/raven-knowledge-content.md
# 2. 然后执行：
raven knowledge create --type <type> --title "<title>" --summary "<summary>" --tags "<tag1,tag2>" --content "$(cat /tmp/raven-knowledge-content.md)"
# 3. 清理临时文件
rm /tmp/raven-knowledge-content.md
```

也可以通过 stdin 管道传入：

```bash
cat /tmp/raven-knowledge-content.md | raven knowledge create --type <type> --title "<title>" --summary "<summary>" --tags "<tag1,tag2>"
```

**`raven knowledge create` 参数说明：**

| 参数 | 必填 | 说明 | 示例 |
|------|------|------|------|
| `--type` | 是 | 知识类型 | `runbook` / `rule` / `solution` / `doc` / `skill` |
| `--title` | 否* | 知识标题 | `"通过 Claude Code 创建 Overmind 任务"` |
| `--summary` | 否* | 一句话摘要 | `"使用 MCP 工具创建 Overmind 任务的流程"` |
| `--tags` | 否* | 标签（逗号分隔） | `"overmind,mcp,task"` |
| `--content` | 否 | 知识正文（与 --dir 二选一） | `"$(cat /tmp/file.md)"` |
| `--dir` | 否 | 打包上报目录（与 --content 二选一） | `/tmp/raven-knowledge` |

\* 使用 `--dir` 模式且目录中含 `raven.json` 时，title/summary/tags 可从 raven.json 自动读取，无需手动指定。

**禁止直接在 `--content` 参数中内联多行长内容**，这会导致 Claude Code 的安全检查拦截命令。

**更新模式**（Step 4.5 选择了更新已有条目时）：

使用 `raven knowledge update` 代替 `create`：

```bash
# 目录模式（推荐）
raven knowledge update --id <id> --dir /tmp/raven-knowledge

# 单文件模式
raven knowledge update --id <id> --title "<title>" --summary "<summary>" --tags "<tag1,tag2>" --content "$(cat /tmp/raven-knowledge-content.md)"
```

注意：更新后条目状态会重置为 pending，需重新审核。

**对于 `rule` 类型，提交后需要额外执行以下步骤使其立即生效：**

1. 使用 `raven knowledge create --type rule --title "<title>"` 提交到知识库
2. 提交成功后，使用 Edit 工具将规则内容追加到当前项目的 `CLAUDE.md` 文件中：
   - 查找 `CLAUDE.md` 中是否已存在 `## 团队规则` 段落
   - 如果不存在，在文件末尾新建 `## 团队规则` 段落
   - 在该段落下追加规则内容，格式为：`- **<规则标题>**: <规则简述>`
   - 如果规则较复杂，可以用子段落 `### <规则标题>` 展开详细内容
3. 这样规则会在下一轮对话中立即生效，无需重启会话

**对于 `skill` 类型（多文件打包）：**

skill 类型支持包含多个文件，创建时使用目录模式：

```bash
# 先准备 skill 目录结构
mkdir -p /tmp/my-skill

# 创建 raven.json（元数据）
cat > /tmp/my-skill/raven.json << 'EOF'
{
  "kb": {
    "type": "skill",
    "title": "my-skill",
    "summary": "skill 描述",
    "tags": ["skill", "workflow"]
  }
}
EOF

# 创建 SKILL.md（主入口，会自动提取为 content）
cat > /tmp/my-skill/SKILL.md << 'EOF'
---
name: my-skill
description: skill 描述
---
# 使用说明
...
EOF

# 创建辅助文件
cat > /tmp/my-skill/helper.md << 'EOF'
辅助内容...
EOF

# 打包提交（有 raven.json 时，title/summary/tags 可省略）
raven knowledge create --type skill --dir /tmp/my-skill
```

**其他类型的目录模式：**

非 skill 类型也支持 `--dir`，主文件用 `content.md`：

```bash
mkdir -p /tmp/my-rule
cat > /tmp/my-rule/raven.json << 'EOF'
{
  "kb": {
    "type": "rule",
    "title": "命名规范",
    "summary": "团队统一的变量命名约定",
    "tags": ["coding-style", "naming"]
  }
}
EOF
cat > /tmp/my-rule/content.md << 'EOF'
## 规则：变量命名使用 camelCase
...
EOF

raven knowledge create --type rule --dir /tmp/my-rule
```

## 注意事项

- 知识内容应当脱敏，不包含密码、token 等敏感信息
- 标题应简洁明了，便于检索
- 优先沉淀有复用价值的知识，避免过于特定的一次性内容
- rule 类型的知识会影响所有团队成员的编码行为，提交前需谨慎确认
- skill 类型适合封装复杂的多步骤工作流，单个知识点建议用其他类型
