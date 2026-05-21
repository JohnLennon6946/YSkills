# mws-xinyu-activity-create 发现与决策

> 创建日期: 2026-05-20
> 本文档在开发全程持续更新

## 技术决策

### 决策 1：任务模块复制 — 直接复用 copyMundo 接口

- **决策**：用 `POST /api/social/mission/backend/copy/mundo` 一键克隆 mundo+box+mission 树，然后遍历新 mission 调 `info-save` 替换 rewardBoxId
- **理由**：`MissionBackendCopyReq` 入参本身就支持 `missionName / startTime / endTime / business`，后端已经实现了完整复制逻辑（递归复制所有 box + mission，重置 id + 关联新 activityId），本期不需要重新发明轮子
- **放弃方案**：手工调 mundo-save + 遍历构造 box/mission 调 info-save。控制力强但工作量大、与后端逻辑耦合度高，且 mundo-save 自身实现里也是调用相同的 saveMundo+saveMissionBox+saveMission，意义不大
- **关键代码引用**：`social-activity-mission/infrastructure/.../MissionBackendSofaServiceImpl.java:150` (copyMundo 实现)

### 决策 2：任务与抽奖本期不耦合（mission.tenantId 不映射）

- **决策**：mission.tenantId 字段保持源值，不做"源奖池 token → 新奖池 token" 映射
- **理由**：用户明确确认本期不耦合；耦合后会增加 spec 复杂度
- **放弃方案**：维护映射表 M4 时一并 patch mission.tenantId
- **遗留风险**：若源任务关联了奖池，新活动的"任务完成给抽奖机会"逻辑会指向**源 plan 的奖池**而非新 plan 的奖池，可能造成数据混乱
- **缓解措施**：design 阶段查 iOS复购5.19-5.24 真实 mission.tenantId 是否非空；若非空，将该风险升级为本期阻塞项

### 决策 3：跨模块强耦合处理 — 严格顺序 + 6 张映射表

- **决策**：复制流程严格按 `任务 → 抽奖 → 小程序活动 (type=7 先, type=4 后)` 顺序执行，过程中维护 6 张映射表 M1-M6，在 type=4 抽奖转盘 configJson 中 patch 6 个跨模块引用字段（token / relatedPoolId / relatedTicketId / relatedActivityId / taskPlayId / taskGroupId）
- **理由**：真实 configJson 数据显示这些字段直接指向任务模块 box id 和活动任务 act-resource id，不 patch 会导致新 plan 的抽奖转盘指向源 plan 资源，**有线上事故风险**
- **放弃方案**：保持源值不变。运营会被迫去 mws 后台手工改 6 个字段，违背 skill 自动化初衷

### 决策 4：ruleText 日期文案 — 自动识别替换

- **决策**：skill 在 patch 抽奖转盘 configJson 时，自动识别 ruleText 中的日期文案并按新活动日期替换
- **理由**：真实 configJson 数据显示 ruleText 头部含"活动时间：5月19号15:00:00-5月24号23:59:59"，是直接展示给最终用户的关键文案，不替换会显示错误日期
- **放弃方案**：让运营手工改（运营负担重 + 易遗漏 + 违背自动化初衷）
- **风险**：日期正则识别不全可能漏改，需要在 finding F7 中收敛正则覆盖

### 决策 5：默认时间 = 15:00:00 ~ 23:59:59

- **决策**：开始时间 = 开始日期 15:00:00（Asia/Shanghai），结束时间 = 结束日期 23:59:59
- **理由**：iOS复购5.19-5.24 真实数据是 15:00:00 起，ruleText 也写的 15:00；与生产实际对齐
- **放弃方案**：14:00（用户初版口述，但与真实数据不符）
- **后果**：奖池时间需与活动时间秒级一致的后端校验（功能 6 提到）天然满足

### 决策 6：AppProductEnum 锁定 MOYI

- **决策**：所有 lottery / template 相关接口 `appProductNames = "moyi"`
- **理由**：本期专注心遇业务，不混业务线
- **影响**：spinach service 多业务线代码路径 (ichat/mirth/look 等) 本期不涉及

