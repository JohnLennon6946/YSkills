# mws-xinyu-activity-create 实现任务

> 基于 DESIGN.md 拆分 | 创建日期: 2026-05-21

## Phase 1: 基础子 skill（无依赖，可并行）

- [x] 1.1 创建 `skill/moyi-resource-sheet-parser/SKILL.md`：实现 POPO 在线表格读取（委托 popo-doc-read）+ 任务 sheet 解析（任务名称/奖励包 ID）+ 抽奖 sheet 解析（资产币 ID/奖品表区 7 列）+ 库存类型容错映射 + 多 sheet 区分逻辑 + 结构化 JSON 返回格式
- [x] 1.2 创建 `skill/moyi-mission-clone/SKILL.md`：实现任务模块克隆流程 — copy-mundo 调用 + mundo-query 拉取新 mundo 树 + 按 missionName 反查替换 rewardBoxId（info-save）+ 映射表 M2 构建 + 单条 mission 失败不阻断 + 结构化 JSON 返回

## Phase 2: 核心子 skill（可并行，互不依赖）

- [x] 2.1 创建 `skill/moyi-lottery-clone/SKILL.md`：实现抽奖模块克隆 — tenant-list 拉源奖池 + tenant-query 取 TenantConfigVO + 新 TenantConfigVO 构造（basicInfo/tenantExtInfo/awards 含 probMap 三档 + inventoryType 映射）+ template-create 创建 + 映射表 M3/M4/M5 构建 + 单奖池失败不阻断 + 结构化 JSON 返回 `blockedBy: 1.1`
- [x] 2.2 创建 `skill/moyi-act-resource-clone/SKILL.md`：实现小程序活动模块克隆 — act-resource-page 拉源资源 + type=7 先创建（构建 M6）+ type=4 configJson 7 项跨模块 patch（token/relatedPoolId/relatedTicketId/relatedActivityId/poolCount/taskPlayId/taskGroupId）+ ruleText 日期文案替换（7 种格式）+ 结构化 JSON 返回

## Phase 3: 主编排 skill

- [x] 3.1 创建 `skill/moyi-activity-create/SKILL.md`：实现主流程编排 — POPO 入口意图识别 + 公共账号鉴权 + 模板克隆 vs 全新分流 + 模板检索（plan-list 模糊匹配 + 候选列表展示）+ 活动时间收集（日期解析 + 15:00:00/23:59:59 补全）+ plan-create + panel-list 构建 M1 + 资源表格收集 + 子模块编排顺序（mission→lottery→act-resource）+ 映射表 M1-M6 累积传递 + 兜底事件汇总通知 + 中途取消 + 会话超时 + 环境选择 `blockedBy: 1.1, 1.2, 2.1, 2.2`

## Phase 4: 集成与验证

- [x] 4.1 验证 5 个 SKILL.md 的 YAML frontmatter 格式与 metadata 字段（name/description/metadata.type）与仓内现有 skill 一致 `blockedBy: 3.1`
- [x] 4.2 验证子 skill 返回 JSON 结构定义与主 skill 解析逻辑对齐（字段名、类型、事件格式一致） `blockedBy: 3.1`
- [x] 4.3 验证日期 token 识别正则集 7 种格式在主 skill 和 act-resource-clone 中定义一致 `blockedBy: 3.1`
