---
name: push-result-notify
description: |
  发送微信 Push 计划创建结果通知。支持群聊 @人员和私聊发送。

  使用场景：
  - wechat-push-create 创建计划完成后调用，发送结果通知
  - push-schedule 批量创建完成后调用，发送汇总通知

  本 Skill 由其他 Skill 内部调用，不直接由用户触发。
---

# push-result-notify

将微信 Push 计划创建结果通过群聊 @人员和私聊发送给指定人。

## 输入参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| results | Array | 是 | 创建结果列表，每项包含 type、success、planId、planName、planTime、launchAccount、errorReason |
| targetUsers | Array | 是 | 通知目标用户列表（邮箱格式） |
| mode | string | 是 | 工作模式：A、B 或 C |
| channel | string | 否 | 触发渠道：`group`（群聊@机器人）或 `private`（私聊机器人），默认 group |

## 通知路由规则

| 触发方式 | targetUsers 来源 | 群聊通知 | 私聊通知 |
|---------|-----------------|---------|---------|
| 模式 B（定时任务） | config.json 的 businessAdmins | @业务管理员 | 私聊业务管理员 |
| 模式 A/C（群聊 @机器人） | 触发该对话的用户 | @该用户 | 私聊该用户 |
| 模式 A/C（私聊机器人） | 触发该对话的用户 | 不发群聊 | 私聊该用户 |

## 通知格式

### 单条创建成功

```
@user1 微信Push计划创建成功
- 计划ID：{planId}
- 计划名称：{planName}
- 发送时间：{planTime 格式化为 YYYY-MM-DD HH:mm}
- 生效时间：{planTime 格式化} ~ {planTime + 7天 格式化}
- 账号类型：{launchAccount}
```

### 单条创建失败

```
@user1 微信Push计划创建失败
- 计划类型：{type}
- 失败原因：{errorReason}
```

### 批量结果（模式 B）

将多个类型的结果合并为一条通知消息，每个类型一段，格式同上。

## 执行步骤

1. **格式化通知内容**

   遍历 `results` 数组，对每条结果：
   - 如果 `success` 为 true：按「创建成功」格式生成，将 `planTime`（毫秒时间戳）格式化为 `YYYY-MM-DD HH:mm`（UTC+8），计算生效结束时间 = planTime + 7天
   - 如果 `success` 为 false：按「创建失败」格式生成

   模式 B（批量）时，将所有结果拼接为一条消息。

2. **群聊 @通知**

   - 如果 `channel` 为 `group`：在当前群聊中发送通知消息，@targetUsers 中的所有用户
   - 如果 `channel` 为 `private`：跳过群聊通知

3. **私聊发送**

   对 targetUsers 中的每个用户，通过私聊发送完整的创建结果。

   - 如果 targetUsers 为空：跳过私聊
   - 如果私聊发送失败：记录日志，不阻塞主流程，不重试

## 错误处理

| 错误场景 | 处理方式 |
|---------|---------|
| targetUsers 为空 | 仅群聊通知，跳过私聊 |
| 私聊发送失败 | 记录日志，继续处理下一个用户 |
| 群聊发送失败 | 记录日志，仍尝试私聊发送 |
| results 为空 | 不发送任何通知 |
