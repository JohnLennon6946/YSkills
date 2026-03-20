---
name: sdd-knowledge-evolve-onboard
description: 知识自动积累管道端到端验证：逐步跑通 Hook → Observe → Instinct → Rule Sync → Knowledge Upload 完整链路。英文：End-to-end walkthrough for the knowledge auto-accumulation pipeline - generate real data through each stage and confirm the full loop works.
license: MIT
compatibility: Requires raven CLI >= 0.7.30.
metadata:
  author: raven
  version: "2.0"
  generatedBy: "1.0.2"
---

端到端验证知识自动积累管道。不同于纯检查——本 skill 会实际产生观测数据、触发 instinct 分析、生成规则文件、并上传一条知识到服务端，确认整条链路完全跑通。

**Pattern:** DO → CHECK → DIAGNOSE → NEXT

---

## Preflight

确认 `raven init` 已完成且 hook 已注册：

**CHECK:**
```bash
cat ~/.claude/settings.json 2>/dev/null | grep -q "raven observe" && echo "HOOK_FOUND" || echo "HOOK_MISSING"
```

**If HOOK_MISSING:**
```
raven init 尚未完成，或 observe hook 未注册。

请先运行：
  raven init

然后重新启动本 skill：/sdd-knowledge-evolve-onboard
```

Stop here if hook is missing.

确认 raven 登录状态：

```bash
raven whoami 2>&1
```

**If 未登录：**
```
知识上传需要登录凭证。请先运行：
  raven login

登录后重新启动本 skill。
```

Stop here if not logged in.

---

## Phase 1: Welcome

Display:

```
## 知识管道端到端验证

本 skill 将实际跑通完整链路，而不仅仅检查配置：

  ┌─────────┐    ┌─────────┐    ┌──────────┐    ┌───────────┐    ┌────────────┐
  │  Hook   │───▶│ Observe │───▶│ Instinct │───▶│ Rule File │───▶│  Knowledge │
  │ trigger │    │  record │    │  evolve  │    │  generate │    │   Upload   │
  └─────────┘    └─────────┘    └──────────┘    └───────────┘    └────────────┘
     Phase 2        Phase 2       Phase 3         Phase 4          Phase 5

每个阶段都会产生真实数据，验证完成后你会拥有：
  ✓ 一批观测记录
  ✓ 至少一个 instinct
  ✓ 一个本地规则文件
  ✓ 一条已提交到服务端的知识条目

预计时长：~5 分钟
```

---

## Phase 2: Observe — 批量生成观测数据

Instinct 分析需要 ≥20 条观测，且能从中识别出**重复模式**。关键要素：

- 需要 `pre`（tool_start）+ `post`（tool_complete）**配对**，模拟完整的工具调用生命周期
- 需要**同一工作流序列重复出现**（如 Read → Edit → Bash 循环），让 observer 识别 "repeated workflows"
- 需要**跨 session 的一致行为**，产生 "tool preferences" 信号

### DO

模拟 3 轮典型的「读代码 → 修改 → 测试」开发循环，每轮使用不同的 session_id：

```bash
# 辅助函数：发送一对 pre+post 观测
obs() {
  local tool="$1" input="$2" output="$3" sid="$4"
  echo "{\"tool_name\":\"$tool\",\"tool_input\":$input,\"session_id\":\"$sid\"}" \
    | raven observe --phase pre 2>/dev/null
  echo "{\"tool_name\":\"$tool\",\"tool_input\":$input,\"tool_output\":$output,\"session_id\":\"$sid\"}" \
    | raven observe --phase post 2>/dev/null
}

# ── 循环 3 轮：模拟「理解 → 修改 → 验证」工作流 ──
for round in 1 2 3; do
  SID="onboard-round-${round}-$(date +%s)"

  # Step 1: 先读配置文件理解项目结构
  obs "Read" '{"file_path":"package.json"}' '{"content":"{\"name\":\"my-app\"}"}' "$SID"
  obs "Read" '{"file_path":"tsconfig.json"}' '{"content":"{\"compilerOptions\":{}}"}' "$SID"

  # Step 2: 搜索相关代码
  obs "Grep" '{"pattern":"export function","path":"src/"}' '{"matches":["src/utils.ts:10","src/handler.ts:5"]}' "$SID"

  # Step 3: 读目标文件
  obs "Read" '{"file_path":"src/utils.ts"}' '{"content":"export function add(a,b){return a+b}"}' "$SID"

  # Step 4: 编辑代码
  obs "Edit" '{"file_path":"src/utils.ts","old_string":"return a+b","new_string":"return a + b"}' '{"success":true}' "$SID"

  # Step 5: 运行测试验证
  obs "Bash" '{"command":"npm test"}' '{"exit_code":0,"stdout":"Tests passed"}' "$SID"

  # Step 6: git 操作
  obs "Bash" '{"command":"git diff"}' '{"stdout":"diff --git a/src/utils.ts"}' "$SID"
  obs "Bash" '{"command":"git add src/utils.ts"}' '{"exit_code":0}' "$SID"
done

# ── 补充模式：编辑后总是先 lint 再 test（重复 3 次强化 "lint before test" 偏好）──
for round in 1 2 3; do
  SID="onboard-lint-${round}-$(date +%s)"
  obs "Edit" '{"file_path":"src/handler.ts","old_string":"console.log","new_string":"logger.info"}' '{"success":true}' "$SID"
  obs "Bash" '{"command":"npm run lint"}' '{"exit_code":0,"stdout":"No errors"}' "$SID"
  obs "Bash" '{"command":"npm test"}' '{"exit_code":0,"stdout":"All tests passed"}' "$SID"
done

# ── 补充模式：写新文件时总是配套写测试（重复 2 次）──
for round in 1 2; do
  SID="onboard-write-${round}-$(date +%s)"
  obs "Write" '{"file_path":"src/feature-'$round'.ts"}' '{"success":true}' "$SID"
  obs "Write" '{"file_path":"tests/feature-'$round'.test.ts"}' '{"success":true}' "$SID"
  obs "Bash" '{"command":"npm test"}' '{"exit_code":0}' "$SID"
done

echo "Done — observations generated."
```

