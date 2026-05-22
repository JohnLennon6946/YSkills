# mws-xinyu-activity-create 产品需求文档

> 创建日期: 2026-05-20
> 修订日期: 2026-05-20（基于代码深挖 + 24 项澄清答案）

## 需求概述

为心遇业务运营提供一套 POPO 聊天机器人 skill，运营在 POPO 中以自然语言「基于某历史活动计划名称克隆一个新活动计划」的方式触发，由 Agent 编排 mws 命令调用心遇活动后台 (`moyi-activity-backend` service) 完成「活动发布计划 + 任务模块 + 抽奖模块 + 小程序活动模块」的克隆创建，把当前需运营手工串多个 mws 命令、手工对齐字段、手工填写奖励包/奖池配置的低效流程，自动化为「一句话触发 + 一份资源配置在线表格 + 多轮交互确认」的成单链路。

**所属业务**：心遇 (mws `moyi-activity-backend`，`AppProductEnum = MOYI`)，本期不抽象通用「活动平台克隆」能力，不支持其他业务线（ichat / mirth / look 等）。

## 核心功能

### 功能 1：POPO 入口触发与意图分流

**描述**：运营在 POPO 群中 @机器人或私聊机器人，发送「帮我创建一个新的活动发布计划」等同类意图描述，机器人通过 **LLM 自由意图识别**（非严格关键词匹配）识别后，追问「是创建全新发布计划，还是以某个已有发布计划名称为模板克隆？」

**实现载体**：本期**新建**专用 POPO bot 服务（不复用 plurk-mcp），通过 mws 公共账号鉴权。

**边界条件**：
- 正常情况（运营选「模板克隆」）：进入功能 2 模板选择流程
- 异常情况（运营选「全新发布计划」）：终止流程，回复"全新发布计划能力建设中，敬请期待"
- 异常情况（运营回复无法识别为上述两种）：再次追问最多 1 次，仍无法识别则终止并提示按格式重发
- 异常情况（鉴权失败）：提示运营联系管理员检查公共账号配置

**验收标准**：
- 运营在 POPO 群 @机器人 发送触发语 → 机器人 30 秒内回复二选一追问
- 运营选「模板克隆」→ 进入功能 2
- 运营选「全新发布计划」→ 机器人回复"建设中"并终止当前会话

### 功能 2：模板发布计划检索与选定

**描述**：机器人引导运营输入计划名称关键词，调用 mws `moyi-activity-backend plan-list` 接口按名称模糊匹配查询历史发布计划，将命中结果以「计划名称 + 开始时间 + 结束时间」格式呈现为编号候选列表，运营按编号选定一个作为克隆源 plan。

**调用接口**：
- `POST /api/livestream/activity/plan/list`（mws: `moyi-activity-backend plan-list`）
- 入参：`name`（模糊匹配关键词）、`page`（默认每页 20 条）
- 返回：`PageResult<ActPlanDTO>`（含 `id`, `name`, `startTime`, `endTime`, `domain`, `modules`, `noticeCorps` 等）

**边界条件**：
| 场景 | 处理方式 |
|------|----------|
| 模糊匹配 0 条命中 | 回复"未找到匹配计划，请重新输入关键词"，允许运营重试最多 3 次 |
| 命中条数 ≤ 20 条 | 全量展示候选列表 |
| 命中条数 > 20 条 | 仅展示最近修改的 20 条 + 提示"还有 N 条未展示，请输入更精确的关键词" |
| 运营输入的编号超出列表范围 | 回复"编号无效，请重新选择"，允许重试最多 3 次 |
| 接口调用失败 | 终止流程并把 mws 报错原样反馈给运营 |

**验收标准**：
- 运营输入"iOS 复购"→ 机器人返回包含"iOS 复购"关键词的历史计划候选列表（每条含名称 + 起止时间）
- 运营回复"1"→ 机器人确认所选源 plan 名称并进入功能 3

### 功能 3：活动时间收集与新发布计划创建

**描述**：运营选定源 plan 后，机器人询问新活动的时间范围（开始日期 + 结束日期），按既定规则把日期补全为完整时间戳并生成新 plan 名称，然后调用 mws 接口创建新发布计划。

**时间规则**（基于真实线上数据校准）：
- **开始时间 = 开始日期 15:00:00**（当地时区 Asia/Shanghai）
- **结束时间 = 结束日期 23:59:59**（当地时区 Asia/Shanghai）

**新 plan 名称生成规则**：
- 识别源 plan 名称中的日期 token（如 `5.19-5.24`、`5/19-5/24`、`0519-0524` 等格式）
- 若识别到日期 token：用新活动日期替换原日期 token，保持 token 格式（与源完全一致）
- 若未识别到日期 token：在源名称末尾追加 ` <新开始日期>-<新结束日期>`（格式默认 `M.d`）

