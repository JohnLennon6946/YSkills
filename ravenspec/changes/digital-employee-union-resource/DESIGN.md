# 数字员工-工会自动化资源位分配 技术方案

## 方案概述

以 Claude Code Skill（SKILL.md）形态实现，无需编写代码。Skill 运行在 POPO 群聊/私聊对话上下文中，通过关键词匹配触发，调用 mws moyi-activity-backend 四个现有接口完成离线取数和分配下发，结果以 Markdown 表格原地展示。复用 wechat-push-schedule 中已验证的 open-task-process → open-task-process-status 异步轮询模式。

## 关键决策

### 决策 1：Skill 形态 vs 独立服务

**选择**：用 SKILL.md 定义 Claude Code Skill，在对话流程中执行

**理由**：
- 6 个步骤均为调用已有 MWS 接口 + 文本解析 + Markdown 渲染，无需后端代码
- 复用 wechat-push-schedule 已验证的接口和轮询模式，开发成本极低
- 运营交互全在 POPO 对话内完成，与现有 Push 计划管理工作流一致

**备选**：独立 Java 服务 — 对纯编排型任务过度设计，增加服务数量和维护成本

### 决策 2：两阶段分离 vs 合并为一次交互

**选择**：第一步取数→展示表格，等待用户查看后手动输入第二步分配指令

**理由**：
- 运营需要在看到推荐结果后才能决定如何分配，不可能预先知道序号/心遇号
- 两步之间的表格是关键的决策依据，不能跳过
- 分离后用户可以在不同时间发起第二步，不影响第一步结果

**备选**：一次性全自动分配 — 不满足运营需人工判断的实际场景

### 决策 3：触发词三层优先级

**选择**：按明确度分三级匹配 — 明确指令 > 带域名词 > 模糊查询，仅"资源位"追问确认

**理由**：
- 避免与"banner资源位""资源位配置"等其他话题误触发
- 成本最低（检查一个条件即可确定是否追问），维护简单

**备选**：LLM 意图识别 — 增加 token 成本和延迟，对这种关键词明确的任务无收益

### 决策 4：轮询用 CronCreate 调度 而非同 turn 阻塞

**选择**：提交任务后立即注册 CronCreate（每分钟一次），cron 中检查 open-task-process-status，完成后 CronDelete 移除 + 通知用户；不阻塞当前对话 turn

**理由**：
- 离线取数任务需数分钟到数十分钟，同 turn sleep 阻塞会锁死整个对话 session
- 与 wechat-push-schedule 的"独立轮询 + cron 移除"模式完全一致，生产已验证
- 用户提交后可继续其他对话，完成后自动推送通知

**备选**：同 turn 内 Bash sleep 循环 — 长时间阻塞不可接受；用户无法中途做其他操作

### 决策 5：跨 turn 数据传递用 .cache JSON 文件 而非依赖对话上下文

**选择**：第一步完成后将解析结果写入 `skill/union-resource-recommend/.cache/latest-result.json`，第二步从文件读取序号→ID 映射

**理由**：
- 100 条数据从 Markdown 对话上下文反向解析不可靠（上下文可能被截断/压缩）
- JSON 结构明确，读取简单可靠
- 缓存文件写入失败时降级提示用户手动指定心遇号

**备选**：依赖 Claude 对话上下文提取表格数据 — 跨 turn 上下文不可控，不适合精确数据映射

### 决策 6：第二步指令解析用正则 vs 用 LLM

**选择**：正则匹配。先提取 `时间是\s*\S+~\S+` 锚点切分指令，再对每条指令匹配 `({start}-{end}号放|心遇号 {ids} 放){N}号位`。tab= 单独提取，不混入房间标识正则

**理由**：
- 格式确定、变体少，正则即可稳定覆盖，无需 LLM
- 时间锚点切分比简单空格 split 更鲁棒——用户可能在号位和时间之间加空格
- tab 字段独立提取，解析清晰
- 解析失败时追问模板清晰，用户体验可预期

**备选**：LLM 提取结构化参数 — 对这种格式化输入过度设计，且增加不确定的解析结果；简单空格 split — 用户输入"时间是 2025-01-01 ~ 2025-01-07"时误拆

