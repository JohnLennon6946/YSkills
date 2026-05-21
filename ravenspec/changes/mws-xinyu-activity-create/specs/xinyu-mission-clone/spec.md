# xinyu-mission-clone 能力规范

> 心遇任务模块克隆 — 子 skill

## ADDED Requirements

### Requirement: 任务模块克隆主流程

本 skill 必须接收源 mission panel activityId + 新活动信息（新 missionName / startTime / endTime / business） + 任务资源数据（来自 xinyu-resource-sheet-parser），调用 mws 完成 mundo + box + mission 树整体克隆，并按任务名称反查替换 rewardBoxId。

#### Scenario: 标准克隆流程

- **WHEN** 主 skill 调用本 skill 并传入合法的源 activityId + 新 mission panel activityId（来自新 plan 的 panel-list）+ 新 plan 信息 + 任务资源数据
- **THEN** 必须依次执行：
  1. 调用 `POST /api/social/mission/backend/mundo/query`（mws: `mundo-query`），入参 activityId = **源** mission panel activityId，拉取源 mundo 树（用于 M2 对齐）
  2. 调用 `POST /api/social/mission/backend/copy/mundo`（mws: `moyi-activity-backend copy-mundo`），入参 MissionBackendCopyReq：`aimActivityId` = 源 mission panel activityId（被克隆的源），`activityId` = 新 mission panel activityId（克隆目标），`missionName` = 新名（按日期规则生成），`startTime/endTime` = 新活动时间，`business` = "moyi"
  3. 调用 `mundo-query`，入参 activityId = **新** mission panel activityId，拉取新 mundo 树
  4. 按 Step 1 源 missionBoxes 与 Step 3 新 missionBoxes 的**顺序索引对齐**构建映射表 M2（源 box id → 新 box id）；若数量不一致则按 missionBoxName 匹配兜底
  5. 遍历新 mission，按 `missionName` 在任务资源数据中精确反查
  6. 对需要替换 rewardBoxId 的 mission 调用 `POST /api/social/mission/backend/info/save`（mws: `info-save`），入参 MissionDTO（仅修改 rewardBoxId）
  7. 输出：映射表 M2 + 成功替换计数 + 兜底事件列表

#### Scenario: copy-mundo 报错

- **WHEN** Step 2 调用 copy-mundo 失败
- **THEN** 跳过任务模块，向主 skill 返回失败 + 失败原因；不影响主 skill 调用后续 lottery / act-resource 子 skill

#### Scenario: 源 mundo-query 报错

- **WHEN** Step 1 调用源 mundo-query 失败
- **THEN** 跳过任务模块（无法构建 M2），向主 skill 返回失败

#### Scenario: 新 mundo-query 报错

- **WHEN** Step 3 调用新 mundo-query 失败
- **THEN** 跳过 rewardBoxId 替换；新 mundo 已创建，记入兜底事件"rewardBoxId 替换未执行，请运营手工核对"；M2 使用 Step 1 源 box 列表与新 panel box 列表（可能为空）

### Requirement: rewardBoxId 反查替换规则

本 skill 必须按"任务名称"作为唯一匹配键反查资源数据中的 rewardBoxId。

#### Scenario: 资源数据匹配成功且 rewardBoxId 非空

- **WHEN** 新 mission 的 missionName 在资源数据中能精确匹配到一条记录，且该记录的 rewardBoxId 非空
- **THEN** 用该 rewardBoxId 覆盖 mission 字段后调用 info-save

#### Scenario: 资源数据匹配成功但 rewardBoxId 为空

- **WHEN** 资源数据中匹配到一条记录但 rewardBoxId 字段为空
- **THEN** 保留源 mission 的原 rewardBoxId，不调用 info-save，无需记入兜底事件

#### Scenario: 资源数据无匹配

- **WHEN** 新 mission 的 missionName 在资源数据中找不到对应记录
- **THEN** 保留源 mission 的原 rewardBoxId，不调用 info-save，记入兜底事件"sheet 中无任务名 <missionName> 的记录"

#### Scenario: 资源数据存在同名重复

- **WHEN** 资源数据中存在多条 missionName 相同的记录
- **THEN** 使用首条记录的 rewardBoxId，记入兜底事件"sheet 中任务名 <missionName> 存在 N 条重复记录，已采用首条"

### Requirement: 单条 mission 失败不阻断

本 skill 必须对每个 mission 的 info-save 独立处理失败。

#### Scenario: 某个 mission info-save 失败

- **WHEN** 遍历到某个 mission 调用 info-save 报错
- **THEN** 跳过该 mission，记入兜底事件"mission <missionName> 的 rewardBoxId 替换失败：<错误原因>"，继续下一个 mission

### Requirement: 字段沿用规则

本 skill 必须遵循 PRD 决策：除 missionName / startTime / endTime / activityId / rewardBoxId 之外，所有字段（含 33+ 个 mission 字段、box 字段、ext 字段）由 copyMundo 后端自动按源复制，本 skill 不再覆盖。

#### Scenario: tenantId 字段不映射

- **WHEN** 源 mission 有非空 tenantId（关联抽奖机）
- **THEN** 新 mission 的 tenantId 保持源值（本期决策：不做"源奖池 token → 新奖池 token"映射）

### Requirement: 失败汇报格式

本 skill 必须按结构化格式向主 skill 上报结果。

#### Scenario: 返回值结构

- **WHEN** 本 skill 执行完毕
- **THEN** 必须返回：
  - `success`: boolean（整体是否走完流程）
  - `newMissionActivityId`: long（新 mission panel activityId，失败时为 0）
  - `boxIdMapping` (M2): `Map<sourceBoxId, newBoxId>`
  - `successCount`: int（成功替换 rewardBoxId 的 mission 数）
  - `events`: List<{level: "warn"|"error", path: "<计划名>→<主任务名>→<任务组名>→<子任务名>", reason: string}>