**调用编排**：
1. `POST /api/livestream/activity/panel/list`（mws: `moyi-activity-backend panel-list`）查源 plan 的模块清单（拿到 `modules` 字段）
2. `POST /api/livestream/activity/plan/create`（mws: `moyi-activity-backend plan-create`）创建新 plan，入参：
   - `name` = 新 plan 名（按上述规则生成）
   - `startTime` / `endTime` = 新时间（毫秒）
   - `modules` = **沿用源 plan 的 modules**（如 `["mission","spinach","wechat"]`）
   - `domain` = **沿用源 plan 的 domain**
   - `noticeCorps` = **沿用源 plan 的 noticeCorps**
3. plan-create 返回 `ActPlanDTO`（含新 plan id）。后端**自动创建所有 panel**，命名规则 `<plan name>-<模块中文名>-1`（mission 例外，直接 = plan name），无需调用方干预
4. `POST /api/livestream/activity/panel/list`（带 `planId` = 新 plan id）查新 plan 下各 panel 的 `activityId`，构造「源 panel activityId → 新 panel activityId」**映射表 M1**，供后续功能 5/6/7 跨模块 patch 使用

**本期支持的 modules 类型白名单**：
- `mission`（任务）
- `spinach`（抽奖）
- `wechat`（小程序活动）
- **源 plan 含其他模块类型（如 `rank`、`shop`、`hourLottery` 等）**：plan-create 时仍传入（保证新 plan 模块结构一致），但**本期不复制其内部内容**，记入兜底事件清单提示运营手工处理

**边界条件**：
| 场景 | 处理方式 |
|------|----------|
| 运营输入的日期格式无法解析 | 提示"日期格式无法识别，请按 `M.d-M.d` 格式输入" |
| 结束日期 ≤ 开始日期 | 提示"结束日期必须晚于开始日期，请重新输入" |
| 开始时间过近（被后端 `allowCreatePlanGapMinutes` 校验拒绝） | 把后端报错原样反馈给运营，提示"活动开始时间需要在 N 分钟后，请重新选日期" |
| 源 plan 名称中日期 token 识别失败 | 走"追加日期"分支，并在最终汇总通知中提示运营核对新名称 |
| `plan-create` 接口报错（其他原因） | 终止流程并把 mws 报错原样反馈给运营 |

**验收标准**：
- 运营输入"6.1-6.10"→ 机器人创建出名为"iOS 复购 6.1-6.10"的新发布计划
- 新 plan 的 `startTime = 2026-06-01 15:00:00`, `endTime = 2026-06-10 23:59:59`
- 新 plan 的 `modules` / `domain` / `noticeCorps` 与源 plan 一致
- 新 plan 的所有 panel 都已由后端自动创建，机器人能从 panel-list 拿到映射表 M1

### 功能 4：资源配置表格收集

**描述**：新 plan 创建成功后，机器人提示运营**发送同一份 POPO 在线表格链接**，表格内含「任务」和「抽奖」两个 sheet（小程序活动模块不需要资源配置）。机器人通过 `popo-doc-read` skill 读取表格内容并解析。

**表格平台**：POPO 在线表格（本期仅支持此一种）。

**表格结构（一份多 sheet）**：

**任务 sheet** 列定义：
| 列名 | 类型 | 说明 |
|---|---|---|
| 任务名称 | string | 用于按"任务名称"反查新 mission，**唯一匹配键** |
| 任务描述 | string | 仅供运营参考，**skill 不消费** |
| 任务类型 | string | 仅供运营参考，**skill 不消费**（mission 内部的类型/描述等字段全部沿用源） |
| 完成条件 | string | 仅供运营参考，**skill 不消费** |
| 任务周期 | string | 仅供运营参考，**skill 不消费** |
| **奖励包 ID** | string/long | **唯一被消费的字段**，覆盖源 mission 的 rewardBoxId |

**抽奖 sheet** 列定义：
- 表头区（前 3 行）：
  | 行 | 内容 |
  |---|---|
  | 第 1 行 | `抽奖` 标识 |
  | 第 2 行 | `资产币ID` |
  | 第 3 行 | （具体的资产币 ID，如 `2003754`） |
- 奖品表区（从第 4 行起）：
  | 列名 | 类型 | 说明 |
  |---|---|---|
  | 奖励包 ID | string/long | 奖品的 rewardBoxId，**唯一匹配键** |
  | 基础权重 | int | 权重数值（不是百分比） |
  | 保底权重 | int | 权重数值（不是百分比） |
  | 是否未中奖奖品 | "是" / "否" | 映射 boolean |
  | 作弊权重 | int | 权重数值（推测 probType=9） |
  | 库存类型 | string | 映射 InventoryCycle 枚举（"一次性库存"/"无限量"/"每日库存" 等） |
  | 库存数量 | int | 库存数 |

