---
name: moyi-mission-clone
description: 心遇任务模块克隆子 skill。接收源/新 mission panel activityId + 任务资源数据，调用 copy-mundo 克隆 mundo 树，反查替换 rewardBoxId，构建 M2 映射表。供 moyi-activity-create 主 skill 调用。
---

# moyi-mission-clone

克隆源 plan 的任务模块（mundo + box + mission 树），并按资源表格替换 rewardBoxId。

## 输入

主 skill 传入：
- `sourceActivityId`: 源 mission panel activityId（被克隆的）
- `newActivityId`: 新 mission panel activityId（来自新 plan 的 panel-list，克隆目标）
- `missionName`: 新活动的任务名称（按日期规则生成）
- `startTime`: 新活动开始时间（毫秒时间戳）
- `endTime`: 新活动结束时间（毫秒时间戳）
- `missionEntries`: 任务资源数据（来自 moyi-resource-sheet-parser）
- `env`: 环境（online / test）

## 工作流程

### Step 1: 查询源 mundo 树

```bash
mws moyi-activity-backend mundo-query --env <env> --params '{"activityId": "<sourceActivityId>"}' --format json
```

记录源 missionBoxes 列表（用于 M2 对齐）。

若失败 → 返回整体失败，不继续。

### Step 2: 调用 copy-mundo

```bash
mws moyi-activity-backend copy-mundo --env <env> --params '{"activityId": "<sourceActivityId>", "aimActivityId": "<newActivityId>", "missionName": "<missionName>", "startTime": "<startTime>", "endTime": "<endTime>"}' --format json
```

**关键参数说明**：
- `activityId` = 源活动 ID（被克隆的，有 mundo 数据，后端从这里读取）
- `aimActivityId` = 新活动 ID（克隆目标，后端会自动在这里创建 mundo 骨架并写入数据）
- 注意：`activityId` 在前、`aimActivityId` 在后，与命名直觉相反

若失败 → 返回整体失败 + 错误原因。

### Step 3: 查询新 mundo 树

```bash
mws moyi-activity-backend mundo-query --env <env> --params '{"activityId": "<newActivityId>"}' --format json
```

记录新 missionBoxes 列表。

若失败 → 记入兜底事件"rewardBoxId 替换未执行，请运营手工核对"，M2 构建降级。

### Step 4: 构建映射表 M2

按 Step 1 源 missionBoxes 与 Step 3 新 missionBoxes 的**顺序索引对齐**：
- 源 missionBoxes[0].id → 新 missionBoxes[0].id
- 源 missionBoxes[1].id → 新 missionBoxes[1].id
- ...

若数量不一致（某个 box 复制失败），降级为按 `missionBoxName` 匹配：
- 遍历源 box，在新 box 列表中找 missionBoxName 相同的记录
- 找不到的 box 跳过，记入兜底事件

### Step 5: 遍历新 mission 替换 rewardBoxId

遍历 Step 3 返回的所有 box → 所有 mission：

1. 取 `mission.missionName`，在 `missionEntries` 中精确匹配
2. 匹配规则：
   - **匹配成功 + rewardBoxId 非空** → 用该 rewardBoxId 调用 info-save 覆盖
   - **匹配成功 + rewardBoxId 为空** → 保留源值，不调 info-save，无需记入兜底
   - **无匹配** → 保留源值，不调 info-save，记入兜底事件"sheet 中无任务名 <missionName> 的记录"
   - **同名重复** → 使用首条记录的 rewardBoxId，记入兜底事件

3. 调用 info-save 替换 rewardBoxId：

```bash
mws moyi-activity-backend info-save --env <env> --params '{"param": "<MissionDTO JSON>"}' --format json
```

MissionDTO 传入完整的 mission 对象（从 mundo-query 返回值取出），仅修改 `rewardBoxId` 字段。

4. 单条 mission info-save 失败 → 跳过，记入兜底事件，继续下一条。

### Step 6: 字段沿用规则

除 `rewardBoxId` 外，所有字段（33+ 个 mission 字段、box 字段、ext 字段）由 copy-mundo 后端自动按源复制，本 skill 不再覆盖。

特别说明：`mission.tenantId` 保持源值，本期不做源奖池→新奖池映射。

## 返回格式

```json
{
  "skill": "moyi-mission-clone",
  "success": true,
  "boxIdMapping": {"9679761": "9679800", "9679762": "9679801"},
  "successCount": 3,
  "events": [
    {"level": "warn", "path": "iOS复购6.1-6.10 → 主任务A → 任务组1 → 签到", "reason": "sheet 中无任务名 签到 的记录"}
  ]
}
```

**字段说明**：
- `success`: boolean — 整体是否走完流程（copy-mundo 成功即 true，即使部分 rewardBoxId 替换失败）
- `boxIdMapping` (M2): 源 box id → 新 box id 映射
- `successCount`: 成功替换 rewardBoxId 的 mission 数
- `events`: 兜底事件列表，level 为 "warn" 或 "error"
