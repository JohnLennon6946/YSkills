# xinyu-plan-clone Specification

## Purpose
TBD - created by archiving change mws-xinyu-activity-create. Update Purpose after archive.
## Requirements
### Requirement: POPO 入口意图识别

本 skill 必须监听 POPO 群 @机器人或私聊消息，通过 LLM 自由意图识别（非严格关键词）判定运营是否在请求"创建新的活动发布计划"。

#### Scenario: 运营触发克隆意图

- **WHEN** 运营在 POPO 中发送任意表达"创建新活动发布计划"意图的消息（如"帮我创建一个新的活动发布计划"、"我要建一个新计划"）
- **THEN** 机器人必须在 30 秒内回复，追问"全新发布计划"或"以已有发布计划名称为模板克隆"二选一

#### Scenario: 触发语无法识别

- **WHEN** 运营消息与"创建活动发布计划"意图不匹配
- **THEN** 本 skill 必须不响应（让其他 skill 或默认响应处理）

### Requirement: 公共账号鉴权

本 skill 通过 mws 公共账号鉴权调用后端接口，不涉及个人 ds_token。

#### Scenario: 公共账号鉴权正常

- **WHEN** bot 服务已正确配置公共账号 token
- **THEN** 所有 mws 命令通过公共账号 token 执行，无需运营绑定个人 token

#### Scenario: 公共账号鉴权失败

- **WHEN** mws 命令因鉴权失败返回错误
- **THEN** 提示运营联系管理员检查公共账号配置

### Requirement: 模板克隆 vs 全新发布计划分流

机器人必须按运营选择走不同分支。

#### Scenario: 选择模板克隆

- **WHEN** 运营回复"模板克隆"或同义表达
- **THEN** 进入功能 2 模板检索流程

#### Scenario: 选择全新发布计划

- **WHEN** 运营回复"全新发布计划"或同义表达
- **THEN** 回复"全新发布计划能力建设中，敬请期待"并终止当前会话

#### Scenario: 回复无法识别

- **WHEN** 运营回复既非"模板克隆"也非"全新发布计划"
- **THEN** 再次追问最多 1 次；仍无法识别则终止并提示按格式重发

### Requirement: 模板发布计划检索与选定

机器人必须引导运营输入计划名称关键词，调用 `mws moyi-activity-backend plan-list` 模糊匹配，呈现候选列表，运营按编号选定。

#### Scenario: 模糊匹配命中 ≤20 条

- **WHEN** plan-list 返回结果数 ≤20
- **THEN** 全量展示候选列表，每条包含「编号 + 计划名称 + 开始时间 + 结束时间」

#### Scenario: 模糊匹配命中 >20 条

- **WHEN** plan-list 返回结果数 >20
- **THEN** 仅展示最近修改的 20 条 + 提示"还有 N 条未展示，请输入更精确的关键词"

#### Scenario: 模糊匹配 0 条命中

- **WHEN** plan-list 返回 0 条结果
- **THEN** 回复"未找到匹配计划，请重新输入关键词"，允许运营重试最多 3 次

#### Scenario: 运营输入无效编号

- **WHEN** 运营回复的编号超出候选列表范围
- **THEN** 回复"编号无效，请重新选择"，允许重试最多 3 次

### Requirement: 活动时间收集

机器人必须询问新活动的开始日期和结束日期，并按既定规则补全为完整时间戳。

#### Scenario: 运营输入合法日期范围

- **WHEN** 运营回复合法日期范围（如"6.1-6.10"）
- **THEN** 计算开始时间 = 开始日期 15:00:00 (Asia/Shanghai)，结束时间 = 结束日期 23:59:59 (Asia/Shanghai)

#### Scenario: 日期格式无法解析

- **WHEN** 运营输入的日期无法解析为有效日期
- **THEN** 提示"日期格式无法识别，请按 `M.d-M.d` 格式输入"

#### Scenario: 结束日期不晚于开始日期

- **WHEN** 解析后的结束日期 ≤ 开始日期
- **THEN** 提示"结束日期必须晚于开始日期，请重新输入"

### Requirement: 新发布计划创建与映射表 M1 构建

机器人必须按以下顺序创建新 plan 并构建源/新 panel activityId 映射表 M1。

#### Scenario: 完整创建流程

- **WHEN** 运营选定源 plan 并输入活动时间
- **THEN** 依次执行：
  1. 调用 `panel-list` 查源 plan 的模块清单
  2. 按日期 token 规则生成新 plan 名（识别到 token 则替换；否则末尾追加 `M.d-M.d`）
  3. 调用 `plan-create`，传入 name + startTime + endTime + modules（沿用源） + domain（沿用源） + noticeCorps（沿用源）
  4. 调用 `panel-list` 查新 plan，构建映射表 M1（源 panel activityId → 新 panel activityId）

#### Scenario: plan-create 被 allowCreatePlanGapMinutes 校验拒绝