**注意**：
- **权重填的是数值不是概率，无需校验 100% 之和**
- 同一份表格内一个抽奖 sheet 对应**一个奖池**；如源 plan 有多个奖池，表格按 sheet 分组（如「抽奖-1」「抽奖-2」），sheet 名与源奖池名按顺序匹配（细节见 [待补充] 项）

**调用编排**：
1. 机器人发送提示，列出当前 plan 含的模块（如"本计划含任务、抽奖、小程序活动；请发送资源配置在线表格链接，需包含任务、抽奖两个 sheet。小程序活动模块不需要资源配置。"）
2. 运营回复表格链接（POPO 在线表格 URL）
3. 机器人通过 `popo-doc-read` skill 读取表格内容
4. 解析为内存数据结构（任务表 + 抽奖表数据）

**边界条件**：
| 场景 | 处理方式 |
|------|----------|
| 当前 plan 仅含小程序活动模块（无任务无抽奖） | 跳过资源收集环节，直接进入功能 7 |
| 运营发送的链接无法解析为有效的 POPO 在线表格 | 提示"链接无法读取，请检查权限或重新发送"，最多重试 3 次 |
| 表格结构缺少必需 sheet（含任务模块但无任务 sheet，等） | 提示"表格缺少 <sheet 名>，请补全后重新发送" |
| 表格内任务 sheet 或抽奖 sheet 字段缺失（如缺奖励包 ID 列） | 提示"<sheet 名> 缺少列 <列名>，请补全后重新发送" |
| 抽奖 sheet 内权重 / 库存数量非整数 | 提示"<sheet 名> 第 X 行 <字段名> 必须为整数" |
| `popo-doc-read` 解析失败 / 表格无法读取（非通用文档表格能力问题） | 终止流程，记入兜底事件，提示运营"表格读取失败，请尝试将表格另存为标准格式后重新发送"（[待补充] popo-doc-read 在心遇活动表格上的实际兼容性需 design 阶段验证）|

**验收标准**：
- 含任务模块的 plan：运营发送表格后机器人确认"已读取任务 sheet N 条"
- 含抽奖模块的 plan：运营发送表格后机器人确认"已读取抽奖 sheet 共 M 个奖池"
- 仅含小程序活动：跳过此环节，直接进入小程序活动复制

### 功能 5：任务模块复制

**描述**：将源 plan 下「任务模块」的整个 mundo + box + mission 树克隆到新 plan 下，奖励包 ID 从任务资源 sheet 中按「任务名称」反查覆盖。

**调用编排（核心简化：直接复用 copyMundo）**：

```
Step A. POST /api/social/mission/backend/copy/mundo  (mws: moyi-activity-backend copy-mundo)
   入参 MissionBackendCopyReq:
     activityId   = 源 plan 的 mission panel activityId（即 mission 模块的子活动 id）
     missionName  = 按源 mundo 名 + 日期规则生成的新名称
     startTime    = 新活动开始时间（毫秒，14:00 → 改 15:00）
     endTime      = 新活动结束时间（毫秒，23:59:59）
     business     = "moyi"
     aimActivityId = 0  → 让后端创建全新子活动
   返回: 新 mission panel 的 activityId（即新 mundo 的 activityId）
   副作用: 后端递归复制所有 box + mission；rewardBoxId 与源一致（待 Step C 覆盖）

Step B. POST /api/social/mission/backend/mundo/query  (mws: moyi-activity-backend mundo-query)
   入参: activityId = Step A 返回的新 activityId
   返回: MissionBackendInfo（含完整 box + mission 列表，每个 mission 有 new id）

Step C. 遍历新 mission 列表：
   按 mission.missionName 在任务 sheet 中反查匹配（精确匹配）
   - 匹配命中 + 表格的 rewardBoxId 非空 → 替换为新 rewardBoxId
   - 匹配命中 + 表格的 rewardBoxId 为空 → 保留源 rewardBoxId（不调 info-save）
   - 匹配不到 → 保留源 rewardBoxId + 记入兜底事件
   仅对需要替换的 mission 调用:
   POST /api/social/mission/backend/info/save  (mws: moyi-activity-backend info-save)
     入参: MissionDTO（mundoQuery 返回的 mission 对象，仅修改 rewardBoxId 字段）
     返回: 该 mission 的 id
```

**关键映射表**（功能 5 产出，供后续功能 6/7 使用）：
- **M2: 源 box id → 新 box id**（由 mundoQuery 返回的新 box 与源按顺序对齐推断；用于功能 7 抽奖转盘 configJson 的 `taskGroupId` patch）

