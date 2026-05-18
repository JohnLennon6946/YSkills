---
name: push-schedule
description: |
  微信 Push 计划定时任务调度。每天早上 10:00 按排期表决定当天需要创建的类型，逐类型串行调用 wechat-push-create。

  使用场景：
  - 龙虾平台 cron 定时任务每天 10:00 触发
  - 自动创建当天排期中的所有 push 计划

  本 Skill 由龙虾平台定时任务框架自动触发，不直接由用户对话触发。
---

# push-schedule

定时任务调度 Skill：每天早上 10:00 按排期表自动创建当天需要的微信 Push 计划。

## 前置条件

1. 龙虾平台定时任务能力已就绪（P1 阶段实现）
2. wechat-push-create Skill 已部署
3. push-result-notify Skill 已部署
4. config.json 中排期表和通知人已配置

## 排期表

默认排期（可通过 config.json 动态修改）：

| 星期 | 执行的类型 |
|------|-----------|
| 周一 (1) | 签到、高耗币 |
| 周二 (2) | 签到、私聊 |
| 周三 (3) | 签到、礼物过期 |
| 周四 (4) | 签到、家族签到 |
| 周五 (5) | 签到、礼物过期 |
| 周六 (6) | 签到、家族签到 |
| 周日 (0) | 签到、私聊 |

## 执行流程

### 步骤 1：读取排期配置

读取 `YSkills/skill/wechat-push-create/config.json` 中的 `schedule` 字段。

如果 config.json 读取失败，使用内置默认排期。

### 步骤 2：匹配今天的类型

获取当天星期几（0=周日, 1=周一, ..., 6=周六），在排期表中查找所有包含今天的类型。

如果没有匹配到任何类型，不执行任何操作，静默退出。

### 步骤 3：串行执行每种类型

对匹配到的类型列表，依次执行：

```
for each type in todayTypes:
  try:
    1. 调用 crowd-async-fetch 获取 crowdPacketUrl
       - 传入 type，等待 open-task-process 提交 + open-task-process-status 轮询完成
       - 获取到 dataUrl 作为 crowdPacketUrl
    2. 调用 wechat-push-create（mode="B", type=当前类型, crowdPacketUrl=获取到的URL）
    3. 记录结果：{ type, success: true, planId, planName, planTime, launchAccount }
  catch error:
    记录结果：{ type, success: false, errorReason: error.message }
    继续执行下一个类型（不中断）
```

### 步骤 4：汇总通知

所有类型执行完毕后：

1. 从 config.json 读取 `notifyUsers` 列表
2. 调用 push-result-notify Skill，传入：
   - results：所有类型的结果列表
   - targetUsers：notifyUsers
   - mode：`"B"`

## 错误处理

| 错误场景 | 处理方式 |
|---------|---------|
| config.json 读取失败 | 使用内置默认排期 |
| 某类型人群拉取超时 | 记录该类型失败，继续下一个 |
| 某类型无历史模板 | 记录该类型失败，继续下一个 |
| 某类型创建接口失败 | 记录该类型失败，继续下一个 |
| 所有类型均失败 | 汇总所有失败原因，通知管理员 |
| notifyUsers 为空 | 仅群聊通知，不发私聊 |
