---
name: sdd-knowledge-usage-onboard
description: 知识消费端到端验证：逐步跑通 Discover → Search → Apply → Feedback 完整消费链路。英文：End-to-end walkthrough for knowledge consumption - discover scopes, search knowledge, apply to local project, and give feedback.
license: MIT
compatibility: Requires raven CLI >= 0.7.30.
metadata:
  author: raven
  version: "1.0"
  generatedBy: "1.0.2"
---

端到端验证知识消费链路。本 skill 演示如何发现团队知识、搜索匹配项、将知识应用到本地项目、并反馈使用效果，形成知识消费闭环。

**Pattern:** DO → CHECK → DIAGNOSE → NEXT

---

## Preflight

确认 raven 登录状态（知识消费需要认证）：

**CHECK:**
```bash
raven whoami 2>&1
```

**If 未登录：**
```
知识消费需要登录凭证。请先运行：
  raven login

登录后重新启动本 skill。
```

Stop here if not logged in.

---

## Phase 1: Welcome

Display:

```
## 知识消费链路端到端验证

知识积累是生产端，知识消费是需求端。本 skill 验证消费链路：

  ┌──────────┐    ┌────────┐    ┌───────┐    ┌──────────┐
  │ Discover │───▶│ Search │───▶│ Apply │───▶│ Feedback │
  │  scopes  │    │  query │    │ local │    │  useful? │
  └──────────┘    └────────┘    └───────┘    └──────────┘
    Phase 2         Phase 3      Phase 4       Phase 5

每个阶段都会执行真实操作，验证完成后你会：
  ✓ 了解团队知识库有哪些 scope
  ✓ 搜索并找到匹配的知识条目
  ✓ 将知识应用（pin）到本地项目
  ✓ 给知识条目反馈使用效果

预计时长：~5 分钟
```

---

## Phase 2: Discover — 发现可用知识

### DO

查看团队知识库有哪些 scope 和知识条目：

```bash
raven knowledge scopes
```

再看看知识库中有多少条目：

```bash
raven knowledge list --page 1 --page-size 5
```

### CHECK

- `scopes` 命令输出至少一个 scope
- `list` 命令输出知识条目列表

### 预期结果

输出类似：
```
Scope: backend — 后端相关规则和最佳实践
Scope: frontend — 前端开发规范
...
```

以及条目列表，每条包含 ID、标题、类型、状态。

### DIAGNOSE

**如果 scopes 为空：**
```
团队知识库还没有配置 scope。
联系管理员在知识管理后台添加 scope。
```

**如果 list 返回空：**
```
知识库中还没有已审批的条目。
可以先运行 /sdd-knowledge-evolve-onboard 上传一些知识。
```

### NEXT

至少看到一些条目 → 继续 Phase 3。

---

## Phase 3: Search — 搜索知识

### DO

> **请问用户：** 你想搜索什么关键词？输入一个与你当前项目相关的关键词。
>
> 如果不确定，可以试试通用关键词如 `rule`、`test`、`lint`、`deploy` 等。

用用户提供的关键词搜索：

```bash
raven knowledge search --q "<用户提供的关键词>"
```

如果搜索无结果，尝试更宽泛的关键词：

```bash
raven knowledge search --q "rule"
```

也可以带上 scope 过滤和上下文推断：

```bash
# 按 scope 过滤
raven knowledge search --q "<关键词>" --scope "<scope名>"

# 自动根据当前文件推断 scope
raven knowledge search --q "<关键词>" --context src/index.ts
```

### CHECK

- 搜索返回至少一条匹配结果
- 记下感兴趣的条目 ID（后续 Phase 4 要用）

### 预期结果

输出类似：
```
[ID: 5] rule — 编辑后先 lint 再 test (approved)
  Summary: 修改源代码后始终先 lint 再 test...
[ID: 3] solution — 数据库连接池配置 (approved)
  Summary: 推荐的连接池参数...
```

### DIAGNOSE

**如果搜索无结果：**
```
没有匹配的已审批知识。可能原因：
1. 关键词太具体 — 试试更通用的词
2. 知识条目尚未审批 — 检查：raven knowledge list --status pending
3. 知识库为空 — 先通过 /sdd-knowledge-evolve-onboard 上传知识
```

**如果报错 401：**
```
认证过期：
  raven login
```

### NEXT

找到至少一条知识 → 记住它的 ID → 继续 Phase 4。

---

## Phase 4: Apply — 应用知识到本地

### DO

将搜索到的知识条目 pin 到本地项目。默认写入 `.claude/rules/` 目录，Claude 后续会话会自动加载。

```bash
raven knowledge apply --id <ID>
```

### CHECK

确认规则文件已写入：

```bash
ls -la .claude/rules/
```

查看文件内容：

```bash
cat .claude/rules/*.md | head -30
```

### 预期结果

- `.claude/rules/` 下新增一个 `.md` 文件
- 文件内容包含知识条目的规则/方案/文档内容
- 文件头部有 frontmatter（description, globs 等）

### DIAGNOSE

**如果 apply 报错 "not found"：**
```
条目 ID 不存在或未审批。确认 ID：
  raven knowledge detail --id <ID>

只有 approved 状态的知识才能 apply。
```

**如果 `.claude/rules/` 目录不存在：**
```
目录会自动创建。如果没有：
  mkdir -p .claude/rules
  raven knowledge apply --id <ID>
```

