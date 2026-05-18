---
name: wechat-push-schedule
description: |
  微信 Push 计划定时任务调度。每天早上 10:00 按排期表决定当天需要创建的类型，逐类型串行拉取人群包并调用 wechat-push-create 创建计划，最后汇总结果通知业务管理员。

  使用场景：
  - 龙虾平台 cron 定时任务每天 10:00 触发
  - 自动创建当天排期中的所有 push 计划

  本 Skill 由龙虾平台定时任务框架自动触发，不直接由用户对话触发。
---

# wechat-push-schedule

定时任务调度 Skill：每天早上 10:00 按排期表自动拉取人群包、创建微信 Push 计划，并汇总通知业务管理员。

## 前置条件

1. 龙虾平台定时任务能力已就绪
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

### 步骤 3：串行执行每种类型

对匹配到的类型列表，依次执行：

```
for each type in todayTypes:
  try:
    1. 调用人群拉取（见「人群包异步拉取」章节）获取 crowdPacketUrl
    2. 调用 wechat-push-create（mode="B", type=当前类型, crowdPacketUrl=获取到的URL）
    3. 记录结果：{ type, success: true, planId, planName, planTime, launchAccount }
  catch error:
    记录结果：{ type, success: false, errorReason: error.message }
    继续执行下一个类型（不中断）
```

### 步骤 4：汇总通知

所有类型执行完毕后，从 config.json 读取 `businessAdmins` 列表，发送汇总通知。

**群聊通知**（@业务管理员）：
```
@wangguojian @renpengtao 今日微信Push计划执行结果汇总

✅ 成功：
- 签到：计划ID 3679010，发送时间 2026-05-18 20:00
- 高耗币：计划ID 3679011，发送时间 2026-05-18 20:00

❌ 失败：
- 私聊：过去30天无可用历史模板记录
```

**私聊通知**（逐一发给每位业务管理员）：
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
```

如果 businessAdmins 为空，仅发群聊通知，不发私聊。

如果全部成功，不展示「❌ 失败」部分；如果全部失败，不展示「✅ 成功」部分。

## 人群包异步拉取

通过 moyi-activity-backend 的 OpenClaw 数据抓取任务接口获取人群包。

### 提交任务

```bash
mws moyi-activity-backend open-task-process --params "{\"type\":\"{类型标识}\"}"
```

- 输入：`type`（任务类型标识，对应排期中的计划类型）
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
2. 每 10 秒调用一次 `open-task-process-status` 查询
3. `status === "done"` 时，取 `dataUrl` 作为 crowdPacketUrl 返回
4. 超过 5 分钟（30 次轮询）仍未完成，判定为超时失败

## 错误处理

| 错误场景 | 处理方式 |
|---------|---------|
| config.json 读取失败 | 使用内置默认排期，businessAdmins 为空 |
| 某类型人群拉取超时（5分钟） | 记录该类型失败，继续下一个 |
| 某类型 open-task-process 调用失败 | 记录该类型失败，继续下一个 |
| 某类型无历史模板 | 记录该类型失败（由 wechat-push-create 返回），继续下一个 |
| 某类型创建接口失败 | 记录该类型失败（由 wechat-push-create 返回），继续下一个 |
| 所有类型均失败 | 汇总所有失败原因，仍然通知业务管理员 |
| businessAdmins 为空 | 仅群聊通知，不发私聊 |