### 决策 6：tab 类型作为分配前置参数

**选择**：用户自行输入 tab 类型，未提供则追问。接口已知 6 个枚举（theme/family/family_voice/rcmd/city/task），但允许透传用户输入的任何值

**理由**：
- 后端 rcmdback-add 需要 tabType 参数
- 用户可自由输入，不强制限制枚举，灵活性最高
- 一次分配共用同一 tab，符合运营场景

**备选**：严格校验枚举 — 未来新增 tab 时需同步更新 Skill，维护成本高

### 决策 7：第二步串行创建 vs 并行创建

**选择**：逐号位串行调用 rcmdback-add

**理由**：
- 号位间可能有依赖（如先创建的号位影响后续），串行最安全
- 计划创建通常 2-4 个号位，总耗时可接受
- 单条失败不中断后续，进度反馈清晰

**备选**：并行 — 如果后端有并发限制可能触发错误，且号位间关系未知

## 改动范围

| 文件 | 操作 | 改动内容 |
|------|------|----------|
| `skill/union-resource-recommend/SKILL.md` | 新增 | Skill 定义：触发词、7 步执行流程（含 CronCreate 轮询）、错误处理、MWS 接口调用 |
| `skill/union-resource-recommend/.cache/latest-result.json` | 新增 | 第一步结果缓存，供第二步 rank→room_no 映射 |
| `ravenspec/changes/digital-employee-union-resource/PRD.md` | 新增 | 产品需求文档 |
| `ravenspec/changes/digital-employee-union-resource/DESIGN.md` | 新增 | 本文档 |
| `ravenspec/changes/digital-employee-union-resource/FINDINGS.md` | 新增 | 待创建 |
| `ravenspec/changes/digital-employee-union-resource/specs/` | 新增 | 2 个 capability spec |
| `ravenspec/changes/digital-employee-union-resource/TASK.md` | 新增 | 待创建 |

## 关键接口

以下 4 个后端接口（2 个 MWS + 2 个 curl 直连），无需新开发：

### open-task-process — 提交异步取数任务

```
mws moyi-activity-backend open-task-process --params '{"type":"unionCoins"}'
→ { processId: "unionCoins_1719654000000" }
```

### open-task-process-status — 轮询任务结果

```
mws moyi-activity-backend open-task-process-status --params '{"processId":"unionCoins_1719654000000"}'
→ { status: "done", rate: 100, dataUrl: "https://...", totalNum: 100 }
```

### rcmdback-add — 创建资源位推荐计划（curl HTTP API）

> 未注册到 MWS CLI，通过 curl 直连。domain 从环境推断。

```
curl -s -X POST "https://moyi-activity-backend.<domain>/moyi/voice/rcmdback/add" \
  -H "Content-Type: application/json" \
  -d '{"slots":"1469611,1722583","position":"1","startTime":"2025-01-01","endTime":"2025-01-07","tabType":"theme"}'
→ { id: "abc123", ... }
```

### rcmdback-list — 查询推荐计划列表（curl HTTP API）

> 未注册到 MWS CLI，通过 curl 直连。

```
curl -s "https://moyi-activity-backend.<domain>/api/moyi/voice/rcmdback/list"
→ [ { id, position, slots, startTime, endTime, status, ... }, ... ]
```

## 风险与边界

| 风险 | 影响 | 应对 |
|------|------|------|
| open-task-process 接口对 type=unionCoins 返回格式与预期不同 | 中：提交失败或 processId 格式异常 | 接口调用前先执行一次 dry-run 验证；异常走字段缺失兜底 |
| 100 条 Markdown 表格在 POPO 消息中有长度限制 | 低：截断后运营看不到完整数据 | POPO 消息支持长文本滚动；末尾附 dataUrl 下载链接备查 |
| 用户输入不规则分配指令（空格/标点变化） | 中：正则解析失败率高 | 解析失败时给出格式 A/B 示例追问；允许空白/逗号等多分隔符 |
| 轮询超过 3 小时 | 低：backend 离线任务通常几分钟 | 超时时保留 processId，方便用户主动重试或排查 |
| 号位重复分配的语义不确定（覆盖 vs 追加 vs 拒绝） | 低 | 检测到重复时暂停并追问用户，不自动决定 |