**字段处理规则**（copyMundo 接口已自动处理大部分，列在此供 spec 对齐用）：
| 字段 | 处理 |
|---|---|
| mundo missionName | Step A 传入新名（按日期规则） |
| mundo 起止时间 | Step A 传入新时间 |
| 每个 box 的字段（任务组名/参与用户/人群包/是否有任务组任务等） | copyMundo 内部自动按源复制，新 id + 新 activityId |
| 每个 mission 的字段（任务名/描述/类型/分类/完成条件/周期/礼包发放方式等 33+ 字段） | copyMundo 内部自动按源复制，新 id + 新 boxId + 新 activityId + 新起止时间 |
| 每个 mission 的 **rewardBoxId** | copyMundo 复制源值；Step C 按 sheet 覆盖 |
| 每个 mission 的 **tenantId**（关联抽奖机） | **本期不映射替换**，保持源值（与你确认：本期任务与抽奖不耦合） |

**边界条件**：
| 场景 | 处理方式 |
|------|----------|
| 源 mission panel activityId 在 panel-list 中找不到 | 跳过任务模块，记入兜底事件 |
| copyMundo 报错 | 跳过任务模块，记入兜底事件，不影响后续抽奖/小程序模块 |
| mundoQuery 报错 | 跳过 rewardBoxId 替换，记入兜底事件 |
| 单个 info-save 报错 | 跳过该 mission 的 rewardBoxId 替换，记录该 mission 失败原因，继续下一个 |
| 任务 sheet 中有"任务名称"在新 mission 中找不到对应 | 记入兜底事件（提示"sheet 中存在源活动已删除的任务名"），不影响流程 |
| 同一"任务名称"在 sheet 中出现多条 | 使用首条 + 记入兜底事件（提示"sheet 中存在重复任务名"） |

**验收标准**：
- 源 mundo 下 N 个主任务 → 新 mundo 下创建出 N 个主任务，名称按日期规则更新
- 每个新 mission 的起止时间 = 新活动时间
- 资源 sheet 中能匹配上的 mission，rewardBoxId 已替换为新值
- 不匹配的 mission，rewardBoxId 保持源值，且事件已记入兜底清单
- 输出映射表 M2（源 box id → 新 box id）

### 功能 6：抽奖模块复制

**描述**：将源 plan 下「抽奖模块」的全部奖池克隆到新 plan 下，奖池基础配置与源一致，奖品/概率/库存从抽奖资源 sheet 读取。

**调用编排**：
```
Step A. POST /api/livestream/activity/backend/lottery/tenant/list
        (mws: moyi-activity-backend tenant-list)
   入参: activityId = 源 plan 的 spinach panel activityId
         appProductNames = "moyi"（锁定心遇业务）
         page = {pageNum:1, pageSize:100}
   返回: PageResult<TenantBriefInfoVO>（源 plan 下所有奖池）

Step B. 对每个源奖池，调用:
   POST /api/livestream/activity/backend/lottery/tenant/query
        (mws: moyi-activity-backend tenant-query)
   入参: tenantId = 源奖池 tenantId
   返回: TenantConfigVO（完整奖池配置，含 basicInfo / awards / probability / inventory 等）

Step C. 基于源 TenantConfigVO + 抽奖 sheet 构造新 TenantConfigVO:
   - tenantId       = 0/空（让后端生成新 id）
   - basicInfo.remark    = 源奖池名按日期规则改写
   - basicInfo.startTime = 新活动 startTime（必须与新活动时间秒级一致）
   - basicInfo.endTime   = 新活动 endTime（必须与新活动时间秒级一致）
   - basicInfo.activityId = M1[源 spinach panel activityId] → 新 spinach panel activityId
   - tenantExtInfo.poolValue = 抽奖 sheet 的"资产币 ID"
   - 概率类型 / 奖池类型 / 支付方式 / 单抽价格 / 跑马灯 / 暴走 / 推送 IM / 扩展点配置 = 与源一致
   - awards (奖品列表) = 抽奖 sheet 每行构造一个 AwardConfigVO:
       - resourceId / business 中的奖励包 id = sheet 的"奖励包 ID"
       - lose             = sheet 的"是否未中奖奖品"映射 boolean
       - controlMode      = INVENTORY（库存模式，沿用源默认）
       - 其他字段（worth/level/name/icon/sortIndex 等） = 按源对应奖品（按"奖励包 ID"匹配源 award 取剩余字段）
       - 若 sheet 中奖励包 ID 在源 award 中找不到 → 仅用 sheet 字段构造，剩余字段为默认值并记入兜底事件
   - probabilities (概率) = 按 sheet 构造 probMap:
       - probType=10 (SINGLE_BASE 基础权重)     ← sheet 的"基础权重"
       - probType=50 (COMPENSATE 保底权重)      ← sheet 的"保底权重"
       - probType=9  (待 design 阶段确认 enum，作弊权重)  ← sheet 的"作弊权重"
       - **权重填的是数值不是概率**，无 100% 校验
   - inventory (库存) = 按 sheet 构造 InventorySettingDO:
       - cycle  = sheet 的"库存类型"映射 InventoryCycle 枚举
       - stock  = sheet 的"库存数量"

Step D. POST /api/livestream/activity/backend/lottery/template/create
        (mws: moyi-activity-backend template-create)
   入参: config = TenantConfigVO 的 JSON 字符串
   返回: 新奖池 id

Step E. 调用 tenant-query 拉新奖池详情，记录新奖池的 token（用于功能 7 抽奖转盘 patch）
```

