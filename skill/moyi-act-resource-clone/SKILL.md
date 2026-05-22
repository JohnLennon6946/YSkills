---
name: moyi-act-resource-clone
description: 心遇小程序活动模块克隆子 skill。接收源/新 wechat panel activityId + 映射表 M1-M5，拉取源 act-resource 列表，按 type=7 先 type=4 后顺序创建，对 type=4 configJson 做跨模块 patch + ruleText 日期替换，构建 M6 映射表。供 moyi-activity-create 主 skill 调用。
---

# moyi-act-resource-clone

克隆源 plan 的小程序活动模块（act-resource），按 type=7 → type=4 顺序创建，对抽奖转盘做跨模块字段 patch。

## 输入

主 skill 传入：
- `sourceActivityId`: 源 wechat panel activityId（被克隆的）
- `newActivityId`: 新 wechat panel activityId（来自新 plan 的 panel-list，克隆目标）
- `newSpinachActivityId`: 新 spinach panel activityId（用于 relatedActivityId patch）
- `startTime`: 新活动开始时间（毫秒时间戳）
- `endTime`: 新活动结束时间（毫秒时间戳）
- `M1`: panel activityId 映射表（源 → 新）
- `M2`: box id 映射表（源 → 新，来自 moyi-mission-clone）
- `M3`: tenantId 映射表（源 → 新，来自 moyi-lottery-clone）
- `M4`: token 映射表（源 → 新，来自 moyi-lottery-clone）
- `M5`: interestId 映射表（源 → 新，来自 moyi-lottery-clone）
- `env`: 环境（online / test）

## 工作流程

### Step 1: 拉取源 act-resource 列表

```bash
mws moyi-activity-backend act-resource-page --env <env> --params '{"trackId": "<sourceActivityId>", "page": {"from": 0, "to": 1, "size": 100}}' --format json
```

**注意**：page 必须同时包含 `from`、`to`、`size`，缺 `to` 会导致后端 500。

分页处理：若返回 `page.total` > 已拉取数，继续翻页（from += size）直到拉完所有源 act-resource。

若失败 → 返回整体失败，不继续。

### Step 2: 按 type 分组

- type=7（活动任务）：先处理
- type=4（抽奖转盘）：后处理
- 其他 type：跳过，记入兜底事件"act-resource <name> type=<X> 不在本期白名单（仅支持 4/7）"

### Step 3: 创建 type=7 资源（活动任务）

对每个 type=7 资源：

#### 3.1 构造 AddActResourceParamDTO

| 字段 | 取值 |
|------|------|
| `type` | 7 |
| `trackId` | 新 wechat panel activityId（入参 newActivityId） |
| `name` | 源 name 按日期规则替换 |
| `configJson` | 源 configJson 全部沿用 |

注意：AddActResourceParamDTO **无 status 字段**，新创建资源状态由后端决定。

#### 3.2 调用 act-resource-create

```bash
mws moyi-activity-backend act-resource-create --env <env> --body '<AddActResourceParamDTO JSON>' --format json
```

**注意**：act-resource-create 是 JSON body 接口（`application/json`），不能用 `--params` 传参。body 直接传 `{"type":7,"trackId":"<newActivityId>","name":"<name>","configJson":"<json>"}`。

返回值为 boolean（true/false），不返回新 ID。

#### 3.3 反查获取新 ID

创建成功后，调用 act-resource-page 按新 trackId 反查：

```bash
mws moyi-activity-backend act-resource-page --env <env> --params '{"trackId": "<newActivityId>", "page": {"from": 0, "to": 1, "size": 100}}' --format json
```

在返回列表中按 `name` 匹配 + 取 `createTime` 最新的一条，获取新 act-resource id，写入 M6。

若反查未命中 → 记入兜底事件"type=7 资源 <name> 创建成功但反查未找到新 ID，M6 映射缺失"。

若创建失败 → 跳过该资源，记入兜底事件，继续下一个。

### Step 4: 创建 type=4 资源（抽奖转盘）

**前置条件**：所有 type=7 已处理完毕，M6 映射表已构建。

对每个 type=4 资源：

#### 4.1 解析源 configJson

将源 act-resource 的 configJson 解析为 JSON 对象。若解析失败 → 跳过该资源，记入兜底事件。