**如果 apply 成功但文件没有出现：**
```
检查 apply 的输出中文件路径，可能写入了自定义位置：
  raven knowledge apply --id <ID> --to .claude/rules/my-rule.md
```

### NEXT

知识已 pin 到本地 → 继续 Phase 5。

---

## Phase 5: Feedback — 反馈使用效果

知识消费的闭环是反馈——告诉知识库这条知识是否有用，帮助提升知识质量。

### DO

先看一下刚 apply 的知识详情：

```bash
raven knowledge detail --id <ID>
```

然后给出反馈：

> **请问用户：** 这条知识对你有帮助吗？
>
> - **有用** → `raven knowledge feedback --id <ID> --useful`
> - **没用** → `raven knowledge feedback --id <ID> --useless`

```bash
# 标记为有用
raven knowledge feedback --id <ID> --useful

# 或标记为没用
raven knowledge feedback --id <ID> --useless
```

### CHECK

- feedback 命令执行成功无报错

### 预期结果

命令执行成功，反馈被记录。这些反馈数据会体现在知识度量看板中（搜索命中率、复用比等指标）。

### DIAGNOSE

**如果报错：**
```
确认 ID 正确：
  raven knowledge detail --id <ID>

确认登录状态：
  raven whoami
```

### NEXT

反馈已提交 → 继续 Phase 6 总结。

---

## Phase 6: Recap

展示所有阶段的结果汇总：

```
## 知识消费链路验证结果

┌─────────────────────────┬──────────┬──────────────────────────────────────────┐
│ 阶段                    │ 状态     │ 产出                                     │
├─────────────────────────┼──────────┼──────────────────────────────────────────┤
│ Preflight               │ [状态]   │ 已登录                                   │
│ Phase 2: Discover       │ [状态]   │ N 个 scope，M 条知识                     │
│ Phase 3: Search         │ [状态]   │ 搜索到 K 条匹配结果                      │
│ Phase 4: Apply          │ [状态]   │ 知识已 pin 到 .claude/rules/             │
│ Phase 5: Feedback       │ [状态]   │ 反馈已提交                               │
└─────────────────────────┴──────────┴──────────────────────────────────────────┘

[状态] 标记：
  ✓ 通过
  ✗ 失败（附原因）
  △ 跳过
```

### 全部通过时

```
## 消费链路跑通！

  Discover ──▶ Search ──▶ Apply ──▶ Feedback
      ✓           ✓          ✓          ✓

知识消费闭环已完整可用。日常使用中：

1. **搜索知识**：遇到问题时 `raven knowledge search --q "<关键词>"`
2. **应用知识**：找到有用的 `raven knowledge apply --id <ID>`
3. **上下文推断**：`raven knowledge search --q "<问题>" --context <当前文件>` 自动匹配 scope
4. **反馈闭环**：用完后 `raven knowledge feedback --id <ID> --useful`

搭配 sdd-knowledge-evolve-onboard（知识生产）形成完整飞轮：

  生产：编码 → 观测 → Instinct → 规则 → 上传知识库
                                              ↓
  消费：搜索 ← 发现 ← Apply ← Feedback ← 知识库
```

### 有阶段失败时

```
## 部分阶段未通过

请根据各阶段的 DIAGNOSE 建议修复后重试。

快速重试各阶段：
  Phase 2: raven knowledge scopes && raven knowledge list
  Phase 3: raven knowledge search --q "rule"
  Phase 4: raven knowledge apply --id <ID>
  Phase 5: raven knowledge feedback --id <ID> --useful

完整重走：/sdd-knowledge-usage-onboard
```

---

## Graceful Exit Handling

### 用户中途想退出

```
没问题！已完成的阶段不需要清理：
- Apply 写入的文件在 .claude/rules/，可手动删除
- Feedback 记录已提交到服务端

重新开始时运行：/sdd-knowledge-usage-onboard
```

### 用户只想看命令参考

```
## 知识消费核心命令速查

| 命令                                          | 说明                          |
|-----------------------------------------------|-------------------------------|
| raven knowledge scopes                        | 列出可用 scope                 |
| raven knowledge list                          | 列出知识条目                   |
| raven knowledge search --q <keyword>          | 搜索知识库                     |
| raven knowledge search --q <kw> --scope <s>   | 按 scope 搜索                  |
| raven knowledge search --q <kw> --context <f> | 按文件上下文推断 scope          |
| raven knowledge detail --id <ID>              | 查看知识详情                   |
| raven knowledge apply --id <ID>               | Pin 知识到本地 .claude/rules/  |
| raven knowledge apply --id <ID> --to <path>   | Pin 到指定路径                 |
| raven knowledge feedback --id <ID> --useful   | 标记知识有用                   |
| raven knowledge feedback --id <ID> --useless  | 标记知识没用                   |

知识消费产生的 usage 数据会体现在知识度量看板的消费指标中。
```

---

## Guardrails

- **每个 CHECK 都要实际执行**——必须运行命令看到真实输出
- **遇到失败立即给出 DIAGNOSE**——不跳过失败阶段
- **Phase 4 会写入文件**——apply 到 `.claude/rules/`，影响后续 Claude 行为
- **Phase 5 会产生真实反馈数据**——提交到服务端，影响知识质量指标
- **搜索关键词优先使用用户提供的**——不要自作主张替换关键词
- **如果知识库为空，引导用户先跑 sdd-knowledge-evolve-onboard**
- **处理退出要温和**——用户随时可以中止