### 决策 7：本期 modules 白名单 = mission / spinach / wechat

- **决策**：源 plan 含其他模块类型（rank/shop/hourLottery 等 30+）时，plan-create 时仍传入模块清单（保证新 plan 模块结构一致），但**不复制其内部内容**，记入兜底事件清单
- **理由**：iOS 复购 plan 真实数据确认仅 mission/spinach/wechat 三个模块；其他模块的内部数据结构 + 复制逻辑超出本期范围

### 决策 8：plan-create 字段 domain / noticeCorps 沿用源

- **决策**：新 plan 的 domain / noticeCorps 直接沿用源 plan（不让运营单独填）
- **理由**：周期性活动这两个字段几乎不变（iOS复购系列连续多期 noticeCorps 都是 ["wangguojian"]、domain 都是 "act"）；运营每次填增加负担
- **放弃方案**：让运营每次输入；或让运营自己手动改 plan-create 入参

### 决策 9：plan 命名生成规则

- **决策**：
  - 识别源 plan 名称中的日期 token（如 `5.19-5.24`、`5/19-5/24`、`0519-0524`）
  - 识别到 → 用新日期 token 替换原 token，保持 token 格式
  - 未识别到 → 在源名称末尾追加 ` <新开始日期>-<新结束日期>`（默认 `M.d` 格式）
- **理由**：iOS复购系列命名格式（`<前缀><M.d-M.d>`）是高频常见模式
- **遗留**：完整正则覆盖范围在 F7 中收敛

### 决策 10：资源配置文件 = 一份 POPO 在线表格多 sheet

- **决策**：任务 sheet + 抽奖 sheet 在同一份 POPO 在线表格中；通过 `popo-doc-read` skill 读取（仓库无专用 popo-sheet-read）
- **理由**：运营熟悉 POPO 在线表格；多文件管理复杂度高；用现有 popo-doc-read 凑合避免新建依赖
- **遗留风险**：popo-doc-read 对在线表格的实际解析能力需 design 阶段验证（见 F8）

### 决策 11：权重无 100% 校验

- **决策**：基础权重 / 保底权重 / 作弊权重三类只作为**数值**直接写入后端，不强制权重和 = 100%
- **理由**：后端 probMap 存的是权重数值（按比例归一化为概率），不是百分比；硬校验会过度限制运营
- **放弃方案**：在 sheet 收集时强校验权重和 = 100%（PRD v1 错误地写了这条校验，已修订）

### 决策 12：POPO bot 新建独立服务

- **决策**：本期新建专用 POPO bot 服务承载本 skill；不复用 plurk-mcp 框架
- **理由**：心遇业务专属入口；权限隔离 + 部署独立
- **影响**：skill 与 bot 服务之间需约定接口契约（design 阶段定）

### 决策 13：触发语 LLM 意图识别

- **决策**：运营触发语用 LLM 自由意图识别，非严格关键词匹配
- **理由**：运营自然语言表达多样化，关键词难穷举

### 决策 14：默认 online 环境

- **决策**：默认 `--env online`；运营明确说"在测试环境"才切换到 `--env test`
- **理由**：运营主要工作在 online；test 是少数验证场景

### 决策 15：兜底事件仅会话内存 + 中途取消手动清理

- **决策**：失败兜底事件不持久化，会话结束即清除；运营回复"取消"时机器人仅提示运营手动清理新 plan，不自动调删除接口
- **理由**：会话短期内运营能看完，无需持久化；且 mws 未暴露 plan 删除接口（F4 已验证）

---

## 调研结论（PRD 末尾 10 项 finding 的现场调研）

### F1: probType 枚举值定位 ✅ 已全部查清（含动态档位机制）

**通用层 probType 定义**（来自 `social-activity-spinach/business/.../ActivityCommonConst.java:10-38` + `social-activity-spinach/shared/.../ActivityProbabilityType.java:12-29`）：

