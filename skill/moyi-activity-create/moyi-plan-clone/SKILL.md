---
name: xinyu-plan-clone
description: 心遇活动发布计划克隆主编排 skill。通过 POPO 对话收集运营意图，调用子 skill 完成模板克隆（plan-create + 任务/抽奖/小程序活动模块复制），维护 M1-M6 映射表，汇总兜底事件通知运营。
---

# xinyu-plan-clone

心遇活动发布计划克隆的主编排 skill，通过 POPO 机器人对话引导运营完成活动模板克隆全流程。

## 触发条件

运营在 POPO 群 @机器人 或私聊中发送含"创建新活动发布计划"意图的消息（LLM 自由意图识别，非严格关键词匹配）。

## 前置条件

- bot 服务已正确配置公共账号 token（mws 公共账号鉴权）
- mws CLI 可用且已配置 moyi-activity-backend 服务

## 整体流程

```
意图识别 → 模式选择（模板克隆/全新）→ 模板检索 → 活动时间收集
→ plan-create + M1 构建 → 资源表格收集 → 子模块编排 → 兜底汇总
```

## 详细步骤

### Step 1: 意图识别与模式选择

1. LLM 识别运营消息是否为"创建新活动发布计划"意图
2. 追问运营选择：
   - **模板克隆** → 进入 Step 2
   - **全新发布计划** → 回复"全新发布计划能力建设中，敬请期待"，终止会话
3. 回复无法识别 → 再追问 1 次；仍无法识别则终止

### Step 2: 模板发布计划检索

1. 提示运营输入计划名称关键词
2. 调用 plan-list 模糊匹配：

```bash
mws moyi-activity-backend plan-list --env <env> --params '{"name": "<关键词>"}' --format json
```

3. 展示候选列表：
   - ≤20 条 → 全量展示（编号 + 计划名称 + 开始时间 + 结束时间）
   - >20 条 → 展示最近 20 条 + 提示"还有 N 条未展示，请输入更精确的关键词"
   - 0 条 → "未找到匹配计划，请重新输入关键词"（允许重试最多 3 次）
4. 运营输入编号选定源 plan
   - 无效编号 → "编号无效，请重新选择"（允许重试最多 3 次）

### Step 3: 活动时间收集

1. 提示运营输入新活动日期范围（如"6.1-6.10"）
2. 解析日期：
   - 成功 → 开始时间 = 开始日期 **15:00:00** (Asia/Shanghai)，结束时间 = 结束日期 **23:59:59** (Asia/Shanghai)
   - 格式无法解析 → "日期格式无法识别，请按 `M.d-M.d` 格式输入"
   - 结束日期 ≤ 开始日期 → "结束日期必须晚于开始日期，请重新输入"
3. 转为毫秒时间戳供后续使用

### Step 4: 创建新 plan + 构建映射表 M1

#### 4.1 查询源 plan 的 panel 列表

```bash
mws moyi-activity-backend panel-list --env <env> --params '{"planId": "<sourcePlanId>"}' --format json
```

记录源 panel 列表（每个 panel 含 type + activityId）。

#### 4.2 生成新 plan 名称

日期 token 识别规则（7 种格式）：
- `M.d-M.d`（如 `5.19-5.24`）
- `M/d-M/d`（如 `5/19-5/24`）
- `MMdd-MMdd`（如 `0519-0524`）
- `M月d号HH:MM:SS-M月d号HH:MM:SS`
- `M月d日-M月d日`
- `M月d号-M月d号`
- `yyyy.M.d-M.d` / `yyyy/M/d-M/d`（跨年格式）

识别到 → 用新日期替换原 token，保持 token 格式。
未识别到 → 在源名称末尾追加 ` <新开始M.d>-<新结束M.d>`。

#### 4.3 调用 plan-create

```bash
mws moyi-activity-backend plan-create --env <env> --params '{"name": "<新plan名>", "startTime": <毫秒>, "endTime": <毫秒>, "modules": [<沿用源modules>], "domain": "<沿用源>", "noticeCorps": [<沿用源>]}' --format json
```

**异常处理**：
- allowCreatePlanGapMinutes 校验失败 → 原样反馈给运营，提示重新选日期
- 其他错误 → 终止流程，原样反馈错误

#### 4.4 查询新 plan 的 panel 列表

```bash
mws moyi-activity-backend panel-list --env <env> --params '{"planId": "<newPlanId>"}' --format json
```

#### 4.5 构建映射表 M1

按 panel type 对齐源 panel 和新 panel：
- M1: `{源panel.activityId → 新panel.activityId}`（按 type 匹配）

M1 中关键条目：
- mission panel: 源 mission activityId → 新 mission activityId
- spinach panel: 源 spinach activityId → 新 spinach activityId
- wechat panel: 源 wechat activityId → 新 wechat activityId

### Step 5: 资源配置表格收集

根据新 plan 的 modules 决定：
- 含 mission 或 spinach → 提示运营发送 POPO 在线表格链接
- 仅含 wechat → 跳过此步

收到链接后调用 `xinyu-resource-sheet-parser`：
- 传入 `sheetUrl` + `modules`（需要解析的模块列表）
- 获取 `missionEntries` + `lotteryEntries`

