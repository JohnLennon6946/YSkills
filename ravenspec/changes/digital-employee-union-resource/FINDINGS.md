# 数字员工-工会自动化资源位分配 发现与决策

> 创建日期: 2026-06-29
> 本文档在开发全程持续更新

## 技术决策

### Skill 形态选择：SKILL.md 而非独立服务

- **决策**：以 Claude Code SKILL.md 实现，纯编排调用现有 MWS 接口
- **理由**：全部 6 个步骤均为调用已有接口 + 文本解析 + Markdown 渲染，无需新增后端代码；复用 wechat-push-schedule 已验证的接口和轮询模式
- **放弃方案**：独立 Java 服务 — 过度设计，增加服务数量和部署维护成本

### 触发词匹配：三层优先级正则 而非 LLM 意图识别

- **决策**：按明确度分三级正则匹配 — 明确指令 > 带域名词 > 模糊查询
- **理由**：触发词集合确定、变体少，正则即可稳定覆盖。LLM 增加 token 成本和延迟，且引入不确定的判断结果
- **放弃方案**：LLM 意图识别 — 对此场景过度设计，额外 token 消耗无对应收益

### 轮询参数：复用 wechat-push-schedule 的 1 分钟 / 3 小时

- **决策**：open-task-process-status 轮询间隔 1 分钟，超时阈值 3 小时
- **理由**：同一套后端接口，任务耗时特征一致，降低运维认知负担，已有生产验证
- **放弃方案**：更短的 10 秒间隔 — 对离线取数任务无意义，增加无效请求；更短的超时 — 某些类型任务可能需数十分钟

### 第二步指令解析：正则 + 时间锚点切分 而非简单空格 split

- **决策**：按空格拆指令，正则匹配每条 `({start}-{end}号放|心遇号 {ids} 放){N}号位，时间是{date}~{date}`

### 轮询调度：CronCreate 而非同 turn 阻塞

- **决策**：提交任务后立即注册 CronCreate（每分钟），cron 中检查 open-task-process-status，完成后 CronDelete + 通知。不阻塞当前 turn。
- **理由**：离线取数需数分钟到数十分钟，同 turn sleep 会锁死对话 session；与 wechat-push-schedule 模式一致
- **放弃方案**：同 turn Bash sleep 循环 — 长时间阻塞不可接受

### 数据缓存：.cache JSON 文件供跨 turn 使用

- **决策**：第一步完成后写 `skill/union-resource-recommend/.cache/latest-result.json`，第二步从中读取序号→ID 映射
- **理由**：100 条数据从 Markdown 上下文反解析不可靠；JSON 结构明确，读写简单
- **放弃方案**：依赖对话上下文反解析表格 — 跨 turn 上下文可能被截断/压缩

### 指令拆分：时间锚点切分 而非简单空格 split

- **决策**：先用正则 `时间是\s*\S+~\S+` 提取时间锚点，再围绕锚点切分指令，而非按空格 split
- **理由**：用户可能在号位和时间间加空格（如"1号位，时间是 2025-01-01 ~ 2025-01-07"），空格 split 会误拆
- **放弃方案**：简单空格 split — 有空格变体时失效
- **理由**：格式确定、变体少，正则稳定覆盖；解析失败时追问模板清晰
- **放弃方案**：LLM 提取结构化参数 — 不确定的解析结果会引入误操作风险

### Tab 类型：6 个已知枚举，用户可以自行输入

- **决策**：tab 类型作为分配前置参数，已知 6 个枚举（THEME=主题、FAMILY_PLAY=家族在玩、FAMILY_VOICE=家族语音房、RCMD=推荐、CITY=同城列表、DAILY_TASK=日常任务），用户可自由输入，未提供则追问。所有号位共用同一个 tab。
- **理由**：透传用户输入而非强制枚举校验，未来新增 tab 无需同步更新 Skill；共用 tab 符合运营场景
- **放弃方案**：严格枚举校验 — 后端新增 tab 时 Skill 需同步维护

### 第二步创建方式：串行 而非并行

- **决策**：逐号位串行调用 rcmdback-add
- **理由**：号位间可能存在未知依赖，通常 2-4 个号位总耗时可控，单条失败不中断后续
- **放弃方案**：并行 — 如果后端有并发限制可能触发错误

### 同 Skill 复用已有 wechat-push-schedule 异步轮询模式

- **决策**：open-task-process → open-task-process-status 的提交/轮询/超时/错误处理全盘复用 wechat-push-schedule 的模式
- **理由**：同一套后端基础设施，设计模式可直接继承，降低实现和维护成本
- **放弃方案**：自行设计新的轮询逻辑 — 无必要差异化

## 踩坑记录

### rcmdback 接口未注册 MWS，需 curl 直连

- **现象**：`mws moyi-activity-backend rcmdback-list` 返回 error: unrecognized subcommand，`--help` 命令列表中无 rcmdback 相关命令
- **根因**：/moyi/voice/rcmdback/add 和 /api/moyi/voice/rcmdback/list 是 HTTP API，未注册到 MWS CLI 命令行工具
- **解决方案**：第二步创建和查询改用 curl 直连 HTTP API；domain 需从 `mws env` 或上下文推断（online/pre/test）

## 变更摘要

| 日期 | 变更内容 | 原因 | 影响范围 |
|------|----------|------|----------|
| 2026-06-29 | 创建 SKILL.md、PRD.md、DESIGN.md | 新需求启动 | skill/union-resource-recommend/ |