#### 4.2 跨模块 patch（6 个字段）

| configJson 字段 | 映射来源 | 说明 |
|----------------|---------|------|
| `token` | M4（源 token → 新 token） | 奖池对外标识 |
| `relatedPoolId` | M3（源 tenantId → 新 tenantId） | 关联奖池 ID |
| `relatedTicketId` | M5（源 interestId → 新 interestId） | 资产币 ID |
| `relatedActivityId` | M1（源 spinach activityId → 新） | 关联 spinach panel |
| `taskPlayId` | M6（源 type=7 actResourceId → 新） | 关联活动任务资源 |
| `taskGroupId` | M2（源 box id → 新 box id） | 关联任务组 |

**映射规则**：
- 从 configJson 中取原始值作为 key，在对应映射表中查找新值
- 查找成功 → 替换为新值
- 查找失败 → 跳过该资源，记入兜底事件"抽奖转盘 <name> 因 <字段名> 映射缺失未创建"

#### 4.3 ruleText 日期文案替换

对 configJson 中的 `ruleText` 字段进行日期文案自动替换：

**支持的日期格式**（7 种，与主 skill 一致）：
- `M月d号HH:MM:SS-M月d号HH:MM:SS`（如 `5月19号15:00:00-5月24号23:59:59`）
- `M月d日-M月d日`（如 `5月19日-5月24日`）
- `M月d号-M月d号`（如 `5月19号-5月24号`）
- `M.d-M.d`（如 `5.19-5.24`）
- `M/d-M/d`（如 `5/19-5/24`）
- `MMdd-MMdd`（如 `0519-0524`）
- `yyyy.M.d-M.d` / `yyyy/M/d-M/d`（跨年格式）

**替换规则**：
- 识别到 → 用新活动日期替换（保持原格式；时间部分：开始 15:00:00，结束 23:59:59）
- 未识别到 → 保留原文，记入兜底事件"抽奖转盘 <name> ruleText 中未识别到日期文案，请运营手工核对"

**注意**：仅替换日期文案，不修改 ruleText 中的金额、规则等非日期内容。

#### 4.4 其他 configJson 字段

除上述 6 个 patch 字段 + ruleText 外，configJson 中所有其他字段（`relatedPageId` / `ifHasTask` / 30+ 图片 URL / 颜色 / `pageBgColor` 等）全部沿用源值。

#### 4.5 构造并调用 act-resource-create

| 字段 | 取值 |
|------|------|
| `type` | 4 |
| `trackId` | 新 wechat panel activityId（入参 newActivityId） |
| `name` | 源 name 按日期规则替换 |
| `configJson` | patch 后的 JSON 字符串 |

```bash
mws moyi-activity-backend act-resource-create --env <env> --body '<AddActResourceParamDTO JSON>' --format json
```

**注意**：同 Step 3.2，必须走 JSON body 模式。**act-resource-create 不支持 update**（带 `id` 字段会报"参数非法"），仅用于新建。如需更新已有资源，使用 `/api/social/backend/act/resource/update`（当前 MWS 未注册此方法，需 curl 直连或后台操作）。

若失败 → 跳过该资源，记入兜底事件，继续下一个。

### Step 5: 日期 token 识别与替换规则（用于 name）

与 moyi-lottery-clone 使用同一套规则：
- 识别到 → 用新日期替换原 token，保持 token 格式
- 未识别到 → 在源名称末尾追加 ` <新开始M.d>-<新结束M.d>`

## 返回格式

```json
{
  "skill": "moyi-act-resource-clone",
  "success": true,
  "taskPlayIdMapping": {"12345": "12400", "12346": "12401"},
  "successCount": 4,
  "events": [
    {"level": "warn", "path": "iOS复购6.1-6.10 → 抽奖转盘", "reason": "ruleText 中未识别到日期文案，请运营手工核对"}
  ]
}
```

**字段说明**：
- `success`: boolean — 整体是否走完流程（act-resource-page 成功即 true，即使部分资源创建失败）
- `taskPlayIdMapping` (M6): 源 type=7 act-resource id → 新 act-resource id 映射
- `successCount`: 成功创建的 act-resource 总数（type=7 + type=4）
- `events`: 兜底事件列表，level 为 "warn" 或 "error"