**关键约束（基于代码深挖）**：
- **奖池时间必须与活动时间秒级一致**（心遇后端有此校验，否则 template-create 报错）
- **AppProductEnum 锁定 MOYI**

**关键映射表**（功能 6 产出，供功能 7 使用）：
- **M3: 源奖池 id → 新奖池 id**
- **M4: 源奖池 token → 新奖池 token**
- **M5: 源奖池 资产币 id → 新奖池 资产币 id**（注：资产币 id 实际是 sheet 提供的，按"源奖池名 → sheet 资产币 id"映射）
- 这三个映射表后续功能 7 在 patch 抽奖转盘 configJson 时全部要用到

**字段处理规则**：
| 字段 | 处理 |
|---|---|
| 奖池名称 | 源名按日期规则改写 |
| 关联活动 id | M1 映射到新 spinach panel activityId |
| 起止时间 | 新活动时间（秒级对齐） |
| 概率类型 / 奖池类型 / 支付方式 / 单抽价格 | 与源一致 |
| 跑马灯公告 / 暴走配置 / 推送 IM / 扩展点配置 | 与源一致 |
| 资产币 ID | 抽奖 sheet |
| 各奖品的 rewardBoxId、权重、是否未中奖、库存类型、库存数量 | 抽奖 sheet |
| 奖品的其他字段（worth/level/name/icon/sortIndex 等） | 按源 award 对齐 |

**奖池模板类型 (LotteryTemplateEnum)**：
- 本期**都按源照搬**，奖池模板类型与源一致，缺什么字段后续汇总提醒用户（不在 PRD 阶段穷举支持哪些模板）

**边界条件**：
| 场景 | 处理方式 |
|------|----------|
| 源 spinach panel activityId 在 panel-list 中找不到 | 跳过抽奖模块，记入兜底事件 |
| tenant-list 报错 / 0 条奖池 | 跳过抽奖模块，记入兜底事件 |
| 单个 tenant-query 报错 | 跳过该奖池，记入兜底事件，继续下一个 |
| 抽奖 sheet 中存在源奖池找不到的奖品 ID | 仅用 sheet 字段构造，记入兜底事件 |
| 抽奖 sheet 中"库存类型"枚举名无法映射到 InventoryCycle | 跳过该奖品 / 用默认值（待 design 阶段定）+ 记入兜底事件 |
| template-create 报错（时间不一致 / 校验失败等） | 跳过当前奖池，记入兜底事件，继续下一个 |

**验收标准**：
- 源奖池数 = M → 新 plan 下创建出 M 个奖池（剔除报错失败项）
- 每个新奖池的 startTime/endTime 与新活动时间秒级一致
- 资产币 ID、奖品 ID、库存等均与抽奖 sheet 一致
- 输出映射表 M3/M4/M5

### 功能 7：小程序活动模块复制

**描述**：将源 plan 下「小程序活动模块」的全部活动资源 (act-resource) 克隆到新 plan 下，按 type 区分子玩法（type=4 抽奖转盘，type=7 活动任务），处理跨模块 ID 映射 patch 和 ruleText 日期文案替换。

**子玩法限制**：本期支持 `type=4`（抽奖转盘）和 `type=7`（活动任务），其他类型遇到时跳过 + 记入兜底事件。

