# xinyu-act-resource-clone 能力规范

> 心遇小程序活动模块克隆 — 子 skill

## ADDED Requirements

### Requirement: 小程序活动模块克隆主流程

本 skill 必须接收源 wechat panel activityId + 新 plan 信息 + 全部映射表（M1: 源 panel activityId → 新；M2: 源 box id → 新；M3/M4/M5: 源奖池 id/token/interestId → 新），完成源 plan 下所有 act-resource 的复制，严格按 type=7 → type=4 顺序。

#### Scenario: 标准克隆流程

- **WHEN** 主 skill 调用本 skill 并传入合法的源 wechat panel activityId + 新 plan 信息 + 全部映射表
- **THEN** 必须依次执行：
  1. 调用 `POST /api/social/backend/act/resource/page`（mws: `act-resource-page`），入参 `trackId` = 源 wechat panel activityId，分页拉取**所有**源 act-resource（首次 from=0, size=100；若 page.total > 已拉取数则继续翻页直到全部拉完）
  2. 按 type 分组，先处理 type=7（活动任务），再处理 type=4（抽奖转盘），其他 type 跳过
  3. 对每个 type=7 资源：构造 AddActResourceParamDTO 调用 `act-resource-create`，创建成功后反查 `act-resource-page`（按新 trackId + name）获取新 ID 写入 M6
  4. 对每个 type=4 资源：构造 AddActResourceParamDTO，对 configJson 做跨模块 patch + ruleText 日期替换，调用 act-resource-create
  5. 输出：M6 映射表 + 成功项统计 + 兜底事件列表

#### Scenario: act-resource-page 失败

- **WHEN** Step 1 调用 act-resource-page 失败
- **THEN** 向主 skill 返回失败 + 失败原因；本 skill 不再继续

#### Scenario: 子玩法不在白名单

- **WHEN** 源 act-resource 的 type 不在 {4, 7} 内
- **THEN** 跳过该资源，记入兜底事件"act-resource <name> type=<X> 不在本期白名单（仅支持 4/7）"

### Requirement: 严格顺序保证

本 skill 必须确保 type=7（活动任务）在 type=4（抽奖转盘）之前全部创建完毕。

#### Scenario: 顺序依赖

- **WHEN** 源 act-resource 列表同时含 type=7 和 type=4
- **THEN** 必须先完成所有 type=7 创建并构建完整 M6 映射表，再开始 type=4 创建

#### Scenario: 仅含 type=4

- **WHEN** 源列表仅含 type=4（无 type=7）
- **THEN** M6 映射表为空；type=4 配置中若依赖 taskPlayId / taskGroupId，按"映射缺失"分支处理（保留源值 + 记入兜底事件）

### Requirement: 活动任务 (type=7) 字段构造

本 skill 必须按以下规则构造 type=7 资源。

#### Scenario: 单个 type=7 资源构造

- **WHEN** 处理一条源 type=7 act-resource
- **THEN** 构造 AddActResourceParamDTO：
  - `type` = 7
  - `trackId` = M1 中"源 wechat panel activityId → 新 wechat panel activityId"
  - `name` = 源 name 按日期规则替换（识别日期 token 则替换；未识别则末尾追加 `M.d-M.d`）
  - `configJson` = 源 configJson 字段全部沿用（含样式 / 颜色 / rewardBoxId / ifSendReward 等）
  - 注意：AddActResourceParamDTO **无 status 字段**，新创建资源状态由后端决定（默认下线），后续由运营在后台手动上线
  - 创建成功后（返回 true），调用 `act-resource-page` 按 `trackId` = 新 wechat panel activityId + `name` = 新名称反查，获取新 act-resource id，写入 M6（源 act-resource id → 新 act-resource id）
  - 若反查未命中，记入兜底事件"type=7 资源 <name> 创建成功但反查未找到新 ID，M6 映射缺失"

### Requirement: 抽奖转盘 (type=4) 字段构造与 configJson patch

本 skill 必须按以下规则构造 type=4 资源，对 configJson 中 6 个跨模块引用字段做映射 patch。

