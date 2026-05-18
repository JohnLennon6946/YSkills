---
name: wechat-push-create
description: |
  创建微信 Push 计划。基于历史最优模板克隆并替换人群包/时间/名称，通过 mws 调用 moyi-activity-backend 接口完成创建。

  使用场景：
  - 用户说"创建签到push"、"新增高耗币推送计划"等意图
  - 用户提供 txt 文件或 nosKey 并指定计划类型
  - 用户说"创建一个微信push计划，我来指定参数"
  - 定时任务 push-schedule 按排期自动触发
  - 用户发送配置管理指令（设置通知人、修改排期等）

  触发词：创建push、新增push、创建推送计划、微信push、设置通知人、添加通知人、移除通知人、查看通知人、查看排期、修改排期、新增场景、删除场景
---

# wechat-push-create

主编排 Skill：通过 mws 调用 moyi-activity-backend 接口，基于历史推送记录模板自动创建微信 Push 计划。

## 前置条件

1. mws CLI 已安装且已认证（`mws auth status` 正常）
2. 有 moyi-activity-backend 的 secretary-page 和 secretary-create 接口权限
3. `config.json` 位于本 Skill 同目录下

## 五种计划类型

| 类型 | planName 关键词 | 说明 |
|------|----------------|------|
| 签到 | `签到` | 每日签到提醒 |
| 高耗币 | `高耗币` | 高耗币用户召回 |
| 礼物过期 | `礼物过期` | 礼物过期提醒 |
| 家族签到 | `家族签到` | 家族签到提醒 |
| 私聊 | `私聊` | 私聊推送 |

## 三种工作模式

### 模式 A：对话模式

用户在对话中提供 nosKey（或 txt 文件）+ 指定五种类型之一。

**判断条件**：用户提供了 nosKey 或 txt 文件，且指定了五种预设类型之一。

### 模式 B：定时任务模式

由 push-schedule Skill 自动触发，传入类型和 crowdPacketUrl。

**判断条件**：调用来源为 push-schedule，参数中包含 `mode: "B"` 和 `type`。

### 模式 C：通用模式

用户手动指定所有参数，创建任意类型的 push 计划。

**判断条件**：用户明确要求手动指定所有参数，或创建非预设类型的 push。

## 意图识别

收到用户消息后，按以下优先级判断意图：

1. **配置管理指令**：消息包含"设置通知人"、"添加通知人"、"移除通知人"、"查看通知人"、"查看排期"、"修改排期"、"新增场景"、"删除场景" → 执行配置管理流程
2. **模式 A**：消息中包含 nosKey（形如 `jdmosi-common/obj/...`）或 txt 文件附件，且提到五种类型之一 → 模式 A
3. **模式 C**：消息中要求手动指定参数或创建非预设类型 → 模式 C
4. **模式 B**：由 push-schedule 内部调用，传入 `mode: "B"` → 模式 B

模式 A 中类型不明确时，主动追问用户："请问要创建哪种类型的 push 计划？（签到/高耗币/礼物过期/家族签到/私聊）"

模式 C 中缺少必填参数时，逐项追问用户补全。

## 模式 A/B 执行流程

### 步骤 1：查询历史最优模板

按指定类型调用 mws `secretary-page` 查询过去 30 天的历史记录：

```bash
# 计算时间范围（当前时间戳 - 30天）
START_MS=$(($(date +%s) * 1000 - 30 * 24 * 60 * 60 * 1000))
END_MS=$(($(date +%s) * 1000))

mws moyi-activity-backend secretary-page \
  --params "{\"page\":\"{\\\"from\\\":0,\\\"size\\\":100}\",\"planName\":\"{类型关键词}\",\"start\":\"${START_MS}\",\"end\":\"${END_MS}\"}"
```

从返回结果中筛选：
1. 仅保留 `launchAccount` 为 `moyi_wechat_welfare` 的记录
2. 将每条记录的 `clickRate`（string）用 parseFloat 转为浮点数，解析失败视为 0
3. 按 `clickRate` 降序排序
4. 若最高 clickRate 有多条相同，取 `createTime` 最新的一条
5. 选取排序后的第一条作为模板