**调用编排**：
```
Step A. POST /api/social/backend/act/resource/page
        (mws: moyi-activity-backend act-resource-page)
   入参: trackId = 源 plan 的 wechat panel activityId
   返回: PageResult<ActResourceBackendInfoDTO>

Step B. 必须先建 type=7（活动任务），再建 type=4（抽奖转盘）
   理由: 抽奖转盘 configJson 中 taskPlayId 引用活动任务的 id，需先有活动任务的新 id

Step C. 对每个 type=7（活动任务）act-resource:
   - 构造 AddActResourceParamDTO:
     - type = 7
     - trackId  = M1[源 wechat panel activityId] → 新 wechat panel activityId
     - name     = 沿用源 name + 日期规则替换（与 plan 同套规则）
     - configJson = 源 configJson 的字段复制（rewardBoxId 保持源 = "" 或源值；样式字段全部沿用）
   - POST /api/social/backend/act/resource/create
   - 返回新 act-resource id，写入映射表 M6（源活动任务 id → 新活动任务 id）

Step D. 对每个 type=4（抽奖转盘）act-resource:
   - 解析源 configJson，构造新 configJson:
     - token            = M4[源 token] → 新奖池 token
     - relatedPoolId    = M3[源 relatedPoolId] → 新奖池 id
     - relatedTicketId  = M5[源 relatedTicketId] → 新奖池资产币 id
     - relatedActivityId = M1[源 relatedActivityId] → 新 spinach panel activityId
     - poolCount        = 对应新奖池的奖品行数（与抽奖 sheet 一致）
     - relatedPageId    = 沿用源（前端固定页面 id）
     - taskPlayId       = M6[源 taskPlayId] → 新活动任务 act-resource id
     - taskGroupId      = M2[源 taskGroupId] → 新 box id
     - ifHasTask        = 沿用源
     - **ruleText**     = **自动识别替换其中的日期文案**（详见下方"ruleText 替换规则"）
     - 所有图片字段（bgImg/wheelBg/btnImg 等 30+）= **沿用源 URL 不变**
     - 所有颜色字段（pageBgColor/leftColor 等）= 沿用源
   - 构造 AddActResourceParamDTO:
     - type = 4
     - trackId = M1[源 wechat panel activityId] → 新 wechat panel activityId
     - name = 沿用源 name + 日期规则替换
     - configJson = 上面构造的新 JSON
   - POST /api/social/backend/act/resource/create
```

**ruleText 替换规则**（关键，否则新活动展示错误日期）：
- skill 自动识别 ruleText 中**所有日期格式**（与 plan 名称日期识别同一套规则，至少覆盖 `M月D号HH:MM:SS-M月D号HH:MM:SS` 这种）
- 用新活动日期 + 默认时间（开始 15:00，结束 23:59:59）替换
- 若识别失败 / 无日期 token：保留源 ruleText 不变，记入兜底事件（提示运营手工核对 ruleText）

**关键约束**：
- **act-resource 命名**（你确认的 23.b）：沿用源 act-resource 的 `name`，按日期规则替换（不强行使用"<plan name>转盘"这种命名规律）
- **trackId 关联**：act-resource.trackId = wechat panel 的 activityId（不是 plan id、不是 spinach panel id）
- **`subCount` 字段** 在 panel-list 返回中可能不反映实际 act-resource 数量，本期以 `act-resource-page` 返回为准

**边界条件**：
| 场景 | 处理方式 |
|------|----------|
| 源 wechat panel activityId 在 panel-list 中找不到 | 跳过小程序活动模块，记入兜底事件 |
| act-resource-page 报错 | 跳过小程序活动模块，记入兜底事件 |
| 源 plan 中存在 type ∉ {4, 7} 的子玩法 | 跳过该资源，记入兜底事件 |
| 抽奖转盘 configJson patch 时所需映射键缺失（如 token 在 M4 中找不到） | 跳过该资源，记入兜底事件 |
| act-resource-create 报错 | 跳过当前资源，记入兜底事件，继续下一个 |
| ruleText 日期识别失败 | 保留源 ruleText，记入兜底事件 |

**验收标准**：
- 源 plan 下所有 type=4/7 资源均在新 plan 下被复制
- 抽奖转盘的 token / relatedPoolId / relatedTicketId / relatedActivityId / taskPlayId / taskGroupId 全部指向新 plan 的对应资源
- 抽奖转盘的 ruleText 中日期文案已替换为新活动日期
- 所有 act-resource 的 trackId = 新 wechat panel activityId

### 功能 8：兜底事件汇总通知

**描述**：在功能 5/6/7 全部执行完毕后，由主 skill 统一收集执行过程中产生的所有兜底事件（任务 rewardBoxId 匹配失败、奖池创建失败、跨模块映射缺失、白名单外子玩法、ruleText 日期识别失败等），以一条 POPO 消息回复给运营。

**通知消息结构**：
- 头部：新发布计划名称 + 计划 id
- 成功汇总：N 个主任务 / M 个奖池 / K 个小程序活动资源 已成功创建
- 失败明细（按模块分组）：
  - 任务模块：`<计划名> → <主任务名> → <任务组名> → <子任务名>：<失败原因>`
  - 抽奖模块：`<计划名> → <奖池名>：<失败原因>`
  - 小程序活动：`<计划名> → <资源名>：<失败原因>`
  - 跨模块映射缺失：`<计划名> → <子玩法名>：<缺失字段>`