| code | enum 名 | 含义 | 用户口述对照 |
|---|---|---|---|
| 1 | DEFAULT | 默认概率 | — |
| 8 | COMPENSATE_WITH_LOSE | 补偿未中奖概率 | — |
| **10** | SINGLE_BASE | 单抽基础概率 | ✅ **基础权重** |
| 20 | TEN_BASE | 十连抽基础概率 | — |
| 21 | TEN_MUST_WIN | 十连抽必中概率 | — |
| 30 | HUNDRED_BASE | 百连抽基础概率 | — |
| 31 | HUNDRED_MUST_WIN | 百连抽必中概率 | — |
| 40 | FREE | 免费券概率 | — |
| **50** | COMPENSATE | 补偿奖品概率 | ✅ **保底权重** |
| 51 | COMPENSATE + 1 | 首抽场景的补偿概率 | — |
| 100 | FIRST / ANTI_CHEAT | 首抽 / 反作弊（不同业务复用同一 code） | — |
| 103 | PERSONAL_MINIMUM_GUARANTEE_STATUS | 个人抽奖兜底权重 | — |
| 104 | ALL_MINIMUM_GUARANTEE_STATUS | 全服抽奖兜底权重 | — |

**关键发现：心遇活动 probType 是动态计算的**（来自 `social-activity-spinach/business/.../core/godness/MoyiActivityRoundGenerateAction.java:47-50`）：

```java
Integer defaultProbType = ActivityProbabilityType.SINGLE_BASE.getType();  // = 10
int probabilityType = request.getLotteryContext().getChangeLevel() != null
        ? defaultProbType + request.getLotteryContext().getChangeLevel()  // = 10 ± changeLevel
        : defaultProbType;
```

也就是说，心遇活动会根据 `changeLevel` **动态调整**用户抽奖时的 probType 档位：
- `changeLevel = -1` → `probType = 9`（**降级一档，即"作弊用户"抽奖时用的权重**）
- `changeLevel =  0` 或未设置 → `probType = 10`（**SINGLE_BASE 基础权重**）
- `changeLevel = +1` → `probType = 11`（升级一档，奖励性升档，若启用）

**真实数据印证**（用户提供的 iOS复购5.19-5.24 奖池 tenant-query 响应）：
- 每个奖品 probMap 都有 `{10: X, 50: Y, 9: Z}` 三个 key
- `9` 与 `50` 的值规律相同（金币5: 100/100; 桃气满满: 300/300; 芝芝芒芒: 300/300; 精灵花环: 150/150）
- `10` 是大概率（普通用户中奖）

**结论（覆盖之前错误的判断）**：
- 用户口述的"基础权重 = 10" ✅ **完全确认**（SINGLE_BASE）
- 用户口述的"保底权重 = 50" ✅ **完全确认**（COMPENSATE）
- 用户口述的"作弊权重 = 9" ✅ **完全确认**（SINGLE_BASE - 1 的动态降级档）

**对 skill 的影响**：
- 抽奖资源 sheet 中"基础权重 / 保底权重 / 作弊权重"三列分别对应 probType `10 / 50 / 9`
- 写入 probMap 时必须包含这 3 个 key（即使值为 0），与真实生产数据保持一致
- 若未来支持更多动态档位（如 changeLevel=+1 用 probType=11），sheet 需要扩展列

### F2: InventoryCycle 枚举映射 ✅ 已查清

**最新枚举定义**（来自 `social-activity-spinach/shared/.../enums/InventoryCycle.java`）：

| code | enum 名 | 后端 desc | sheet 可能写法 |
|---|---|---|---|
| 1 | DAILY | "每日库存" | "每日" / "每日库存" |
| 2 | HALF | "半天库存" | "半天" / "半天库存" |
| 3 | HOURLY | "每小时库存" | "每小时" / "每小时库存" |
| 4 | ONCE | "一次性库存" | "一次性" / "一次性库存" ← **用户 sheet 示例** |
| 5 | NO_LIMIT | "无限库存" | "无限" / "无限量" / "无限库存" ← **用户 sheet 示例** |
| 6 | THREE | "3小时库存" | "3 小时" / "三小时" |
| 7 | SIX | "6小时库存" | "6 小时" / "六小时" |
| 8 | MIN_10 | "10分钟库存" | "10 分钟" / "十分钟" |