#### Scenario: 单个 type=4 资源构造

- **WHEN** 处理一条源 type=4 act-resource
- **THEN** 构造 AddActResourceParamDTO：
  - `type` = 4
  - `trackId` = M1 中"源 wechat panel activityId → 新"
  - `name` = 源 name 按日期规则替换
  - `configJson` = 源 configJson 解析后做以下 patch（其余字段沿用）：
    - `token` = M4 映射后的新奖池 token
    - `relatedPoolId` = M3 映射后的新奖池 id（字符串化）
    - `relatedTicketId` = M5 映射后的新奖池 interestId（字符串化）
    - `relatedActivityId` = M1 映射后的新 spinach panel activityId（字符串化）
    - `poolCount` = 对应新奖池的奖品行数（来自 xinyu-lottery-clone 产出的奖品总数）
    - `taskPlayId` = M6 映射后的新活动任务 act-resource id（字符串化）
    - `taskGroupId` = M2 映射后的新 box id（字符串化）
    - `ruleText` = 源 ruleText 经日期文案自动识别替换（详见后续 Requirement）
    - 其他字段（`relatedPageId` / `ifHasTask` / 30+ 图片 URL / 颜色 / `pageBgColor` 等）沿用源
  - 注意：AddActResourceParamDTO **无 status 字段**，新创建资源状态由后端决定，后续由运营在后台手动上线

#### Scenario: 跨模块映射缺失

- **WHEN** 上述 6 个 patch 字段中任一映射 key 在对应映射表中找不到（如源 token 不在 M4 中）
- **THEN** 跳过该资源，记入兜底事件"抽奖转盘 <name> 因 <字段名> 映射缺失未创建"

#### Scenario: configJson 不是合法 JSON

- **WHEN** 源 act-resource 的 configJson 无法解析为合法 JSON
- **THEN** 跳过该资源，记入兜底事件"抽奖转盘 <name> configJson 解析失败"

### Requirement: ruleText 日期文案自动替换

本 skill 必须自动识别 ruleText 中的日期文案并按新活动日期替换。

#### Scenario: 识别并替换日期

- **WHEN** 源 ruleText 含"M月d号HH:MM:SS-M月d号HH:MM:SS"或同类格式的日期范围（与 plan 名称的日期 token 识别规则同一套）
- **THEN** 用新活动日期替换原日期文案（新开始日期 15:00:00 / 新结束日期 23:59:59），保持原格式与原文其余内容不变

#### Scenario: 未识别到日期文案

- **WHEN** 源 ruleText 无可识别的日期格式
- **THEN** 保留源 ruleText 原样，记入兜底事件"抽奖转盘 <name> ruleText 中未识别到日期文案，请运营手工核对"

### Requirement: act-resource 命名规则

本 skill 必须沿用源 act-resource 的 name 并按日期规则替换。

#### Scenario: 源 name 含日期 token

- **WHEN** 源 act-resource name 中能识别到日期 token（与 plan 名同一套规则）
- **THEN** 用新日期替换原日期 token

#### Scenario: 源 name 无日期 token

- **WHEN** 源 act-resource name 中无可识别日期 token
- **THEN** 在源 name 末尾追加 `M.d-M.d`（与 plan 名规则一致）

### Requirement: 单资源失败不阻断

本 skill 必须对每个 act-resource 独立处理失败。

#### Scenario: act-resource-create 失败

- **WHEN** 某资源的 act-resource-create 调用报错
- **THEN** 跳过该资源，记入兜底事件，继续下一资源

### Requirement: 失败汇报格式

#### Scenario: 返回值结构

- **WHEN** 本 skill 执行完毕
- **THEN** 必须返回：
  - `success`: boolean（整体是否走完流程）
  - `taskPlayIdMapping` (M6): `Map<sourceActResourceId, newActResourceId>` （仅 type=7）
  - `successCount`: int（成功创建的 act-resource 总数）
  - `events`: List<{level: "warn"|"error", path: "<计划名>→<资源名>", reason: string}>