- 尾部：行动建议（"请前往 mws 后台手动补充失败项"）

**持久化策略**：
- 兜底事件**仅存会话内存**，不写外部存储（会话结束即清除）
- 中途运营回复"取消"且新 plan 已创建：机器人**仅提示运营手动清理**（不自动调删除接口，且代码层面 plan 删除接口尚未在 mws 暴露）

**边界条件**：
| 场景 | 处理方式 |
|------|----------|
| 全部模块均无失败事件 | 仅发送成功汇总，无失败明细段 |
| 全部模块均失败 | 仍发送通知，明确告知"新 plan 已创建但所有模块复制失败，请人工处理" |
| POPO 消息超长（> 3000 字符） | 拆分为多条消息按顺序发送 |
| 用户中途取消 | 终止流程；若新 plan 已创建，提示"新 plan 已创建（id=X，name=Y），请前往 mws 后台手动清理" |

**验收标准**：
- 一次完整克隆流程结束后，运营在 POPO 中能收到一条汇总消息，包含成功项数量 + 全部失败项明细
- 失败明细中每条都能定位到具体模块/任务/奖池
- 中途取消时，机器人明确告知运营需要手动清理已创建的新 plan

## 用户场景

### 场景 1：周期性活动按时间复刻（高频场景）

**入口**：POPO 群中 @机器人

**触发条件**：运营每周/每两周需要按相同模板创建下一期 iOS 复购活动

**操作流程**：
1. 运营在 POPO 群 @机器人："帮我创建一个新的活动发布计划"
2. 机器人追问"全新 / 模板克隆"→ 运营回复"模板克隆"
3. 机器人追问"请输入计划名称关键词"→ 运营回复"iOS 复购"
4. 机器人返回候选列表（按名称模糊匹配的近期计划，含起止时间）
5. 运营回复编号"1"，机器人确认选定
6. 机器人追问"请输入新活动的开始日期和结束日期"→ 运营回复"6.1-6.10"
7. 机器人创建新 plan、提示运营发送资源配置在线表格（含任务、抽奖两个 sheet）
8. 运营发送一份 POPO 在线表格链接
9. 机器人依次执行：copyMundo（任务） → tenant-list + template-create（抽奖） → act-resource 按 type=7 → type=4 顺序创建并 patch 跨模块 ID + ruleText 日期文案
10. 机器人发送一条汇总通知（成功项 + 失败明细）
11. 运营前往 mws 后台核查 + 处理失败明细

### 场景 2：非周期性独立活动复刻

**入口**：POPO 私聊机器人

**触发条件**：运营基于某个一次性的特殊活动模板，再做一期类似活动

**操作流程**：与场景 1 一致，差异在于运营输入的计划名称关键词只命中 1-3 条候选。

## 边界条件（全局）

| 场景 | 处理方式 |
|------|----------|
| mws 公共账号鉴权失败 | 提示运营联系管理员检查公共账号配置 |
| 运营在某一步长时间无响应（> 10 分钟） | 当前会话上下文超时回收，运营需重新触发 |
| `plan-create` 成功但后续模块全部失败 | 新 plan 已存在但内部为空，由功能 8 通知运营人工处理；**不**自动删除新 plan |
| 运营在中途回复"取消"或类似意图 | 终止当前会话；若新 plan 已创建，提示运营手动清理（不自动删） |
| mws 环境选择 | **默认 online**；运营在触发语中显式说"测试环境"才切换到 test |

## 非功能需求

- **环境**：默认 `online`；运营明确说"测试环境"才用 `test`
- **响应时间**：每一次运营交互后机器人应在 30 秒内首次响应；整条克隆流程（含人工交互）预期在 10 分钟内完成
- **并发**：单运营同一时刻仅允许一个进行中的克隆会话；不限制不同运营同时克隆同一源 plan
- **鉴权**：使用 mws 公共账号鉴权，禁止 curl / 其他绕过路径
- **兼容性**：当 mws CLI 版本过旧导致接口不可用时，机器人提示运营升级 mws；本 skill 不内嵌 mws schema 副本
- **时区**：所有时间统一使用 `Asia/Shanghai`

## 非目标（本期不做）