**结论**：
- 8 个枚举值全部确认
- skill 解析时需做**容错映射**：
  - **优先**精确匹配 desc（"一次性库存" → 4）
  - **次选**模糊匹配关键词（含"无限" → 5、含"一次" → 4、含"每日" → 1 等）
  - 仍无法匹配 → 记入兜底事件 + 跳过该奖品
- 旧版 `InventoryCycleEnum`（api 层）只到 code=7，缺 MIN_10；统一使用 shared 层的 `InventoryCycle`

### F3: panel-list 的 subCount 字段语义 ✅ 已查清

**代码定位**：`social-activity-mdm/.../ActPanelConfigServiceImpl.java:248-269` (assembleMundoInfo)
- subCount 来自各模块通过 RPC 扩展点 `IActMdmMundoInfoQueryExt.queryActModuleInfo(activityId)` 上报
- 各模块需要自己实现这个扩展点
- 真实数据显示 wechat panel subCount=0 但实际有 2 个 act-resource，说明 wechat 模块**没实现这个扩展点**或返回的 count 不准

**结论**：
- subCount **不能可靠反映 act-resource 实际数量**
- skill 实现时**直接调 `act-resource-page`** 查实际数据，不依赖 subCount

### F4: mws 中 plan 删除接口 ✅ 已查清（确认无）

- `mws moyi-activity-backend -h` 输出的 14 个方法中**无 plan-delete / plan-remove 等**
- 代码 grep `plan/delete | deletePlan | deleteActPlan` **未找到**任何匹配
- 后端可能根本没暴露 plan 删除接口（只有下线 offlineMundo 等状态变更）

**结论**：
- 运营取消时机器人**无能力自动清理新 plan**
- skill 提示"请前往 mws 后台手工清理"即可（与 PRD 决策 15 一致）
- 未来若需自动清理：先推动 mws 团队或后端补充 plan-delete 接口

### F5: allowCreatePlanGapMinutes 后端校验值获取 ⚠️ 部分查清

- 代码：`actModuleNoticeConfigAdapter.getActPlanConfigDTO().getAllowCreatePlanGapMinutes()`
- HTTP 接口：`/api/livestream/activity/domain/module/list`
- **mws 中此命令未暴露**（不在 14 个方法清单内）

**结论**：
- skill 没有 mws 命令可以直接拿到该值
- **采用"事后兜底"策略**：plan-create 报错时把后端报错原样反馈给运营（如 "活动开始时间需要在 30 分钟后"），引导运营重新选日期
- 若运营反馈频繁触发该错误：design 阶段可让运营自己告知该值并写死在 skill 里，或推动 mws 暴露 domain-module-list 接口

### F6: 抽奖 sheet 多奖池场景（PRD 未澄清，需追加用户澄清）

**当前状况**：
- 用户给的 sheet 示例只有 1 个"抽奖" sheet
- 真实 iOS 复购 plan 的 spinach panel 只有 1 个奖池（subCount=1，但需用 tenant-list 验证）
- **多奖池场景的 sheet 结构未定**

**待 design 阶段澄清**（已加入 design 阶段澄清池）：
- 多奖池时 sheet 名怎么命名（"抽奖-1"/"抽奖-2" 序号 vs "奖池名" vs 其他）
- sheet 与源奖池的对齐策略（按 sheet 名匹配 vs 按顺序对齐）
- 当前**iOS 复购系列大概率永远单奖池**，多奖池场景可能本期不需要

### F7: 日期 token 识别正则覆盖范围（待 design 收敛）

**已确认的真实生产格式**：
- plan name 中：`M.d-M.d`（如 `5.19-5.24`）
- ruleText 中：`M月d号HH:MM:SS-M月d号HH:MM:SS`（如 `5月19号15:00:00-5月24号23:59:59`）

**design 阶段收敛清单**（建议至少覆盖）：
- `M.d-M.d`（plan 名常见）
- `M/d-M/d`（plan 名可能格式）
- `MMdd-MMdd`（plan 名可能格式）
- `M月d号HH:MM:SS-M月d号HH:MM:SS`（ruleText 已确认）
- `M月d日-M月d日`（ruleText 可能简化版）
- `M月d号-M月d号`（ruleText 可能简化版）

