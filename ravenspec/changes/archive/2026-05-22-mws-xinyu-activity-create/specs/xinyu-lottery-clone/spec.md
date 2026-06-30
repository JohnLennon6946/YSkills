# xinyu-lottery-clone 能力规范

> 心遇抽奖模块克隆 — 子 skill

## ADDED Requirements

### Requirement: 抽奖模块克隆主流程

本 skill 必须接收源 spinach panel activityId + 新 plan 信息（新 plan 活动 ID / 新活动起止时间） + 抽奖资源数据（来自 xinyu-resource-sheet-parser），完成源 plan 下所有奖池的复制。

#### Scenario: 标准克隆流程

- **WHEN** 主 skill 调用本 skill 并传入合法的源 spinach panel activityId + 新 plan 信息 + 抽奖资源数据
- **THEN** 必须依次执行：
  1. 调用 `POST /api/livestream/activity/backend/lottery/tenant/list`（mws: `tenant-list`），入参 `activityId` = 源 spinach panel activityId，`appProductNames` = "moyi"，分页拉取**所有**源奖池（首次 from=0, size=100；若 page.total > 已拉取数则继续翻页）
  2. 对每个源奖池，调用 `POST /api/livestream/activity/backend/lottery/tenant/query`（mws: `tenant-query`）拉完整 TenantConfigVO
  3. 基于源 TenantConfigVO + 抽奖资源数据构造新 TenantConfigVO（字段映射见后续 Requirement）
  4. 调用 `POST /api/livestream/activity/backend/lottery/template/create`（mws: `template-create`），入参 `config` = 新 TenantConfigVO 的 JSON 字符串；template-create 返回完整 TenantConfigVO（含新 tenantId）
  5. 从 Step 4 返回值中提取新奖池 tenantId / basicInfo.token / tenantExtInfo.interestId
  6. 输出：映射表 M3（源奖池 id → 新奖池 id）+ M4（源奖池 token → 新奖池 token）+ M5（源奖池 interestId → 新奖池 interestId）

### Requirement: 奖池字段构造规则

本 skill 必须按以下规则构造新 TenantConfigVO 的字段。

#### Scenario: 基础信息字段

- **WHEN** 构造新 TenantConfigVO.basicInfo
- **THEN** 必须设置：
  - `remark` = 源 remark 按日期规则改写（识别日期 token 则替换；未识别则末尾追加 `M.d-M.d`）
  - `startTime` = 新活动 startTime（毫秒，必须与新 plan startTime **秒级一致**）
  - `endTime` = 新活动 endTime（毫秒，必须与新 plan endTime 秒级一致）
  - `activityId` = 主 skill 映射表 M1 中"源 spinach panel activityId → 新 spinach panel activityId"
  - `token` = 0 / 空（让后端通过 IDObfuscation 生成）
  - `status` = 沿用源

#### Scenario: 扩展信息字段

- **WHEN** 构造新 TenantConfigVO.tenantExtInfo
- **THEN** 必须设置：
  - `interestEnableStatus` = 沿用源（如 1 表示资产币模式）
  - `interestId` = 抽奖资源数据中的"资产币 ID"列（如 sheet 提供 `2003754`）
  - `ticketPrice` / `price` / `floorAwardRate` / `periodType` / `personalMiniGuaranteeCount` / `allMiniGuaranteeCount` / `compensateWithDeduct` = 沿用源
  - `gifts` / `probTypeInfos` / `sceneCodes` / `adminUsers` / `labelId` / `financeMsg` = 沿用源（多为 null）

#### Scenario: 模板类型与高级配置

- **WHEN** 构造新 TenantConfigVO
- **THEN** 必须设置：
  - `template` = 沿用源（LotteryTemplateEnum）
  - `appProductName` = "moyi"
  - `tenantPushImConfig` / `tenantAnnounceConfig` / `tenantWildConfigVO` / `extensibleConfigVO` / `levels` = 沿用源

### Requirement: 奖品 (AwardConfigVO) 构造规则

本 skill 必须按抽奖资源数据构造每个奖品。

#### Scenario: 单个奖品字段构造

- **WHEN** 抽奖资源数据中存在一条奖品记录
- **THEN** 构造一个 AwardConfigVO，字段映射：
  - `awardId` = 0（让后端 auto-increment）
  - `rewardBoxId` = 资源数据的"奖励包 ID"列
  - `awardName` / `level` / `worth` / `needPush` / `needAnnounce` / `sortIndex` / `wildtimeFactors` / `awardType` / `nosKey` / `amount` / `ext` = 按"奖励包 ID"匹配源 award 取源值；源中找不到则用默认值（"", "", 0, false, false, 0, null, 0, null, 0, null）
  - `inventoryType` = 资源数据"库存类型"列经枚举映射后的 code（1-8）
  - `inventoryNum` = 资源数据"库存数量"列
  - `currentInventoryNum` = 0（克隆时不带运行时计数）
  - `lose` = 资源数据"是否未中奖奖品"列映射 boolean（"是" → true，"否" → false）
  - `probMap` = 严格包含 3 个 key：`{"10": 基础权重值, "50": 保底权重值, "9": 作弊权重值}`（来自资源数据三列）