### CHECK

确认观测数据已写入：

```bash
wc -l .raven/knowledge/observations.jsonl 2>/dev/null || echo "FILE_MISSING"
```

预期行数 ≥ 60（3 轮主循环 × 7 步 × 2 事件 + 3 轮 lint × 3 步 × 2 + 2 轮 write × 3 步 × 2 = 42 + 18 + 12 = 72）。

抽样检查一条记录：
```bash
tail -1 .raven/knowledge/observations.jsonl | python3 -m json.tool 2>/dev/null || tail -1 .raven/knowledge/observations.jsonl
```

### 预期结果

- 文件存在且行数 ≥ 60
- 每条记录都有 `timestamp`、`event`（tool_start 或 tool_complete）、`tool`、`input`、`project` 字段
- tool_complete 事件还包含 `output` 字段

### DIAGNOSE

**如果 `FILE_MISSING`：**
```
观测日志目录可能不存在。检查：
  ls -la .raven/knowledge/

如果 .raven/ 目录不存在，说明 raven init 可能没在当前项目目录执行。
回到 Preflight 步骤重新检查。
```

**如果行数远小于预期：**
```
部分观测写入失败。查看 raven 日志：
  tail -20 ~/.raven/logs/raven-$(date +%Y-%m-%d).log

常见原因：
1. observe 进程被 CI 检测跳过 — 确认：echo $CI $GITHUB_ACTIONS $GITLAB_CI
2. stdin 读取超时 — 管道传输过慢
```

### NEXT

观测数据 ≥ 60 条 → 继续 Phase 3。

---

## Phase 3: Instinct — 触发分析

### DO

先查看当前 instinct 状态：

```bash
raven instinct status
```

然后触发分析，使用 `--generate` 自动生成规则草稿：

```bash
raven instinct evolve --generate
```

### CHECK

确认 instinct 已生成：

```bash
raven instinct status
```

查看 instinct 文件：

```bash
ls .raven/knowledge/instincts/*.yaml 2>/dev/null || echo "NO_INSTINCTS"
```

如有文件，查看其中一个：

```bash
ls -t .raven/knowledge/instincts/*.yaml 2>/dev/null | head -1 | xargs cat 2>/dev/null
```

### 预期结果

- `instinct status` 输出中列出至少一个 instinct 条目
- `.raven/knowledge/instincts/` 目录下有 `.yaml` 文件
- 文件内容包含 `trigger`、`action`、`confidence` 等字段

### DIAGNOSE

**如果 `NO_INSTINCTS`：**
```
instinct evolve 未能产生 instinct。可能原因：

1. 观测数据不够多样化——检查 Phase 2 是否正常完成
2. LLM 分析未返回有效模式——查看日志：
   tail -50 ~/.raven/logs/raven-$(date +%Y-%m-%d).log | grep -i "instinct\|evolve\|observer"

3. 网络或认证问题（分析需要调用 LLM API）：
   raven whoami
```

**如果 evolve 命令本身报错：**
```
检查 raven CLI 版本：
  raven --version

需要 >= 0.7.30。如版本过低：
  npm install -g @music/raven-cli@latest
```

### NEXT

至少一个 instinct 已生成 → 继续 Phase 4。

---

## Phase 4: Rule File — 确认规则文件