**design 阶段需补充**：跑一遍历史 iOS 复购系列 ruleText 抓出实际出现过的所有日期格式

### F8: POPO 在线表格读取兼容性 ⚠️ 待 design 阶段实测

**当前状况**：
- 仓库无专用 popo-sheet-read skill
- 现有 popo-doc-read 只支持文档（doc/PDF/DOCX 等）
- 决策是用 popo-doc-read 凑合，但**实际能否解析在线表格未验证**

**design 阶段必须实测**：
1. 拿运营真实在线表格链接，跑一遍 popo-doc-read 看返回的内容结构
2. 验证：
   - 多 sheet 是否能区分
   - 表头跨行（如抽奖 sheet 的 3 行表头区）是否能识别
   - 单元格特殊字符（带逗号 / 特殊符号 / 表情等）是否完整保留
3. 若 popo-doc-read 完全无法解析在线表格：**design 阶段必须提案新建 `popo-sheet-read` skill**（用 POPO 官方表格 API），否则本期无法上线

### F9: 跨模块映射 M2（源 box id → 新 box id）对齐策略

**copyMundo 内部逻辑**（来自 `MissionBackendSofaServiceImpl.java:171-189`）：
- 遍历源 missionBoxes，按顺序逐个调 saveMissionBox
- 新 box 的 id 由数据库自增生成
- **顺序确定的情况下，源 box 顺序 vs 新 box 顺序保持一致**

**结论**：
- 主对齐策略：**按 mundo-query 返回的 missionBoxes 顺序索引对齐**（源 [0] ↔ 新 [0]、源 [1] ↔ 新 [1]）
- 备用对齐策略：用 `missionBoxName` 匹配（万一某个 box saveMissionBox 失败导致顺序错位）
- design 阶段需补：失败时如何降级（按名字匹配？跳过该 box？）

### F10: 新奖池资产币 id 来源（用户已部分回答，待 design 完善）

**用户答案**：
- sheet 表头区第 2/3 行存"资产币ID"（单值，如 `2003754`）

**待 design 阶段细化**：
- **多奖池场景**：所有奖池共用一个资产币 id？还是每个奖池有独立资产币 id？
- 若每奖池独立：sheet 结构如何容纳（每个奖池 sheet 各自的表头区？）
- 当前本期假设：**单奖池场景共用一个资产币 id**（iOS 复购系列符合此假设）

---

## 新增 finding（代码深挖发现的、PRD 未覆盖的）

### F11: copy/mundo 在 mws 中未暴露 ⚠️

- 代码 `MissionV2BackendController.java:452` 有 `POST /api/social/mission/backend/copy/mundo` 接口
- 但 `mws moyi-activity-backend -h` 列出的 14 个方法中**不包含 copy-mundo**
- 决策 1 依赖此接口

**应对**：
- 短期：用 `mws schema moyi-activity-backend.copy-mundo` 验证；若不可用，**推动 mws 暴露**或在 design 阶段改用手工 mundo-save + 遍历构造方案（决策 1 的放弃方案）
- design 阶段必须先确认 mws 可用性

### F12: act-resource 命名实际规律观察

- 真实数据：
  - 抽奖转盘 (type=4) name = `iOS复购5.19-5.24转盘`
  - 活动任务 (type=7) name = `iOS复购5.19-5.24`
- 决策 23.b（沿用源 name + 日期替换）合理，但需要 design 阶段额外处理"沿用源 name 时识别日期 token"

### F13: domain-module-list 接口在 mws 未暴露

- 即决策 8 中"沿用源 plan 的 domain"虽然能直接读 plan-list 返回，但 domain 合法性校验（`ActDomainNameEnum.fromDomain`）在 plan-create 里做
- 若源 plan 的 domain 在最新枚举中已废弃 → plan-create 会失败
- 概率极低（iOS 复购系列 domain="act" 是常见值），但需在 design 阶段评估

### F14: plan-create 异常时新 panel 已创建副作用