- 创建「全新发布计划」（无模板）：功能 1 分支返回"建设中"，本期不实现
- 模板分类自动识别（周期性 vs 孤立）：由运营从候选列表手动选定
- 资源配置文件的「在线编辑器」：本期仅消费运营自行维护的 POPO 在线表格
- 跨业务线复用：本期仅服务心遇 (`AppProductEnum = MOYI`)，不抽象通用「活动平台克隆」能力
- 模块类型扩展：本期仅支持 `mission / spinach / wechat`，其他模块跳过 + 告警
- 子玩法扩展：小程序活动仅支持 type=4 抽奖转盘 + type=7 活动任务
- 失败自动回滚：本期采用「不回滚 + 告警」策略
- 失败自动清理：运营取消时新 plan 不自动删除（且 mws 未暴露 plan 删除接口）
- 创建后的活动审批 / 发布 / 上下线操作：本期仅做创建
- 资源配置表格的版本管理 / 变更审计：本期表格仅作为一次性输入消费
- 任务模块与抽奖模块的 tenantId 耦合处理：本期 mission.tenantId 保持源值不映射替换
- 兜底事件持久化：本期仅会话内存

## Capabilities

### 新增能力

- `moyi-activity-create`：心遇活动发布计划克隆主流程，承载 POPO 入口触发、运营多轮交互（LLM 意图识别）、新 plan 创建、子模块编排调度（任务 → 抽奖 → 小程序活动顺序）、跨模块 ID 映射表管理（M1-M6）、兜底事件汇总通知
- `moyi-mission-clone`：心遇任务模块克隆，通过 `copyMundo` 一键克隆 mundo+box+mission 树，按任务名称反查覆盖 rewardBoxId，输出映射表 M2（源 box id → 新 box id）
- `moyi-lottery-clone`：心遇抽奖模块克隆，遍历源奖池 → query 详情 → 按抽奖 sheet 构造新 TenantConfigVO → template-create，输出映射表 M3/M4/M5（奖池 id / token / 资产币 id）
- `moyi-act-resource-clone`：心遇小程序活动模块克隆，按 type=7 → type=4 顺序创建 act-resource，对抽奖转盘 configJson 做 6 项跨模块 patch（token/relatedPoolId/relatedTicketId/relatedActivityId/taskPlayId/taskGroupId）+ ruleText 日期文案自动替换
- `moyi-resource-sheet-parser`：心遇活动资源配置表格解析（POPO 在线表格读取 + 任务 sheet 和抽奖 sheet 解析 + 字段校验），通过调用 `popo-doc-read` 实现表格读取，供 `moyi-mission-clone` 与 `moyi-lottery-clone` 共同消费

### 修改能力

_无_

## 已知 finding 项（design 阶段需消化）

- **作弊权重 probType 枚举值**：用户口述为 9，但代码 ProbabilityTypeEnum 中需验证具体枚举（design 阶段查 `social-activity-spinach` 仓库）
- **库存类型 sheet 列值映射**：sheet 中"一次性库存"/"无限量"/"每日库存" 等中文需精确映射到 InventoryCycle 枚举（1-8）
- **抽奖 sheet 多奖池场景**：当源 plan 含多个奖池时，sheet 内"抽奖-1"/"抽奖-2" 与源奖池的对齐策略需 design 阶段验证（按 sheet 顺序对齐 vs 按奖池名匹配）
- **日期 token 识别正则覆盖范围**：至少要支持 `M.D-M.D` / `M/D-M/D` / `MMDD-MMDD` / `M月D号HH:MM:SS-M月D号HH:MM:SS`（用于 plan 名 + ruleText）；其他格式如 `YYYY-MM-DD` 是否需要支持待 design 阶段定
- **POPO 在线表格读取实际兼容性**：本期复用 `popo-doc-read` skill 凑合（仓库无专用 sheet skill），design 阶段需验证 popo-doc-read 对在线表格的实际解析能力，若不足则在 design 阶段提案新建 `popo-sheet-read` skill
- **allowCreatePlanGapMinutes 后端校验值**：design 阶段需调 `/api/livestream/activity/domain/module/list` 拿到当前配置值，让 skill 在提示运营时告知"开始时间需至少 N 分钟后"
- **panel-list 的 subCount 字段语义**：真实数据显示有 2 个 act-resource 但 subCount=0，design 阶段需确认 subCount 的统计口径
- **新奖池资产币 id 来源细节**：抽奖 sheet 提供资产币 id 后，与"哪个源奖池"的映射在多奖池时如何确定
- **跨模块 ID 映射 M2（源 box id → 新 box id）的对齐策略**：copyMundo 创建的新 box 与源 box 的对应关系，可能需按"任务组名"匹配或按顺序对齐，design 阶段需确认
- **mws 中是否有 plan 删除接口**：当前 mws 列出的方法里未见，若运营误操作创建错 plan，目前只能在 mws 后台手工删，design 阶段可考虑请求 mws 团队补充
