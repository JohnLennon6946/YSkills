## ADDED Requirements

### Requirement: Tab 类型选择

系统必须在分配指令解析前获取用户选择的 tab 类型。已知枚举：THEME（key=theme，显示名=主题）、FAMILY_PLAY（key=family，显示名=家族在玩）、FAMILY_VOICE（key=family_voice，显示名=家族语音房）、RCMD（key=rcmd，显示名=推荐）、CITY（key=city，显示名=同城列表）、DAILY_TASK（key=task，显示名=日常任务）。允许用户输入已知枚举之外的 tab 值，透传即可。一次分配中所有号位共用同一个 tab。

#### Scenario: 用户在指令中附带 tab（已知枚举的 key）
- **WHEN** 用户发送"tab=theme 1-10号放1号位，时间是2025-01-01~2025-01-07"
- **THEN** 系统提取 tabType="theme"，继续解析分配指令

#### Scenario: 用户在指令中附带 tab（已知枚举的显示名）
- **WHEN** 用户发送"tab=主题 1-10号放1号位，时间是2025-01-01~2025-01-07"
- **THEN** 系统提取 tabType="主题"，透传给接口

#### Scenario: 用户指令中未附带 tab
- **WHEN** 用户发送分配指令但未包含 `tab=xxx`
- **THEN** 系统追问"请选择 tab 类型：主题 / 家族在玩 / 家族语音房 / 推荐 / 同城列表 / 日常任务（也可自行输入其他 tab 类型）"，等待用户选择

#### Scenario: 用户输入已知枚举之外的自定义 tab
- **WHEN** 用户指定 `tab=新活动类型`
- **THEN** 系统透传 tabType="新活动类型"，不拦截

### Requirement: 分配指令解析（序号范围格式）

系统必须解析用户发送的"{start}-{end}号放{N}号位，时间是{date}~{date}"格式的分配指令。

#### Scenario: 单个序号范围指令
- **WHEN** 用户发送"tab=theme 1-10号放1号位，时间是2025-01-01~2025-01-07"
- **THEN** 系统解析出：tabType="唠嗑"、房间序号范围 1-10、号位 "1"、开始时间 "2025-01-01"、结束时间 "2025-01-07"

#### Scenario: 多个序号范围指令
- **WHEN** 用户发送"tab=theme 1-10号放1号位，时间是2025-01-01~2025-01-07 11-25号放2号位，时间是2025-01-08~2025-01-14"
- **THEN** 系统解析出两条分配指令，共用 tabType="唠嗑"，分别对应 1 号位和 2 号位

#### Scenario: 序号超出数据范围
- **WHEN** 用户指定的序号范围超出第一步表格数据范围（如共 100 条但指定了 95-105）
- **THEN** 系统提示"序号 {start}-{end} 超出数据范围（共 {N} 条）"，跳过该条指令，继续处理下一条

#### Scenario: 指令无法解析
- **WHEN** 用户输入的指令格式无法被正则匹配
- **THEN** 系统追问"请按格式指定：`tab=theme 1-10号放1号位，时间是2025-01-01~2025-01-07`"，等待用户重新输入

### Requirement: 分配指令解析（心遇号格式）

系统必须解析用户发送的"心遇号 {id1},{id2} 放{N}号位，时间是{date}~{date}"格式的分配指令。

#### Scenario: 单个心遇号指令
- **WHEN** 用户发送"tab=theme 心遇号 12345,12346 放2号位，时间是2025-01-08~2025-01-14"
- **THEN** 系统解析出：tabType="唠嗑"、房间 ID 列表 ["12345", "12346"]、号位 "2"、开始时间 "2025-01-08"、结束时间 "2025-01-14"

#### Scenario: 心遇号 ID 非数字
- **WHEN** 用户指定的心遇号包含非数字字符（如"abc123"）
- **THEN** 系统提示"房间 ID 格式异常：{id}"，跳过该 ID

#### Scenario: 混合使用两种格式
- **WHEN** 用户在同一消息中混合使用序号范围和心遇号格式
- **THEN** 系统分别按各自规则解析，汇总为完整的分配指令列表，共用同一个 tabType

### Requirement: 序号到房间 ID 映射

系统必须在第一步表格缓存中按序号查找对应的房间 ID。

#### Scenario: 正常映射
- **WHEN** 用户指定序号范围 1-10
- **THEN** 系统从 `skill/union-resource-recommend/.cache/latest-result.json` 中取出序号 1 到 10 对应的房间 ID，用逗号拼接为 slots 参数

#### Scenario: 缓存文件缺失
- **WHEN** latest-result.json 不存在（未执行第一步或缓存已清理）
- **THEN** 系统提示"未找到推荐数据缓存，请先拉取资源位数据"，不执行创建

### Requirement: 逐号位创建推荐计划

系统必须对每条分配指令调用 rcmdback-add，传入 tabType，串行执行，单条失败不中断。

#### Scenario: 单号位创建成功
- **WHEN** 系统调用 `mws moyi-activity-backend rcmdback-add`，传入 slots、position、startTime、endTime、tabType
- **THEN** 系统输出进度反馈"正在创建资源位计划... (1/N) {N}号位 → 已创建（{M}个房间）"，继续下一条

#### Scenario: 单号位创建失败
- **WHEN** rcmdback-add 接口返回错误
- **THEN** 系统记录失败原因，输出错误信息，继续创建下一条

#### Scenario: 全部创建失败
- **WHEN** 所有号位的 rcmdback-add 调用均失败
- **THEN** 系统返回"所有号位创建均失败，请检查接口状态"

#### Scenario: 号位重复检测
- **WHEN** 用户指定的号位已在本次分配中出现过
- **THEN** 系统暂停并追问"号位 {N} 已分配，是否覆盖？"，等待用户确认

### Requirement: 创建结果汇总展示

系统必须在全部创建完成后调用 rcmdback-list 并展示汇总表格。

#### Scenario: 正常查询并展示
- **WHEN** 全部 rcmdback-add 调用完成后，系统调用 rcmdback-list
- **THEN** 系统输出包含号位、房间 ID 列表（含数量）、tab 类型、生效时间、计划 ID、状态的 Markdown 表格

#### Scenario: rcmdback-list 查询失败
- **WHEN** rcmdback-list 接口返回错误
- **THEN** 系统从各 rcmdback-add 的返回值拼接汇总信息，提示用户"查询接口不可用，以下为创建时返回的汇总"

#### Scenario: 部分成功部分失败
- **WHEN** 只有部分号位创建成功
- **THEN** 系统在汇总表格中分别标注成功和失败的号位，失败的注明失败原因