`instinct evolve --generate` 会自动将高置信度 instinct 写入 `.claude/rules/`。

### CHECK

```bash
ls .claude/rules/raven-instinct-*.md 2>/dev/null || ls .claude/rules/*.md 2>/dev/null | head -5 || echo "NO_RULES"
```

如有文件，查看最新的一个：

```bash
ls -t .claude/rules/raven-instinct-*.md 2>/dev/null | head -1 | xargs cat 2>/dev/null
```

### 预期结果

- `.claude/rules/` 下有 `raven-instinct-*.md` 文件
- 文件内容是 Claude 可读的规则，描述了从观测中提炼的行为模式

### DIAGNOSE

**如果 `NO_RULES`：**
```
evolve --generate 可能因 instinct 置信度不足未生成规则文件。
检查 instinct 置信度：
  raven instinct status

置信度 < 0.7 的 instinct 不会自动生成规则。
可以再补充一些观测数据后重试：
  raven instinct evolve --generate
```

**如果 `.claude/rules/` 目录不存在：**
```
mkdir -p .claude/rules
raven instinct evolve --generate
```

### NEXT

规则文件存在 → 继续 Phase 5。

如果没有生成规则文件但 instinct 存在，也可继续 Phase 5（直接手动创建知识条目验证上传链路）。

---

## Phase 5: Knowledge Upload — 上传到服务端

### DO

先确认知识库连接：

```bash
raven knowledge scopes
```

然后选择测试哪种知识类型：

> **请问用户：** 你想测试哪种知识上传方式？
>
> - **A) 单文件 Rule** — 上传一条规则（最简单，快速验证链路）
> - **B) 多文件 Skill** — 上传一个包含 SKILL.md 的目录（验证目录打包能力）

---

#### 方式 A：单文件 Rule

如果 Phase 4 生成了规则文件，直接上传：

```bash
RULE_FILE=$(ls -t .claude/rules/raven-instinct-*.md 2>/dev/null | head -1)

if [ -n "$RULE_FILE" ]; then
  raven knowledge upload \
    --file "$RULE_FILE" \
    --type rule \
    --tags "onboard-test,auto-generated" \
    --scope "$(basename $(pwd))"
else
  echo "没有规则文件，手动创建一条："
fi
```

如果没有规则文件，手动创建：

```bash
raven knowledge create \
  --type rule \
  --title "Onboard 验证规则" \
  --content "## 编辑后先 lint 再 test

在修改源代码文件后，始终先运行 lint 检查代码规范，通过后再运行测试。

\`\`\`bash
npm run lint && npm test
\`\`\`

这是一条由 sdd-knowledge-evolve-onboard 生成的测试知识条目，可安全删除。" \
  --tags "onboard-test" \
  --scope "$(basename $(pwd))"
```

---

#### 方式 B：多文件 Skill

创建一个临时 skill 目录，然后用 `--dir` 打包上传：

```bash
# 创建临时 skill 目录
mkdir -p /tmp/onboard-test-skill

cat > /tmp/onboard-test-skill/SKILL.md << 'SKILLEOF'
---
name: onboard-test-skill
description: 由 sdd-knowledge-evolve-onboard 生成的测试 skill，验证多文件知识上传。可安全删除。
---

# Onboard Test Skill

这是一个用于验证知识上传链路的测试 skill。

## 使用方法

```bash
echo "Hello from onboard test skill!"
```

## 注意事项

- 本 skill 仅用于端到端验证
- 验证完成后可以安全删除
SKILLEOF

cat > /tmp/onboard-test-skill/helpers.sh << 'HELPEREOF'
#!/bin/bash
# Helper script for onboard test skill
echo "This is a helper file demonstrating multi-file upload."
HELPEREOF
```

然后上传整个目录：

```bash
raven knowledge upload \
  --file /tmp/onboard-test-skill \
  --type skill \
  --title "Onboard Test Skill" \
  --tags "onboard-test,multi-file" \
  --scope "$(basename $(pwd))"
```

上传后清理临时目录：

```bash
rm -rf /tmp/onboard-test-skill
```

---

### CHECK

确认知识已提交：

```bash
raven knowledge list --tag onboard-test
```

### 预期结果

- `knowledge scopes` 列出可用的 scope
- 上传命令执行成功，返回知识条目 ID
- `knowledge list` 能看到刚提交的条目（状态为 `pending`，等待审批）
- 方式 B 的条目类型为 `skill`，内容包含打包后的多文件内容

### DIAGNOSE

**如果 scopes 为空：**
```
当前账号没有可访问的知识库 scope。
联系团队管理员添加 scope，或检查账号：
  raven whoami
```

**如果 upload/create 报错 401：**
```
认证过期，重新登录：
  raven login
```