- plan-create 用事务 `transactionHelper.inTransaction`，失败会回滚
- 但若失败发生在功能 5/6/7（任务/抽奖/小程序复制）中途：新 plan + 部分模块已落库
- 决策 15（不回滚 + 告警 + 提示手动清理）已覆盖此场景

### F15: ruleText 还可能包含金额、规则文案的活动周期描述

- 真实 ruleText 含"完成签到任务可获得1张免费抽奖券"、"当累计充值【6】元时" 等
- 这些**与时间无关的文案**保持源即可
- 但"活动时间"附近的日期文案是必替换的，识别范围要精准（避免误改奖励数量）

### F16: 真实奖池数据带出的字段精确语义 ✅ 全部澄清

用户提供的 iOS复购5.19-5.24 奖池 (tenantId=601111) tenant-query 完整响应，确认以下字段语义：

**奖池基础信息**：
- `template = "inventoryNormal"` — 奖池模板类型（LotteryTemplateEnum 之一），本期照搬源不变
- `basicInfo.remark` = 奖池名（不是 name 字段！这是个易踩坑点）
- `basicInfo.token` = 奖池对外标识（IDObfuscation 混淆生成），act-resource 用此值
- `basicInfo.activityId` = 22095431 = spinach panel 的 activityId（不是 plan id）

**奖池扩展信息 tenantExtInfo**：
- `interestEnableStatus = 1` → 资产币模式（SpinachPayTypeEnum.INTEREST）
- `interestId = 2003754` → **资产币 ID**（与 act-resource configJson 的 `relatedTicketId` 完全一致）
- `ticketPrice = 0.0`, `price = 0` → 资产币模式下不用单抽价格
- `floorAwardRate = null` → 心遇本期不用保底返奖率
- `personalMiniGuaranteeCount = 0`, `allMiniGuaranteeCount = 0` → 不启用兜底次数

**奖品 AwardConfigVO 字段**（每个 award 多一些之前没注意的字段）：
- `awardId` ≠ `rewardBoxId` —— 两个独立 id，**awardId 是 spinach 自己的奖品 id；rewardBoxId 是奖励包系统的 id**（关键！sheet 里运营填的是 rewardBoxId）
- `awardName` — 奖品名（仅供运营辨识，skill 沿用源即可）
- `worth` — 奖品价值（沿用源）
- `level` — 等级（沿用源，多为空字符串）
- `inventoryType` — 库存类型（数字 code，1-8 → InventoryCycle 枚举）
- `inventoryNum` — **配置库存数**（运营在 sheet 里填的"库存数量"对应此字段；可能始终为 0）
- `currentInventoryNum` — **当前剩余库存**（运行时计数，**克隆时无意义**，新奖池应置 0）
- `needPush` / `needAnnounce` — 推送/公告开关（沿用源）
- `lose` — 是否未中奖奖品（sheet 的"是否未中奖奖品"对应此字段，真实数据多为 false）
- `sortIndex` — 排序（沿用源）
- `probMap` — **必须包含 10 / 50 / 9 三个 key**（基础/保底/作弊权重数值），见 F1
- `wildtimeFactors / awardType / nosKey / amount / ext` — 沿用源（多为 null / 0）

**对 PRD/skill 实现的影响**：
- 奖品名字段叫 `awardName`（不是 `name`）
- 奖池名字段叫 `basicInfo.remark`（不是 `basicInfo.name`）
- 资产币 ID 字段叫 `tenantExtInfo.interestId`（不是 poolValue / ticketPrice）
- 库存数量字段是 `inventoryNum`（写入用），`currentInventoryNum`（运行时计数）克隆时应置 0
- 复制奖品时如能保留 `awardId` 也保留，但**新奖池的 awardId 应由后端重新生成**（设置为 0 让后端 auto-increment）

### F17: tenant-query 中 `tenantExtInfo.gifts` / `probTypeInfos` / `sceneCodes` / `adminUsers` 等高级字段在 iOS 复购数据里为 null

- 这些字段都是 null（即 iOS 复购系列不用这些扩展配置）
- skill 复制时直接 `null` → `null` 沿用即可
- 若未来其他 plan 用了这些字段，需要补充扩展逻辑

