## ADDED Requirements

### Requirement: 触发词识别与意图匹配

系统必须在收到用户消息时，按三层优先级匹配触发词，决定是否启动资源位取数流程。

#### Scenario: 明确指令触发
- **WHEN** 用户消息包含"多人房资源位"、"资源位推荐"或"资源位分配"
- **THEN** 系统直接进入离线取数流程，不追问

#### Scenario: 带域名词触发
- **WHEN** 用户消息包含"工会资源位"、"union资源位"、"公会资源位"或"数字员工资源位"
- **THEN** 系统直接进入离线取数流程，不追问

#### Scenario: 模糊查询触发
- **WHEN** 用户消息包含"拉取资源位"、"查询资源位"或"获取资源位"
- **THEN** 系统直接进入离线取数流程，不追问

#### Scenario: 仅出现"资源位"无上下文
- **WHEN** 用户消息中仅出现"资源位"且无动词或其他上下文
- **THEN** 系统追问"请问需要拉取多人房资源位推荐数据吗？"，等待用户确认后再触发

#### Scenario: 其他类型资源位不触发
- **WHEN** 用户提到"banner资源位"等非多人房类型的资源位
- **THEN** 系统不触发本 Skill，提示暂不支持该类型

### Requirement: 异步取数任务提交

系统必须向 moyi-activity-backend 提交 type=unionCoins 的异步取数任务，并获取 processId。

#### Scenario: 任务提交成功
- **WHEN** 系统调用 `mws moyi-activity-backend open-task-process --params '{"type":"unionCoins"}'`
- **THEN** 系统获取有效 processId，进入轮询阶段

#### Scenario: 接口不可用
- **WHEN** open-task-process 接口返回错误或不可达
- **THEN** 系统返回"资源位取数接口暂不可用，请稍后重试"，流程终止

#### Scenario: 返回空 processId
- **WHEN** 接口返回成功但 processId 为空
- **THEN** 系统返回"任务提交失败，未获取到有效的任务 ID"，流程终止

### Requirement: 任务结果轮询（CronCreate 调度）

系统必须在任务提交后立即注册 CronCreate 轮询脚本（每分钟一次），不在当前 turn 阻塞。轮询检测到任务完成或超时后，CronDelete 移除 cron 并通知用户。

#### Scenario: 任务提交成功后注册 cron
- **WHEN** open-task-process 返回有效 processId
- **THEN** 系统立即注册 CronCreate（cron: `*/1 * * * *`），轮询脚本调用 open-task-process-status

#### Scenario: 轮询中任务进行中
- **WHEN** cron 轮询返回 `status: "process"`
- **THEN** 系统仅首次输出进度提示（含 rate 百分比），后续轮询静默

#### Scenario: 轮询中任务完成
- **WHEN** cron 轮询返回 `status: "done"`
- **THEN** 系统 CronDelete 移除 cron，取 dataUrl 和 totalNum，进入数据展示阶段

#### Scenario: 单次轮询网络错误
- **WHEN** 单次 cron 轮询因网络错误失败
- **THEN** 系统不中断，继续下一次 cron

#### Scenario: 轮询超时
- **WHEN** 累计轮询超过 3 小时（180 次）仍未完成
- **THEN** 系统 CronDelete 移除 cron，返回"数据拉取超时（已等待 3 小时），请稍后重试。processId: {processId}"

#### Scenario: CronCreate 注册失败降级
- **WHEN** CronCreate 注册失败
- **THEN** 系统回退为同步轮询模式（当前 turn 内最多 5 次），提示用户可能需要手动查询

### Requirement: 推荐数据表格展示

系统必须将 dataUrl 返回的数据解析为 Markdown 表格，全量展示在对话中。

#### Scenario: 正常数据展示
- **WHEN** dataUrl 可访问且返回约 100 条有效数据
- **THEN** 系统输出包含序号、房间名、房间 ID、资源位类型、推荐分值、推荐理由的完整 Markdown 表格，末尾附 dataUrl 下载链接

#### Scenario: 全量展示不截断
- **WHEN** 数据量为 100 条左右
- **THEN** 系统一次性输出完整表格，不做分页或截断

#### Scenario: 返回数据为空
- **WHEN** totalNum 为 0 或数据列表为空
- **THEN** 系统返回"本次未拉取到资源位推荐数据，请确认数据源是否有新数据"

#### Scenario: dataUrl 不可访问
- **WHEN** dataUrl 返回错误或超时
- **THEN** 系统返回"数据拉取完成但下载链接不可用"，附带 processId 和 dataUrl 供排查

#### Scenario: 字段与预期不一致
- **WHEN** 返回数据的字段名与预期不同
- **THEN** 系统以实际字段为准动态生成表头，并提示用户"返回字段与预期不一致，已按实际字段展示"

#### Scenario: 数据解析失败
- **WHEN** dataUrl 返回的内容无法解析
- **THEN** 系统返回"数据解析失败，请检查返回格式"，附带 dataUrl 供手动查看

### Requirement: 数据缓存

系统必须在表格展示后，将解析后的结构化数据写入 `skill/union-resource-recommend/.cache/latest-result.json`，供第二步序号→ID 映射使用。

#### Scenario: 正常缓存
- **WHEN** 数据解析并展示成功
- **THEN** 系统写入 latest-result.json，包含 fetchedAt、totalNum、dataUrl、rows（每行含 seq、roomName、roomId 等字段）

#### Scenario: 缓存写入失败
- **WHEN** 文件写入因权限或磁盘问题失败
- **THEN** 表格仍正常展示，系统提示"数据缓存失败，第二步需手动指定心遇号"
