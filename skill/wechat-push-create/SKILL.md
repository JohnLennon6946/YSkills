---
name: wechat-push-create
description: |
  微信 Push 计划创建执行 Skill。接收主入口 Skill（wechat-push）分发的创建指令，执行模板查询、参数组装、计划创建、结果通知。

  由 wechat-push 主入口调用，不直接由用户触发。
---

# wechat-push-create

Push 计划创建执行 Skill：接收经过意图识别和权限校验的创建指令，完成模板查询、参数组装、调用 secretary-create 创建计划、发送结果通知的完整流程。

## 前置条件

1. 由 wechat-push 主入口 Skill 分发调用
2. mws CLI 已安装且已认证
3. 有 moyi-activity-backend 的 secretary-page 和 secretary-create 接口权限

## 两种工作模式

### 模式 A：对话模式

由主入口传入 `mode="A"`、`type`（计划类型）、`crowdPacketUrl`（nosKey）。

### 模式 C：通用模式

由主入口传入 `mode="C"` 及用户指定的全部参数。

### 模式 B：定时任务模式

由 wechat-push-schedule 调用，传入 `mode="B"`、`type`、`crowdPacketUrl`。

## 模式 A 执行流程

### 步骤 1：获取 crowdPacketUrl

- 主入口传入 nosKey → 直接使用
- 主入口传入 txt 文件路径：
    1. 文件校验：检查存在性、.txt 格式、非空
    2. 上传至 NOS 公有桶获取 crowdPacketUrl：
       ```bash
       nos-cli upload <txt文件路径> --public
       ```
       从返回 JSON 中取 `nos_url` 作为 crowdPacketUrl
    3. 上传失败重试 3 次，均失败则提示用户直接提供 nosKey

### 步骤 2：查询历史最优模板

按指定类型调用 mws `secretary-page` 查询过去 30 天的历史记录：

```bash
START_MS=$(($(date +%s) * 1000 - 30 * 24 * 60 * 60 * 1000))
END_MS=$(($(date +%s) * 1000))

mws moyi-activity-backend secretary-page \
  --params "{\"page\":\"{\\\"from\\\":0,\\\"to\\\":1,\\\"size\\\":100}\",\"planName\":\"{类型关键词}\",\"start\":\"${START_MS}\",\"end\":\"${END_MS}\"}"
```

**分页参数说明**（PageRequest）：
- `from`：当前页码（从 0 开始）
- `to`：下一页页码（`from + 1`）
- `size`：每页条数

示例：查第一页 `{"from":0,"to":1,"size":100}`；翻下一页 `{"from":1,"to":2,"size":100}`

从返回结果中筛选：
1. 仅保留 `launchAccount` 为 `moyi_wechat_welfare` 的记录
2. 将每条记录的 `clickRate`（string）用 parseFloat 转为浮点数，解析失败视为 0
3. 按 `clickRate` 降序排序
4. 若最高 clickRate 有多条相同，取 `createTime` 最新的一条
5. 选取排序后的第一条作为模板

如果筛选后无记录，返回失败："过去30天无可用历史模板记录"。

### 步骤 3：参数组装

基于选中的模板记录组装 `secretary-create` 请求参数：

**planName 日期替换**：
```
正则匹配：/^\d{1,2}\.\d{1,2}/
替换为：当天日期的 M.DD 格式（如 5.18）
示例：5.14私聊 → 5.18私聊
兜底：正则不匹配时，使用 "{M.DD}{类型关键词}"（如 5.18签到）
```

**crowdPacketName 日期替换**：
```
同 planName 规则，对模板的 crowdPacketName 执行相同的日期前缀替换
示例：12.12高耗币未授权 → 5.18高耗币未授权
```

**planTime 计算**：
```
当天 20:00:00 UTC+8 的毫秒时间戳
```

**content 更新**：
```
1. JSON.parse(模板的 content 字段)
2. 如果 linkUrlExpire === true:
   将 linkUrlExpireTime 设置为 planTime + 7 * 24 * 60 * 60 * 1000
3. 如果 linkUrlExpire 为 false 或字段不存在，不修改
4. JSON.stringify 回字符串
```

**固定字段**：
- `planId`: `"0"`（新建）
- `launchApp`: 原样复制模板
- `launchAccount`: 原样复制模板
- `planType`: 原样复制模板
- `extInfo`: 原样复制模板

### 步骤 4：创建 Push 计划

```bash
mws moyi-activity-backend secretary-create \
  --json "{\"planId\":\"0\",\"planName\":\"{planName}\",\"planType\":{planType},\"content\":\"{content}\",\"crowdPacketUrl\":\"{crowdPacketUrl}\",\"crowdPacketName\":\"{crowdPacketName}\",\"planTime\":\"{planTime}\",\"launchApp\":\"{launchApp}\",\"launchAccount\":\"{launchAccount}\",\"extInfo\":\"{extInfo}\"}"
```

**planName 重复处理**：接口返回 planName 已存在时，追加后缀重试（`_2`、`_3`），最多 3 次。

### 步骤 5：发送结果通知

根据触发方式决定通知目标和渠道：

| 触发方式 | 群聊通知 | 私聊通知 |
|---------|---------|---------|
| 群聊 @机器人（模式 A/C） | @触发用户 | 私聊触发用户 |
| 私聊机器人（模式 A/C） | 不发群聊 | 私聊触发用户 |
| 模式 B（定时任务） | 不发（由 wechat-push-schedule 统一汇总） | 不发 |

**成功通知格式**：
```
@user 微信Push计划创建成功
- 计划ID：{planId}
- 计划名称：{planName}
- 发送时间：{planTime 格式化为 YYYY-MM-DD HH:mm}
- 生效时间：{planTime} ~ {planTime + 7天}
- 账号类型：{launchAccount}
```

**失败通知格式**：
```
@user 微信Push计划创建失败
- 计划类型：{type}
- 失败原因：{errorReason}
```

## 模式 B 执行流程

由 wechat-push-schedule 调用，传入 `mode="B"`、`type`、`crowdPacketUrl`。

执行步骤 2（查模板）→ 步骤 3（参数组装，crowdPacketUrl 使用传入值）→ 步骤 4（创建）。

不发送通知，仅返回结果给调用方（成功返回 planId/planName/planTime/launchAccount，失败返回 errorReason），由 wechat-push-schedule 统一汇总通知。

## 模式 C 执行流程

由主入口传入所有参数（用户已在主入口逐项补全）：

| 参数 | 说明 |
|------|------|
| planName | 计划名称 |
| planType | 推送类型（1=缩略图, 2=大图, 3=文本） |
| content | 推送文案 JSON 字符串 |
| crowdPacketUrl | 人群包文件链接 |
| crowdPacketName | 人群包名称 |
| launchApp | 投放应用 |
| launchAccount | 投放账号 |
| planTime | 执行时间（毫秒时间戳） |

直接调用 `secretary-create` 创建，按步骤 5 发送结果通知。

## 错误处理

| 错误场景 | 处理方式 |
|---------|---------|
| mws 未安装或未认证 | 返回错误信息 |
| secretary-page 接口失败 | 返回原始错误信息 |
| secretary-create 接口失败 | 返回原始错误信息 |
| clickRate 解析失败 | 视为 0，不阻塞选取逻辑 |
| planName 日期前缀不匹配 | 使用兜底名称 "{M.DD}{类型关键词}" |
| nosKey 格式异常 | 返回错误提示 |
| NOS 上传能力未就绪（P1） | 提示用户直接提供 nosKey |
