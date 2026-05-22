---
name: wechat-push-schedule
description: |
  微信 Push 计划定时任务调度。每天早上 10:00 按排期表决定当天需要创建的类型，先并行提交所有人群包拉取任务，再各自轮询获取 crowdPacketUrl，满足条件的类型按序调用 wechat-push-create，最后汇总通知业务管理员。

  支持模式 B（全自动）和模式 D（半自动，带人群包确认）。

  使用场景：
  - 模式 B：龙虾平台 cron 定时任务每天 10:00 触发，全自动执行
  - 模式 D：用户手动触发（如"执行今天的微信push任务"），类似模式 B 的全自动主流程，但增加人群包确认步骤，让用户 double-check 后再继续
---

# wechat-push-schedule

定时任务调度 Skill：每天早上 10:00 按排期表自动拉取人群包、创建微信 Push 计划，并汇总通知业务管理员。支持模式 B（全自动）和模式 D（半自动，带人群包确认）。

## 两种工作模式

### 模式 B（定时任务模式）

由 cron 定时触发，全自动执行，无需人工干预。

### 模式 D（半自动任务模式）

由用户手动触发（如"执行今天的微信push任务"），从主入口传入 `mode: "D"` 和当天匹配的 `todayTypes` 列表。主流程与模式 B 相同，但**增加人群包确认步骤**。

**模式 D 人群包确认流程**：
1. 并行提交人群包任务并轮询等待就绪
2. 人群包全部就绪后，立即移除轮询 cron，输出人群包下载地址给用户
3. 等待用户回复「确认」后，再继续创建计划
4. 用户回复「取消」则终止流程
5. 创建计划时，必须逐步骤输出中间结果：模板选取理由（clickRate/planName）、参数变更（日期替换、linkUrlExpireTime 计算）、创建结果（成功/重试）

**人群包确认输出格式**：
```
人群包已生成，可点击下方链接下载检查：
- 签到：{downloadUrl}（{totalNum}人）
- 家族签到：{downloadUrl}（{totalNum}人）

确认人群无误后发送「确认」继续创建推送计划。
```

**参数差异**：
| 步骤 | 模式 B | 模式 D |
|------|--------|--------|
| 触发方式 | cron 定时 | 用户手动 |
| 人群包就绪后 | 直接创建计划 | 等待用户确认 |
| 创建计划 | 调用 wechat-push-create（mode="B"） | 调用 wechat-push-create（mode="B"） |
| 通知 | 自动通知业务管理员 | 用户确认后通知业务管理员 |
| 适用场景 | 每天定时自动执行 | 用户主动执行，需要人工检查人群包 |

## 前置条件

1. 龙虾平台定时任务能力已就绪（模式 B）
2. wechat-push-create Skill 已部署
3. mws CLI 已安装且已认证
4. `wechat-push-create/config.json` 中排期表和业务管理员已配置

## 执行流程

### 步骤 1：读取排期配置

读取 `YSkills/skill/wechat-push-create/config.json`：

```json
{
  "business": "moyi-wechat-push",
  "businessAdmins": ["wangguojian@corp.netease.com", "renpengtao@corp.netease.com"],
  "schedule": {
    "签到": [0, 1, 2, 3, 4, 5, 6],
    "高耗币": [1],
    "礼物过期": [3, 5],
    "家族签到": [4, 6],
    "私聊": [2, 0]
  }
}
```

如果 config.json 读取失败，使用内置默认排期：
- 签到=[0,1,2,3,4,5,6]，高耗币=[1]，礼物过期=[3,5]，家族签到=[4,6]，私聊=[2,0]

### 步骤 2：匹配今天的类型

获取当天星期几（0=周日, 1=周一, ..., 6=周六），在排期表中查找所有包含今天的类型。

如果没有匹配到任何类型，不执行任何操作，静默退出。

### 步骤 3：并行提交 + 独立轮询

1. **并行提交人群包任务**：对 `todayTypes` 中的每个类型，同时调用 `open-task-process`，收集所有 `processId`
2. **独立轮询**：为每个 `processId` 单独启动轮询，互不影响
3. **逐个创建计划**（模式 B）/ **人群包确认**（模式 D）：
   - **模式 B**：每种类型的 crowdPacketUrl 到位后，依次调用 `wechat-push-create`（mode="B"）创建计划
   - **模式 D**：人群包全部就绪后，输出下载地址等待用户确认，确认后再创建计划

```
// 并行提交
processIds = {}
for each type in todayTypes:
  try:
    processIds[type] = 调用 open-task-process 提交任务
  catch error:
    记录该类型失败，不参与轮询

// 独立轮询（各自独立执行，互不阻塞）
for each type, processId in processIds:
  轮询 open-task-process-status 直到 status == "done" 或超时 3 小时
  若成功：得到 crowdPacketUrl，标记为待创建
  若超时：记录失败

// 所有人群包就绪后立即移除轮询 cron，避免空转
立即移除当前轮询 cron

// 模式 B：按序创建（确保顺序可控）
results = []
for each type in todayTypes（原始顺序）:
  if 该类型 crowdPacketUrl 已就绪:
    try:
      result = 调用 wechat-push-create（mode="B", type, crowdPacketUrl）
      results.append({ type, success: true, ... })
    catch error:
      results.append({ type, success: false, errorReason: ... })
  else:
    results.append({ type, success: false, errorReason: "人群包未就绪或超时" })

// 模式 D：等待用户确认
crowdPackets = {}
for each type in todayTypes:
  if crowdPacketUrl 已就绪:
    crowdPackets[type] = { url, totalNum }

// 所有人群包就绪后立即移除轮询 cron，避免空转抢占主会话资源
立即移除当前轮询 cron
输出人群包确认消息给用户
等待用户回复「确认」

if 用户确认:
  按序创建计划（同模式 B）
  发送汇总通知
else:
  终止流程，返回「已取消」
```

