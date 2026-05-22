---
name: moyi-lottery-clone
description: 心遇抽奖模块克隆子 skill。接收源/新 spinach panel activityId + 抽奖资源数据，拉取源奖池列表并逐个复制（构造新 TenantConfigVO + template-create），构建 M3/M4/M5 映射表。供 moyi-activity-create 主 skill 调用。
---

# moyi-lottery-clone

克隆源 plan 的抽奖模块（奖池 + 奖品配置），按资源表格设置 interestId / 奖品 / 权重。

## 输入

主 skill 传入：
- `sourceActivityId`: 源 spinach panel activityId（被克隆的）
- `newActivityId`: 新 spinach panel activityId（来自新 plan 的 panel-list，克隆目标）
- `startTime`: 新活动开始时间（毫秒时间戳）
- `endTime`: 新活动结束时间（毫秒时间戳）
- `lotteryEntries`: 抽奖资源数据（来自 moyi-resource-sheet-parser，按 sheet 顺序排列）
- `env`: 环境（online / test）

## 工作流程

### Step 1: 拉取源奖池列表

```bash
mws moyi-activity-backend tenant-list --env <env> --params '{"activityId": "<sourceActivityId>", "appProductNames": "moyi", "page": {"from": 0, "to": 1, "size": 100}}' --format json
```

**注意**：page 必须同时包含 `from`、`to`、`size` 三个字段，缺 `to` 会导致后端 500。

分页处理：若返回 `page.total` > 已拉取数，继续翻页（from += size）直到拉完所有源奖池。

若失败或返回 0 条 → 返回整体失败，不继续。

### Step 2: 查询每个源奖池详情

对 Step 1 中每个奖池，调用：

```bash
mws moyi-activity-backend tenant-query --env <env> --params '{"tenantId": "<tenantId>"}' --format json
```

获取完整 TenantConfigVO（含 basicInfo / tenantExtInfo / awards / template 等）。

若某奖池 tenant-query 失败 → 跳过该奖池，记入兜底事件，继续下一个。

### Step 3: 源奖池与 lotteryEntries 对齐

按**顺序索引对齐**：
- 源奖池列表[0] 对应 lotteryEntries[0]
- 源奖池列表[1] 对应 lotteryEntries[1]
- ...

若数量不一致（源奖池数 ≠ lotteryEntries 数），记入兜底事件"源奖池数 N 与 sheet 奖池数 M 不一致，按较小值对齐"。

### Step 4: 构造新 TenantConfigVO

对每个对齐的（源奖池, lotteryEntry）对，按以下规则构造新 TenantConfigVO：

#### 4.1 basicInfo

| 字段 | 取值 |
|------|------|
| `remark` | 源 remark 中日期 token 替换为新日期；无日期 token 则末尾追加 ` M.d-M.d` |
| `startTime` | 新活动 startTime（毫秒） |
| `endTime` | 新活动 endTime（毫秒） |
| `activityId` | 新 spinach panel activityId（入参 newActivityId） |
| `token` | 0（让后端生成） |
| `status` | 沿用源 |
| 其他字段 | 沿用源 |

#### 4.2 tenantExtInfo

| 字段 | 取值 |
|------|------|
| `interestId` | lotteryEntry.interestId（资源 sheet 提供的资产币 ID） |
| `interestEnableStatus` | 沿用源 |
| `ticketPrice` / `price` / `floorAwardRate` | 沿用源 |
| `periodType` / `personalMiniGuaranteeCount` / `allMiniGuaranteeCount` / `compensateWithDeduct` | 沿用源 |
| `gifts` / `probTypeInfos` / `sceneCodes` / `adminUsers` / `labelId` / `financeMsg` | 沿用源（多为 null） |

#### 4.3 awards（奖品列表）

遍历 lotteryEntry.awards，对每条奖品记录构造一个 AwardConfigVO：

| 字段 | 取值 |
|------|------|
| `awardId` | 0（让后端 auto-increment） |
| `rewardBoxId` | 资源数据的 rewardBoxId |
| `probMap` | `{"10": baseWeight, "50": floorWeight, "9": cheatWeight}`（资源数据三列） |
| `inventoryType` | 资源数据 inventoryType（已由 sheet-parser 映射为 code 1-8） |
| `inventoryNum` | 资源数据 inventoryNum |
| `currentInventoryNum` | 0（克隆时不带运行时计数） |
| `lose` | 资源数据 isLose（boolean） |
| `awardName` / `level` / `worth` / `needPush` / `needAnnounce` / `sortIndex` | 按 rewardBoxId 匹配源 award 取源值；找不到则用默认值 |
| `wildtimeFactors` / `awardType` / `nosKey` / `amount` / `ext` | 按 rewardBoxId 匹配源 award 取源值；找不到则为 null/0 |