### F18: tenantAnnounceConfig 真实数据是 `{id: 2949125, content: null}`

- 跑马灯公告配置只有 id，content 为 null
- 推测：tenant-query 返回的 announce content 是异步加载或单独接口；克隆时只需保留 id 引用关系
- design 阶段确认：若 id 是跨 tenant 复用的（公告库），复制时直接照搬 id；若 id 是 tenant 私有的，需要新建公告

### F19: tenantWildConfigVO / extensibleConfigVO 在 iOS 复购数据里为 null

- 暴走配置 / 扩展点配置都是 null
- 本期不需要处理这些配置（与 F17 同）

### F20: copy-mundo 参数语义 ✅ 已通过 schema 确认

**问题**：初版 spec 将 `activityId` 和 `aimActivityId` 写反（`activityId = 源`，`aimActivityId = 0`）。

**schema 实际语义**（来自 `mws schema moyi-activity-backend.copy-mundo`）：
- `activityId` = "新活动 ID（克隆后的**目标**活动）" — 应传新 plan 的 mission panel activityId
- `aimActivityId` = "源活动 ID（被克隆的活动）" — 应传源 plan 的 mission panel activityId

**接口描述原文**：基于源活动（aimActivityId）的配置整体克隆出新的活动主任务，并替换为传入的 activityId / 时间区间 / 任务名等基础信息。

**已修复**：xinyu-mission-clone spec 已修正参数映射，并增加源 mundo-query 步骤。

### F21: act-resource-create 返回 BooleanResult ⚠️ 无法直接获取新 ID

**问题**：`act-resource-create` 响应是裸 boolean（true/false），不返回新资源 ID。M6 映射表需要新 act-resource ID。

**解法**：创建成功后反查 `act-resource-page`（按新 trackId + name 过滤）获取新 ID。

**风险**：
- 若同名资源已存在，反查可能命中旧资源 → 建议反查时取 createTime 最新的一条
- 若创建成功但后端异步处理导致反查瞬间查不到 → 增加短延时重试（最多 2 次，间隔 1s）

**已修复**：xinyu-act-resource-clone spec 已增加"创建后反查"步骤。

### F22: act-resource-page / tenant-list 分页处理

**问题**：两个接口都是分页接口（page.from / page.size），iOS 复购系列数据量小（2 个 act-resource、1 个 tenant），但**若未来用于其他 plan 或 plan 膨胀**，单次请求可能拿不完。

**解法**：首次 from=0, size=100；若 page.total > 100 则继续翻页。实际 iOS 复购系列不会触发此分支。

**已修复**：两个 spec 已增加分页翻页逻辑。

### F23: AddActResourceParamDTO 无 status 字段

**问题**：`act-resource-create` 的请求体 schema 不含 `status` 字段。初版 spec 写 "status = 沿用源" 不成立。

**实际行为**：新创建的 act-resource 由后端控制初始状态（推测默认 status=0 下线），运营后续在后台手动上线。

**已修复**：spec 移除 status 字段，注明由后端决定初始状态。

---

## 踩坑记录

<!-- 开发过程中持续填充 -->

_暂无_

---

## 变更摘要

| 日期 | 变更内容 | 原因 | 影响范围 |
|------|----------|------|----------|
| 2026-05-20 | 初版创建 FINDINGS.md | 沉淀 PRD 阶段决策 + 10 项 finding 调研结论 + 5 项代码深挖新发现 | 全文 |
| 2026-05-20 | 修正 F1 + 新增 F16-F19 | 用户提供 iOS复购5.19-5.24 奖池 tenant-query 真实数据后，确认 probType=9 是 SINGLE_BASE-1 动态降级档（作弊权重），并提炼出多个奖池字段精确语义 | F1, F16, F17, F18, F19 |
| 2026-05-21 | 新增 F20-F23 | 对照 mws schema 逐接口审计 spec，发现 copy-mundo 参数写反、act-resource-create 无法返回新 ID、分页未处理、status 字段不存在等 4 类问题 | F20-F23, 同步修正 spec |