**设计说明**：人群包拉取是典型的 I/O 等待场景，并行提交可显著缩短总耗时（尤其是签到 + 家族签到这类高频组合日），靠各自独立轮询获取结果后再串行创建计划。

### 步骤 4：汇总通知（模式 B 必须执行，模式 D 用户确认后执行）

⚠️ 模式 B 定时任务完成后，**必须通知业务管理员**，不可跳过。

模式 D 在用户确认人群包后，创建计划完毕再发送汇总通知。

所有类型执行完毕后，从 config.json 读取 `businessAdmins` 列表，发送汇总通知。

**通知工具选择**：
- 群聊 @通知：使用 `popo-group-cli` 技能的 `send` 命令，指定 `atUserIds` 为 businessAdmins 列表
- 私聊通知：使用 `message` 工具 `action=send`，`channel=popo`，逐一发给每位业务管理员

**群聊通知**（在群内 @所有业务管理员，使用 `popo-group-cli send`）：
```
@wangguojian @renpengtao @yusiyu01 今日微信Push计划执行结果汇总

✅ 成功：
- 签到：计划ID 3679010，发送时间 2026-05-18 20:00
- 高耗币：计划ID 3679011，发送时间 2026-05-18 20:00

❌ 失败：
- 私聊：过去30天无可用历史模板记录

⚠️ 请运营及时审核Push计划，确保正常发送。
```

**私聊通知**（使用 `message action=send channel=popo` 逐一发给每位业务管理员）：
```
今日微信Push计划执行结果汇总

✅ 成功（2/3）：
- 签到
  - 计划ID：3679010
  - 计划名称：5.18签到
  - 发送时间：2026-05-18 20:00
  - 生效时间：2026-05-18 20:00 ~ 2026-05-25 20:00
  - 账号类型：moyi_wechat_welfare

- 高耗币
  - 计划ID：3679011
  - 计划名称：5.18高耗币
  - 发送时间：2026-05-18 20:00
  - 生效时间：2026-05-18 20:00 ~ 2026-05-25 20:00
  - 账号类型：moyi_wechat_welfare

❌ 失败（1/3）：
- 私聊
  - 失败原因：过去30天无可用历史模板记录

⚠️ 请运营及时审核Push计划，确保正常发送。
```

**注意事项**：
- 群聊通知和私聊通知都必须发送，不可遗漏
- 如果 businessAdmins 为空，仅发群聊通知，不发私聊
- 如果全部成功，不展示「❌ 失败」部分；如果全部失败，不展示「✅ 成功」部分
- 通知发送失败不影响任务本身，但需记录日志

## 人群包异步拉取

通过 moyi-activity-backend 的 OpenClaw 数据抓取任务接口获取人群包。

### 类型映射

调用 `open-task-process` 时，需将排期中的中文类型名映射为接口 `type` 参数值：

| 任务类型 | type 参数值 |
|---------|------------|
| 签到 | `sign` |
| 高耗币 | `highCoin` |
| 礼物过期 | `giftExpire` |
| 家族签到 | `familySIgn` |
| 私聊 | `chat` |

### 提交任务

```bash
mws moyi-activity-backend open-task-process --params "{\"type\":\"{type参数值}\"}"
```

- 输入：`type`（接口类型参数值，通过上方映射表将中文类型名转换得到）
- 输出：`processId`（格式 `{prefix}_{timestamp}`，用于后续查询）

### 轮询状态

```bash
mws moyi-activity-backend open-task-process-status --params "{\"processId\":\"{processId}\"}"
```

- 输出字段：
  - `status`：`"process"` 进行中 / `"done"` 完成
  - `rate`：进度百分比（0-100）
  - `dataUrl`：完成后的下载地址（即 crowdPacketUrl）
  - `totalNum`：数据总量

### 轮询策略

1. 提交任务获取 processId
2. 每 1 分钟调用一次 `open-task-process-status` 查询
3. `status === "done"` 时，取 `dataUrl` 作为 crowdPacketUrl 返回
4. 超过 3 小时（180 次轮询）仍未完成，判定为超时失败

## 错误处理

| 错误场景 | 处理方式 |
|---------|---------|
| config.json 读取失败 | 使用内置默认排期，businessAdmins 为空 |
| 某类型人群拉取超时（3小时） | 记录该类型失败，继续下一个 |
| 某类型 open-task-process 调用失败 | 记录该类型失败，继续下一个 |
| 某类型无历史模板 | 记录该类型失败（由 wechat-push-create 返回），继续下一个 |
| 某类型创建接口失败 | 记录该类型失败（由 wechat-push-create 返回），继续下一个 |
| 所有类型均失败 | 汇总所有失败原因，仍然通知业务管理员 |
| businessAdmins 为空 | 仅群聊通知，不发私聊 |
| 模式 D 用户取消确认 | 终止流程，通知用户「已取消」|
