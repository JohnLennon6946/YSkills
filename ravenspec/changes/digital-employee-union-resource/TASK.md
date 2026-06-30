# 数字员工-工会自动化资源位分配 实现任务

> 基于 DESIGN.md 拆分 | 创建日期: 2026-06-29

## Phase 1: 基础框架

- [x] 1.1 编写 SKILL.md 前置条件与触发词识别：定义 YAML frontmatter（name/description/触发词）、三层优先级匹配规则、不触发场景与追问模板
- [x] 1.2 定义错误处理骨架：汇总所有已知错误场景及处理方式，确保 PRD 边界条件表中每条都有对应

## Phase 2: 第一步 — 离线取数 + 表格展示

- [x] 2.1 实现步骤 1-2：open-task-process 提交 unionCoins 任务 + CronCreate 注册轮询脚本（每分钟检查 / 3 小时超时 / 单次错误不中断 / 完成时 CronDelete 移除 / 首次进度反馈）`blockedBy: 1.1`
- [x] 2.2 实现步骤 3：dataUrl 数据解析 + Markdown 表格全量展示 + 缓存写入 `.cache/latest-result.json`（含缓存失败降级）`blockedBy: 2.1`

## Phase 3: 第二步 — 资源位分配下发

- [x] 3.1 实现步骤 4：tab 类型获取（6 个已知枚举 + 自定义透传、未提供追问）`blockedBy: 1.1`
- [x] 3.2 实现步骤 5：分配指令解析（时间锚点切分避免空格干扰、序号范围 / 心遇号直指两种格式、混合解析、序号→ID 从 latest-result.json 映射、超范围/非数字兜底）`blockedBy: 3.1`
- [x] 3.3 实现步骤 6-7：rcmdback-add 逐号位串行创建（含 tabType）+ rcmdback-list 汇总展示`blockedBy: 3.2`

## Phase 4: 集成验证

- [x] 4.1 端到端流程验证：逐步骤走通触发→取数→轮询→表格→tab→解析→创建→汇总，确认每个分支（超时/空数据/解析失败/创建失败）都有明确的用户反馈路径`blockedBy: 2.2, 3.3`
- [x] 4.2 验收标准逐项核对：对照 PRD 中 9 条验收标准逐一确认 SKILL.md 覆盖，标记未覆盖项