如果筛选后无记录，报告失败："过去30天无可用历史模板记录"。

### 步骤 2：参数组装

基于选中的模板记录组装 `secretary-create` 请求参数：

**planName 日期替换**：
```
正则匹配：/^\d{1,2}\.\d{1,2}/
替换为：当天日期的 M.DD 格式（如 5.17）
示例：5.14私聊 → 5.17私聊
兜底：正则不匹配时，使用 "{M.DD}{类型关键词}"（如 5.17签到）
```

**crowdPacketName 日期替换**：
```
同 planName 规则，对模板的 crowdPacketName 执行相同的日期前缀替换
示例：12.12高耗币未授权 → 5.17高耗币未授权
```

**planTime 计算**：
```
当天 20:00:00 UTC+8 的毫秒时间戳
JavaScript: new Date('YYYY-MM-DD 20:00:00+08:00').getTime()
Shell: date -d "$(date +%Y-%m-%d) 20:00:00" +%s 再乘以 1000（macOS 用 date -j -f）
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

**crowdPacketUrl**：
- 模式 A：使用用户提供的 nosKey 或上传后获取的 nosKey
- 模式 B：使用 push-schedule 传入的 crowdPacketUrl

### 步骤 3：创建 Push 计划

调用 mws `secretary-create`：

```bash
mws moyi-activity-backend secretary-create \
  --json "{\"planId\":\"0\",\"planName\":\"{组装后的planName}\",\"planType\":{planType},\"content\":\"{转义后的content JSON字符串}\",\"crowdPacketUrl\":\"{crowdPacketUrl}\",\"crowdPacketName\":\"{组装后的crowdPacketName}\",\"planTime\":\"{planTime毫秒时间戳}\",\"launchApp\":\"{launchApp}\",\"launchAccount\":\"{launchAccount}\",\"extInfo\":\"{extInfo}\"}"