- **WHEN** plan-create 返回"活动开始时间需要在 N 分钟后"等时间提前量校验错误
- **THEN** 把后端报错原样反馈给运营，提示重新选日期

#### Scenario: plan-create 其他错误

- **WHEN** plan-create 因其他原因失败
- **THEN** 终止整个流程并把 mws 报错原样反馈给运营

### Requirement: 资源配置表格收集

机器人必须根据 plan 的 modules 类型决定是否提示运营发送资源表格。

#### Scenario: plan 含 mission 或 spinach 模块

- **WHEN** 新 plan 的 modules 包含 mission 或 spinach
- **THEN** 提示"本计划含 <模块列表>；请发送资源配置在线表格链接，需包含任务、抽奖两个 sheet"，并等待运营回复链接

#### Scenario: plan 仅含 wechat 模块

- **WHEN** 新 plan 的 modules 仅含 wechat（无 mission/spinach）
- **THEN** 跳过资源收集环节，直接进入小程序活动复制

#### Scenario: 资源表格读取失败

- **WHEN** 调用 `xinyu-resource-sheet-parser` 解析失败 3 次
- **THEN** 记入兜底事件并继续后续模块（任务/抽奖将走"全部按源沿用"路径）

### Requirement: 子模块编排严格顺序

机器人必须按"任务 → 抽奖 → 小程序活动"顺序执行子 skill，过程中累积映射表 M1-M6。

#### Scenario: 模块全部存在的标准流程

- **WHEN** 新 plan 含 mission + spinach + wechat 三个模块
- **THEN** 依次调用：
  1. `xinyu-mission-clone`（传入：源 mission panel activityId + **新 mission panel activityId**（来自 M1）+ 新 plan 时间 + 任务资源数据；产出 M2: 源 box id → 新 box id）
  2. `xinyu-lottery-clone`（传入：源 spinach panel activityId + 新 spinach panel activityId（来自 M1）+ 新 plan 时间 + 抽奖资源数据；产出 M3/M4/M5: 源奖池 id/token/资产币 id → 新值）
  3. `xinyu-act-resource-clone`（传入：源 wechat panel activityId + 新 wechat panel activityId（来自 M1）+ M1-M5；消费 M1-M5，先 type=7 创建产出 M6，再 type=4 patch configJson）

#### Scenario: 部分模块缺失

- **WHEN** 新 plan 仅含部分模块（如 mission + wechat 但无 spinach）
- **THEN** 仍按相对顺序调用存在的模块子 skill；缺失模块的映射表条目留空，依赖该映射的下游模块走"保留源值 + 记入兜底事件"分支

#### Scenario: 某个子模块全失败

- **WHEN** 某子 skill（如 xinyu-mission-clone）返回完全失败
- **THEN** 记入兜底事件，**不阻断**后续子模块继续执行

### Requirement: 兜底事件汇总通知

机器人必须在所有子模块执行完毕后，统一发送一条 POPO 消息汇总成功项 + 失败明细。

#### Scenario: 全部成功

- **WHEN** 所有子模块均成功，无兜底事件
- **THEN** 发送通知含：新 plan 名称 + plan id + 成功项数量统计（N 主任务 / M 奖池 / K 小程序资源）

#### Scenario: 存在兜底事件

- **WHEN** 任一子模块产生兜底事件
- **THEN** 发送通知含：成功汇总 + 失败明细（按模块分组，每条定位到具体模块/任务/奖池/失败原因） + 行动建议"请前往 mws 后台手动补充失败项"

#### Scenario: 通知消息超长

- **WHEN** 汇总消息超过 3000 字符
- **THEN** 拆分为多条按顺序发送

### Requirement: 中途取消处理

机器人必须支持运营在任意交互节点回复"取消"或同义表达。

#### Scenario: 取消时新 plan 未创建

- **WHEN** 运营在 plan-create 之前取消
- **THEN** 直接终止会话，无需清理

#### Scenario: 取消时新 plan 已创建

- **WHEN** 运营在 plan-create 之后任意节点取消
- **THEN** 终止当前会话并明确提示"新 plan 已创建（id=X，name=Y），请前往 mws 后台手动清理"，**不**调用任何删除接口

### Requirement: 会话超时回收

机器人必须管理单运营会话超时。

#### Scenario: 长时间无响应

- **WHEN** 运营在某一步超过 10 分钟无响应
- **THEN** 当前会话上下文被回收，运营需重新触发

#### Scenario: 单运营并发会话限制

- **WHEN** 运营已有进行中的克隆会话，又触发新的
- **THEN** 提示"你有进行中的会话（在第 N 步），请先完成或回复取消"

### Requirement: 环境选择

机器人必须按运营意图选择 mws 环境。

#### Scenario: 默认环境

- **WHEN** 运营触发语中无环境表述
- **THEN** 所有 mws 命令使用 `--env online`

#### Scenario: 明确指定测试环境

- **WHEN** 运营触发语含"测试环境"、"test 环境"等表达
- **THEN** 所有 mws 命令使用 `--env test`