若解析失败重试最多 3 次，仍失败则记入兜底事件，后续模块走"全部按源沿用"路径。

### Step 6: 子模块编排（严格顺序）

按 **任务 → 抽奖 → 小程序活动** 顺序依次调用子 skill。

#### 6.1 任务模块 — xinyu-mission-clone

**前置**：plan 含 mission 模块

传入参数：
- `sourceActivityId`: M1 中源 mission panel activityId
- `newActivityId`: M1 中新 mission panel activityId
- `missionName`: 新 plan 名称（用于 mundo 的 missionName）
- `startTime`: 新活动 startTime（毫秒）
- `endTime`: 新活动 endTime（毫秒）
- `missionEntries`: Step 5 获取的任务资源数据
- `env`: 当前环境

产出：M2（源 box id → 新 box id）

#### 6.2 抽奖模块 — xinyu-lottery-clone

**前置**：plan 含 spinach 模块

传入参数：
- `sourceActivityId`: M1 中源 spinach panel activityId
- `newActivityId`: M1 中新 spinach panel activityId
- `startTime`: 新活动 startTime（毫秒）
- `endTime`: 新活动 endTime（毫秒）
- `lotteryEntries`: Step 5 获取的抽奖资源数据
- `env`: 当前环境

产出：M3（源 tenantId → 新 tenantId）、M4（源 token → 新 token）、M5（源 interestId → 新 interestId）

#### 6.3 小程序活动模块 — xinyu-act-resource-clone

**前置**：plan 含 wechat 模块

传入参数：
- `sourceActivityId`: M1 中源 wechat panel activityId
- `newActivityId`: M1 中新 wechat panel activityId
- `newSpinachActivityId`: M1 中新 spinach panel activityId（用于 relatedActivityId patch）
- `startTime`: 新活动 startTime（毫秒）
- `endTime`: 新活动 endTime（毫秒）
- `M1` / `M2` / `M3` / `M4` / `M5`: 前序子 skill 产出的映射表
- `env`: 当前环境

产出：M6（源 type=7 act-resource id → 新 act-resource id）

#### 6.4 子模块失败处理

- 某子 skill 返回 success=false → 记入兜底事件，**不阻断**后续子模块
- 部分模块缺失 → 跳过，缺失模块的映射表留空
- 依赖空映射表的下游模块 → 走"保留源值 + 记入兜底事件"分支

### Step 7: 兜底事件汇总通知

所有子模块执行完毕后，统一发送一条 POPO 消息：

**全部成功时**：
```
✅ 活动计划克隆完成
新计划：<新plan名>（ID: <planId>）
- 主任务：N 条成功
- 奖池：M 个成功
- 小程序资源：K 个成功
```

**存在兜底事件时**：
```
⚠️ 活动计划克隆完成（部分需手工处理）
新计划：<新plan名>（ID: <planId>）

成功项：
- 主任务：N/总数 条成功
- 奖池：M/总数 个成功
- 小程序资源：K/总数 个成功

需手工处理：
[任务模块]
- <path>: <reason>
[抽奖模块]
- <path>: <reason>
[小程序活动模块]
- <path>: <reason>

请前往 mws 后台手动补充失败项。
```

若消息超过 3000 字符，拆分为多条按顺序发送。

### Step 8: 会话管理

#### 中途取消

运营在任意交互节点回复"取消"或同义表达：
- plan 未创建 → 直接终止
- plan 已创建 → 提示"新 plan 已创建（id=X，name=Y），请前往 mws 后台手动清理"，不调删除接口

#### 会话超时

- 运营在某一步超过 **10 分钟**无响应 → 上下文回收，需重新触发
- 单运营并发限制：已有进行中会话时，提示"你有进行中的会话（在第 N 步），请先完成或回复取消"

#### 环境选择

- 默认 `--env online`
- 运营明确说"测试环境"/"test 环境" → `--env test`

## 本期 modules 白名单

仅处理 **mission / spinach / wechat** 三类模块的内部内容复制。其他模块类型（rank/shop/hourLottery 等）在 plan-create 时照常传入 modules 保证结构一致，但**不复制其内部数据**，记入兜底事件"模块 <type> 不在本期白名单，请运营手工配置"。

## 映射表汇总

| 映射表 | 含义 | 来源 |
|-------|------|------|
| M1 | 源 panel activityId → 新 panel activityId | Step 4（plan-create 后 panel-list 对齐） |
| M2 | 源 mission box id → 新 box id | xinyu-mission-clone |
| M3 | 源 tenantId → 新 tenantId | xinyu-lottery-clone |
| M4 | 源 token → 新 token | xinyu-lottery-clone |
| M5 | 源 interestId → 新 interestId | xinyu-lottery-clone |
| M6 | 源 type=7 act-resource id → 新 id | xinyu-act-resource-clone |

## 注意事项

- `mission.tenantId` 本期不做源奖池→新奖池映射（保持源值）
- 所有日期 token 识别使用同一套 7 种格式正则，与子 skill 保持一致
- plan-create 的 domain / noticeCorps 沿用源（周期性活动几乎不变）
- 奖池时间与活动时间秒级一致（15:00:00 ~ 23:59:59）