```

**planName 重复处理**：如果接口返回 planName 已存在的错误，自动追加后缀重试：
- 第 1 次重试：`{planName}_2`
- 第 2 次重试：`{planName}_3`
- 最多重试 3 次

### 步骤 4：发送结果通知

调用 push-result-notify Skill 发送创建结果。

- 模式 A/C：targetUsers 为对话发起用户
- 模式 B：targetUsers 为 config.json 中的 notifyUsers

## 模式 C 执行流程

1. 向用户逐项收集以下必填参数：

   | 参数 | 说明 | 示例 |
   |------|------|------|
   | planName | 计划名称 | 5.17测试推送 |
   | planType | 推送类型（1=缩略图, 2=大图, 3=文本） | 2 |
   | content | 推送文案 JSON 字符串 | {"text":"..."} |
   | crowdPacketUrl | 人群包文件链接 | jdmosi-common/obj/.../xxx.txt |
   | crowdPacketName | 人群包名称 | 5.17测试人群 |
   | launchApp | 投放应用 | moyi |
   | launchAccount | 投放账号 | moyi_wechat_welfare |
   | planTime | 执行时间（毫秒时间戳，或 YYYY-MM-DD HH:mm 格式自动转换） | 2026-05-17 20:00 |

2. 所有参数收集完成后，调用 `secretary-create` 创建
3. 调用 push-result-notify 发送结果给对话用户

## 配置管理

配置文件路径：`YSkills/skill/wechat-push-create/config.json`

### 权限模型（两级管理员）

**系统管理员**：
- 来源：POPO 机器人后台的子管理员列表（平台自动同步，不存储在 config.json）
- 权限：全部操作（配置业务管理员、管理所有类型的排期、新增/删除场景、一切配置变更）

**业务管理员**：
- 来源：由系统管理员通过对话指令配置，存储在 config.json 的 `businessAdmins` 字段
- 权限：管理本业务的排期（修改排期、新增/删除场景）
- 当前业务：moyi-wechat-push，初始业务管理员：wangguojian@corp.netease.com、renpengtao@corp.netease.com

**权限校验流程**：
1. 从 POPO 消息获取发送者身份（邮箱）
2. 查询 POPO 机器人后台子管理员列表 → 若命中，视为系统管理员，放行所有操作
3. 若非系统管理员，查找 config.json 的 `businessAdmins` → 若命中，放行业务管理操作
4. 均未命中 → 拒绝：
   ```
   抱歉，您没有该操作的权限。请联系系统管理员分配权限。
   ```

查看类指令（查看排期、查看业务管理员）不限制权限，任何人均可查看。

### 通知路由规则

| 触发方式 | 通知目标 | 说明 |
|---------|---------|------|
| 模式 B（定时任务） | 群聊 @业务管理员 + 私聊业务管理员 | 定时任务结果只通知业务管理员 |
| 模式 A（用户在群聊 @机器人） | 群聊 @该用户 + 私聊该用户 | 谁触发的回复谁 |
| 模式 A（用户私聊机器人） | 私聊回复该用户 | 谁触发的回复谁 |
| 模式 C（用户在群聊 @机器人） | 群聊 @该用户 + 私聊该用户 | 谁触发的回复谁 |
| 模式 C（用户私聊机器人） | 私聊回复该用户 | 谁触发的回复谁 |

### 指令处理

| 指令 | 操作 | 权限要求 |
|------|------|----------|
| `修改排期 高耗币 周一周三` | 更新指定类型的执行日 | 系统管理员 或 业务管理员 |
| `新增场景 拉新` | 追问执行周期，写入 schedule 新类型 | 系统管理员 或 业务管理员 |
| `删除场景 拉新` | 从 schedule 中移除该类型 | 系统管理员 或 业务管理员 |
| `查看排期` | 读取并展示排期表（类型 + 对应星期） | 所有人 |
| `设置业务管理员 user1 user2` | 覆盖写入 businessAdmins | 系统管理员 |
| `添加业务管理员 user3` | 追加到 businessAdmins（去重） | 系统管理员 |
| `移除业务管理员 user1` | 从 businessAdmins 删除 | 系统管理员 |
| `查看业务管理员` | 展示当前业务管理员列表 | 所有人 |

星期解析规则：周日=0, 周一=1, 周二=2, 周三=3, 周四=4, 周五=5, 周六=6。支持"每天"作为 [0,1,2,3,4,5,6] 的快捷方式。

### 新增场景交互流程

当系统管理员或业务管理员说"新增场景 {类型名}" 或 "新增一种类型 {类型名}" 时：

1. **确认类型名称**：从指令中提取类型名称（如"拉新"）
2. **追问执行周期**：
   ```
   请问「拉新」类型的执行周期是？（如：每天 / 周一周三 / 周二周四周六）
   ```
3. **解析并写入配置**：将运营回复解析为星期数组，写入 config.json 的 schedule 字段
4. **确认响应**：
   ```
   ✅ 已新增类型「拉新」，执行周期：周二、周四
   当前排期表：
   - 签到：每天
   - 高耗币：周一
   - 礼物过期：周三、周五
   - 家族签到：周四、周六
   - 私聊：周二、周日
   - 拉新：周二、周四
   ```

新增的类型会自动纳入模式 B 定时任务：push-schedule 触发时会根据排期表匹配该类型，调用 crowd-async-fetch 获取人群包后查询 planName 含该关键词的历史模板来创建计划。

## 错误处理

| 错误场景 | 处理方式 |
|---------|---------|
| mws 未安装或未认证 | 提示用户运行 `mws auth status` 检查认证状态 |
| secretary-page 接口失败 | 返回原始错误信息 |
| secretary-create 接口失败 | 返回原始错误信息，包含在通知中 |
| clickRate 解析失败 | 视为 0，不阻塞选取逻辑 |
| planName 日期前缀不匹配 | 使用兜底名称 "{M.DD}{类型关键词}" |
| config.json 损坏或缺失 | 使用内置默认排期，notifyUsers 为空 |
| 当天 20:00 已过 | 提示用户确认是否仍创建 |
| nosKey 格式异常 | 提示用户检查 nosKey 格式 |