**奖品匹配规则**：
- 按 `rewardBoxId` 在源奖池 awards 中查找匹配
- 匹配成功 → 沿用源的 awardName / worth / level / needPush / needAnnounce / sortIndex 等辅助字段
- 匹配失败 → 辅助字段用默认值（awardName=""、worth=0、level=""、needPush=false、needAnnounce=false、sortIndex=0），记入兜底事件

**inventoryType 映射失败处理**：
- 若 sheet-parser 返回的 inventoryType 不是 1-8 的数字 → 跳过该奖品，记入兜底事件

**权重值校验**：
- baseWeight / floorWeight / cheatWeight 必须为非负整数
- 若不合法 → 跳过该奖品，记入兜底事件

#### 4.4 其他顶层字段

| 字段 | 取值 |
|------|------|
| `template` | 沿用源（如 "inventoryNormal"） |
| `appProductName` | "moyi" |
| `tenantPushImConfig` | 沿用源 |
| `tenantAnnounceConfig` | 沿用源 |
| `tenantWildConfigVO` | 沿用源 |
| `extensibleConfigVO` | 沿用源 |
| `levels` | 沿用源 |

### Step 5: 调用 template-create

```bash
mws moyi-activity-backend template-create --env <env> --params '{"config": "<新 TenantConfigVO JSON 字符串>"}' --format json
```

**注意**：config JSON 较大时（含多奖品、中文文案等），query string 可能超出 URL 长度限制（`Invalid request path`），此时需精简 config 内容（去除 null 字段、缩短文案等）。

**返回值处理**：template-create 返回的 `basicInfo.token` 固定为入参值（"0"），**不是后端实际生成的 token**。提取规则：
- 新 tenantId = response.tenantId
- 新 token = **见 Step 5.1**（template-create 不返回真实 token）
- 新 interestId = response.tenantExtInfo.interestId

若失败 → 跳过该奖池，记入兜底事件，继续下一个。

### Step 5.1: 二次查询获取真实 token

template-create 返回后，立即调用 tenant-query 获取后端异步生成的真实 token：

```bash
mws moyi-activity-backend tenant-query --env <env> --params '{"tenantId": "<新 tenantId>"}' --format json
```

从返回值 `basicInfo.token` 中取真实 token（如 `30V1048MaU9g2vl9iP2gv3kae`），用于 M4 映射。

⚠️ 若跳过此步，M4 会记录错误 token（"0"），导致下游小程序活动的 relatedPoolId token 关联失败。

### Step 6: 构建映射表 M3 / M4 / M5

逐奖池累积：
- **M3**（源 tenantId → 新 tenantId）：`{源奖池.tenantId: Step5返回.tenantId}`
- **M4**（源 token → 新 token）：`{源奖池.basicInfo.token: Step5返回.basicInfo.token}`
- **M5**（源 interestId → 新 interestId）：`{源奖池.tenantExtInfo.interestId: Step5返回.tenantExtInfo.interestId}`

### Step 7: 日期 token 识别与替换规则（用于 remark）

支持 7 种日期格式识别：
- `M.d-M.d`（如 `5.19-5.24`）
- `M/d-M/d`（如 `5/19-5/24`）
- `MMdd-MMdd`（如 `0519-0524`）
- `M月d号HH:MM:SS-M月d号HH:MM:SS`（如 `5月19号15:00:00-5月24号23:59:59`）
- `M月d日-M月d日`（如 `5月19日-5月24日`）
- `M月d号-M月d号`（如 `5月19号-5月24号`）
- `yyyy.M.d-M.d` / `yyyy/M/d-M/d`（跨年格式）

识别到 → 用新日期替换原 token，保持 token 格式。
未识别到 → 在源名称末尾追加 ` <新开始M.d>-<新结束M.d>`。

## 返回格式

```json
{
  "skill": "moyi-lottery-clone",
  "success": true,
  "tenantIdMapping": {"601111": "601200", "601112": "601201"},
  "tokenMapping": {"abc123": "def456", "ghi789": "jkl012"},
  "interestIdMapping": {"2003754": "2003754"},
  "successCount": 2,
  "events": [
    {"level": "warn", "path": "iOS复购6.1-6.10 → 奖池1 → 奖品8440099", "reason": "在源奖池中找不到，使用默认辅助字段"}
  ]
}
```

**字段说明**：
- `success`: boolean — 整体是否走完流程（tenant-list 成功即 true，即使部分奖池创建失败）
- `tenantIdMapping` (M3): 源 tenantId → 新 tenantId 映射
- `tokenMapping` (M4): 源 token → 新 token 映射
- `interestIdMapping` (M5): 源 interestId → 新 interestId 映射
- `successCount`: 成功创建的奖池数
- `events`: 兜底事件列表，level 为 "warn" 或 "error"
