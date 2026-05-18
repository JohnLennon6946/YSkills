---
name: crowd-async-fetch
description: |
  异步拉取特定任务类型的今日人群包。通过 mws 调用 open-task-process 提交任务，轮询 open-task-process-status 获取结果，返回 dataUrl 作为 crowdPacketUrl。

  使用场景：
  - push-schedule 定时任务中，自动获取每种类型的人群包
  - 需要从后端异步拉取人群包数据

  本 Skill 由 push-schedule 内部调用。

  触发词：拉取人群包、获取人群包
---

# crowd-async-fetch

异步拉取特定任务类型的今日人群包。通过 moyi-activity-backend 的 `open-task-process` 提交抓取任务，轮询 `open-task-process-status` 直到完成，返回 `dataUrl` 作为 crowdPacketUrl。

## 前置条件

1. mws CLI 已安装且已认证（`mws auth status` 正常）
2. 有 moyi-activity-backend 的 open-task-process 和 open-task-process-status 接口权限

## 输入参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| type | string | 是 | 计划类型标识：签到/高耗币/礼物过期/家族签到/私聊 |

## 执行流程

### 步骤 1：提交拉取任务

```bash
mws moyi-activity-backend open-task-process --params '{"type": "{type}"}'
```

从响应中获取 `processId`（格式为 `{prefix}_{timestamp}`）。

**响应示例**：
```json
{
  "processId": "crowd_1716019200000"
}
```

### 步骤 2：轮询任务状态

每 10 秒调用一次状态查询接口：

```bash
mws moyi-activity-backend open-task-process-status --params '{"processId": "{processId}"}'
```

**响应字段**：
| 字段 | 类型 | 说明 |
|------|------|------|
| status | string | `process` = 处理中，`done` = 已完成 |
| rate | integer | 处理进度百分比（0~100） |
| dataUrl | string | 数据文件下载地址，仅 status=done 时返回 |
| totalNum | integer | 数据总量，仅 status=done 时返回 |
| sampleList | string[] | 样例数据，仅 status=done 时返回 |

**轮询逻辑**：
- `status` 为 `"process"`：等待 10 秒后再次查询
- `status` 为 `"done"`：提取 `dataUrl` 作为 crowdPacketUrl，返回成功
- 累计轮询超过 5 分钟（30 次）：停止轮询，返回超时错误
- 单次查询网络失败：不中断，继续下一次轮询

### 步骤 3：返回结果

- 成功：返回 `dataUrl` 字符串（即 crowdPacketUrl）
- 失败：返回结构化错误信息

**成功返回示例**：
```json
{
  "success": true,
  "crowdPacketUrl": "https://nos.netease.com/jdmosi-common/obj/.../crowd_20260518.txt",
  "totalNum": 52300
}
```

**失败返回示例**：
```json
{
  "success": false,
  "errorReason": "任务超时（5分钟内未完成）"
}
```

## 错误处理

| 错误场景 | 处理方式 |
|---------|---------|
| 任务提交失败（接口报错） | 返回原始错误信息 |
| 任务超时（5 分钟） | 停止轮询，返回 "任务超时（5分钟内未完成）" |
| 单次轮询网络失败 | 跳过本次，继续下一轮（连续 3 次失败则停止） |
| processId 为空 | 返回 "任务提交异常，未获取到 processId" |
| dataUrl 为空（status=done 但无 URL） | 返回 "任务完成但未返回数据地址" |