**如果报错网络连接失败：**
```
检查 raven 服务连接：
  raven whoami

如在内网环境，确认 VPN 已连接。
```

**如果 list 看不到刚提交的条目：**
```
试试不带 filter：
  raven knowledge list --page 1 --page-size 5

或查看详情（用 upload/create 返回的 ID）：
  raven knowledge detail --id <ID>
```

### NEXT

知识条目已提交到服务端 → 继续 Phase 6 总结。

---

## Phase 6: Recap

展示所有阶段的结果汇总：

```
## 知识管道端到端验证结果

┌─────────────────────────┬──────────┬──────────────────────────────────────────┐
│ 阶段                    │ 状态     │ 产出                                     │
├─────────────────────────┼──────────┼──────────────────────────────────────────┤
│ Preflight               │ [状态]   │ Hook 已注册 + 已登录                     │
│ Phase 2: Observe        │ [状态]   │ ≥20 条观测记录写入 observations.jsonl    │
│ Phase 3: Instinct       │ [状态]   │ N 个 instinct 生成于 .raven/knowledge/  │
│ Phase 4: Rule File      │ [状态]   │ 规则文件写入 .claude/rules/              │
│ Phase 5: Knowledge      │ [状态]   │ 知识条目已提交到服务端 (ID: xxx)         │
└─────────────────────────┴──────────┴──────────────────────────────────────────┘

[状态] 标记：
  ✓ 通过
  ✗ 失败（附原因）
  △ 跳过（前置条件不满足但不阻塞后续）
```

### 全部通过时

```
## 全链路跑通！

  Hook ──▶ Observe ──▶ Instinct ──▶ Rule File ──▶ Knowledge Upload
   ✓          ✓           ✓            ✓                ✓

你的知识自动积累管道已完全可用。日常使用中：

1. **自动**：每次 Claude 工具调用 → observe hook 自动记录
2. **自动**：观测达到阈值（默认 20 条 / 5 分钟间隔）→ 自动触发 instinct 分析
3. **手动**：运行 `raven instinct evolve --generate` → 生成/更新规则文件
4. **手动**：运行 `raven knowledge upload --file <rule> --type rule` → 提交到团队知识库

清理提示：本次生成的 onboard-test 标签条目可在知识管理后台删除。
```

### 有阶段失败时

```
## 部分阶段未通过

请根据各阶段的 DIAGNOSE 建议修复后重试。

快速重试各阶段：
  Phase 2: echo '{"tool_name":"Read","tool_input":{}}' | raven observe --phase pre
  Phase 3: raven instinct evolve --generate
  Phase 4: ls .claude/rules/raven-instinct-*.md
  Phase 5: raven knowledge list --tag onboard-test

完整重走：/sdd-knowledge-evolve-onboard
```

---

## Graceful Exit Handling

### 用户中途想退出

```
没问题！已完成的阶段产出会保留：
- 观测数据在 .raven/knowledge/observations.jsonl
- Instinct 在 .raven/knowledge/instincts/
- 规则文件在 .claude/rules/

重新开始时运行：/sdd-knowledge-evolve-onboard
跳过已完成的阶段即可。
```

### 用户只想看命令参考

```
## 知识管道核心命令速查

| 命令                                    | 说明                              |
|-----------------------------------------|-----------------------------------|
| raven init                              | 注册 observe hook                 |
| raven observe --phase pre/post          | 手动触发观测记录（通常自动）       |
| raven instinct status                   | 查看已有 instinct 列表             |
| raven instinct evolve --generate        | 分析聚类 + 生成规则文件            |
| raven knowledge scopes                  | 列出可用 scope                     |
| raven knowledge upload --file --type    | 上传本地文件到知识库               |
| raven knowledge create --type --title   | 创建知识条目                       |
| raven knowledge list                    | 列出知识条目                       |
| raven knowledge search --q <keyword>    | 搜索知识库                         |
| raven whoami                            | 查看当前登录用户                   |
| raven login                             | 登录                               |

关键路径：
  观测日志：.raven/knowledge/observations.jsonl
  Instinct：.raven/knowledge/instincts/*.yaml
  规则文件：.claude/rules/raven-instinct-*.md
  Raven 日志：~/.raven/logs/raven-YYYY-MM-DD.log
```

---

## Guardrails

- **每个 CHECK 都要实际执行**——必须运行命令看到真实输出，不要假设结果
- **遇到失败立即给出 DIAGNOSE**——不跳过失败阶段
- **Phase 5 会产生真实数据**——提交到服务端的知识条目带有 `onboard-test` tag，方便后续清理
- **不要修改用户已有的配置文件或规则文件**
- **Phase 2 的模拟观测不会影响已有数据**——只是追加到 observations.jsonl
- **处理退出要温和**——用户随时可以中止，已产生的数据不需要清理