#### Scenario: 库存类型枚举映射成功

- **WHEN** 资源数据"库存类型"列值能匹配 InventoryCycle 枚举（精确匹配 desc 或模糊匹配关键词）
- **THEN** 使用映射后的 code（1=DAILY, 2=HALF, 3=HOURLY, 4=ONCE, 5=NO_LIMIT, 6=THREE, 7=SIX, 8=MIN_10）

#### Scenario: 库存类型枚举映射失败

- **WHEN** 资源数据"库存类型"列值无法匹配任何 InventoryCycle 枚举
- **THEN** 跳过该奖品，记入兜底事件"奖品 <rewardBoxId> 库存类型 <值> 无法识别"

#### Scenario: 奖品在源奖池中找不到

- **WHEN** 资源数据中的"奖励包 ID"在源奖池的 awards 中找不到匹配
- **THEN** 仅用资源数据字段构造，其余字段用默认值，记入兜底事件"奖品 <rewardBoxId> 在源奖池中找不到，使用默认 awardName/worth/level 等字段"

### Requirement: 权重无 100% 校验

本 skill 必须把 sheet 中的基础权重 / 保底权重 / 作弊权重作为**数值**直接写入 probMap，不强制权重和 = 100%。

#### Scenario: 权重值合法

- **WHEN** sheet 中权重列值为非负整数
- **THEN** 直接作为数值写入 probMap

#### Scenario: 权重值非整数

- **WHEN** sheet 中权重列值不是非负整数（如负数 / 小数 / 非数字）
- **THEN** 跳过该奖品，记入兜底事件"奖品 <rewardBoxId> 权重 <字段> 非合法数值"

### Requirement: 奖池时间秒级对齐

本 skill 必须保证新奖池的 startTime / endTime 与新活动时间精确一致（毫秒级，含 15:00:00 / 23:59:59 设定）。

#### Scenario: 时间对齐校验

- **WHEN** 构造新 TenantConfigVO 时
- **THEN** basicInfo.startTime 必须等于主 skill 传入的新活动 startTime；basicInfo.endTime 必须等于新活动 endTime

#### Scenario: template-create 因时间不一致报错

- **WHEN** template-create 返回时间校验失败
- **THEN** 跳过该奖池，记入兜底事件"奖池 <remark> template-create 因时间校验失败"

### Requirement: 单奖池失败不阻断

本 skill 必须对每个奖池独立处理失败。

#### Scenario: 单奖池 tenant-query / template-create 失败

- **WHEN** 某奖池流程中任一步骤失败
- **THEN** 跳过该奖池，记入兜底事件，继续下一奖池

#### Scenario: tenant-list 失败 / 返回 0 条

- **WHEN** Step 1 调用 tenant-list 失败，或源 plan 下 0 个奖池
- **THEN** 向主 skill 返回失败 + 失败原因；不影响主 skill 调用后续 act-resource 子 skill

### Requirement: 多奖池场景处理

本 skill 必须支持源 plan 下含多个奖池的场景。

#### Scenario: 单奖池场景

- **WHEN** 源 plan 下仅 1 个奖池
- **THEN** 抽奖资源数据按单 sheet 解析；该 sheet 的全部奖品记录归属此奖池

#### Scenario: 多奖池场景 [待 design 阶段细化]

- **WHEN** 源 plan 下含多个奖池
- **THEN** 按抽奖资源数据中 sheet 名（约定 "抽奖-N" 形式）与源奖池**按顺序对齐**；如 design 阶段确认采用其他对齐策略（如按奖池名匹配），按 design 实施

### Requirement: 失败汇报格式

#### Scenario: 返回值结构

- **WHEN** 本 skill 执行完毕
- **THEN** 必须返回：
  - `success`: boolean（整体是否走完流程）
  - `tenantIdMapping` (M3): `Map<sourceTenantId, newTenantId>`
  - `tokenMapping` (M4): `Map<sourceToken, newToken>`
  - `interestIdMapping` (M5): `Map<sourceInterestId, newInterestId>`
  - `successCount`: int（成功创建的奖池数）
  - `events`: List<{level: "warn"|"error", path: "<计划名>→<奖池名>(→<奖品 rewardBoxId>)", reason: string}>
