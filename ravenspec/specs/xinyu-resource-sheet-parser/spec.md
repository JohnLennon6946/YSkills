# xinyu-resource-sheet-parser Specification

## Purpose
TBD - created by archiving change mws-xinyu-activity-create. Update Purpose after archive.
## Requirements
### Requirement: POPO 在线表格读取

本 skill 必须接收 POPO 在线表格链接，通过 `popo-doc-read` skill 读取表格内容并解析为结构化数据。

#### Scenario: 链接合法且权限可访问

- **WHEN** 主 skill 传入合法的 POPO 在线表格链接
- **THEN** 调用 popo-doc-read skill 读取表格内容，按 sheet 拆分解析

#### Scenario: 链接无法访问

- **WHEN** popo-doc-read 返回权限拒绝 / 链接非法
- **THEN** 向主 skill 返回失败 + 失败原因"链接无法读取，请检查权限或重新发送"

#### Scenario: popo-doc-read 解析能力不足 [F8 待 design 验证]

- **WHEN** popo-doc-read 无法正确识别多 sheet 结构 / 单元格内容
- **THEN** 向主 skill 返回失败 + 提示"表格读取失败，请尝试将表格另存为标准格式后重新发送"；design 阶段需评估是否新建 popo-sheet-read 替代方案

### Requirement: 任务 sheet 解析

本 skill 必须按以下结构解析任务 sheet：以「任务名称」为唯一匹配键，仅消费「奖励包 ID」列。

#### Scenario: 任务 sheet 结构完整

- **WHEN** 任务 sheet 含至少「任务名称」和「奖励包 ID」两列（其他列：任务描述 / 任务类型 / 完成条件 / 任务周期 仅供运营参考，本 skill 不消费）
- **THEN** 解析为 `List<MissionResourceEntry>{missionName: string, rewardBoxId: string | empty}`

#### Scenario: 任务 sheet 缺失必需列

- **WHEN** 任务 sheet 不含「任务名称」列或不含「奖励包 ID」列
- **THEN** 向主 skill 返回失败 + 失败原因"任务 sheet 缺少列 <列名>"

#### Scenario: 任务 sheet 含同名重复

- **WHEN** 任务 sheet 中存在 missionName 完全相同的多行
- **THEN** 全部保留（不去重）；下游消费方（xinyu-mission-clone）自行处理重复

### Requirement: 抽奖 sheet 解析

本 skill 必须按以下结构解析抽奖 sheet：先解析表头区（资产币 ID），再解析奖品表区。

#### Scenario: 抽奖 sheet 结构完整

- **WHEN** 抽奖 sheet 含：
  - 表头区第 1 行：`抽奖` 标识（仅用于辨识）
  - 表头区第 2 行：`资产币ID`
  - 表头区第 3 行：（资产币 ID 数值，如 `2003754`）
  - 第 4 行起：奖品表列名「奖励包 ID / 基础权重 / 保底权重 / 是否未中奖奖品 / 作弊权重 / 库存类型 / 库存数量」
- **THEN** 解析为 `LotteryResourceEntry{interestId: long, awards: List<AwardResourceEntry>{rewardBoxId, baseWeight, floorWeight, isLose, cheatWeight, inventoryType, inventoryNum}}`

#### Scenario: 抽奖 sheet 缺失必需字段

- **WHEN** 抽奖 sheet 无法识别表头区资产币 ID，或奖品表区缺少必需列
- **THEN** 向主 skill 返回失败 + 失败原因"抽奖 sheet 缺少 <字段名>"

#### Scenario: 抽奖 sheet 权重列非整数

- **WHEN** 奖品行的「基础权重 / 保底权重 / 作弊权重 / 库存数量」列值非整数
- **THEN** 向主 skill 返回失败 + 失败原因"抽奖 sheet 第 N 行 <字段名> 必须为整数"

#### Scenario: 抽奖 sheet 「是否未中奖奖品」字段值合法

- **WHEN** 「是否未中奖奖品」列值为 `是` 或 `否`
- **THEN** 解析为 boolean（`是` → true，`否` → false）

#### Scenario: 抽奖 sheet 「是否未中奖奖品」字段值非法

- **WHEN** 「是否未中奖奖品」列值既不是 `是` 也不是 `否`
- **THEN** 向主 skill 返回失败 + 失败原因"抽奖 sheet 第 N 行 是否未中奖奖品 必须为 是 或 否"

### Requirement: 库存类型容错映射

本 skill 必须对「库存类型」列做容错映射（仅辨识，不报错；映射失败由下游 xinyu-lottery-clone 处理）。

#### Scenario: 精确匹配 InventoryCycle desc

- **WHEN** 「库存类型」列值精确等于 InventoryCycle 任一 desc（如 "一次性库存" / "无限库存"）
- **THEN** 返回对应 code（1-8）

#### Scenario: 模糊匹配关键词

- **WHEN** 「库存类型」列值不精确匹配但含已知关键词（如 "无限"→5, "一次"→4, "每日"→1, "半天"→2, "每小时"→3, "3 小时"→6, "6 小时"→7, "10 分钟"→8）
- **THEN** 返回对应 code

#### Scenario: 无法识别

- **WHEN** 「库存类型」列值无法精确匹配也无法模糊匹配
- **THEN** 返回原始字符串，由下游 xinyu-lottery-clone 决定如何处理（推测会记入兜底事件 + 跳过该奖品）

### Requirement: 多 sheet 区分

本 skill 必须按 sheet 名区分任务和抽奖。

#### Scenario: 标准 sheet 命名

- **WHEN** 表格含两个 sheet，sheet 名分别包含「任务」和「抽奖」关键词
- **THEN** 任务 sheet → 任务解析逻辑；抽奖 sheet → 抽奖解析逻辑

#### Scenario: sheet 缺失

- **WHEN** 主 skill 要求解析任务但表格无任务 sheet（或同理抽奖）
- **THEN** 向主 skill 返回失败 + 失败原因"表格缺少 <任务/抽奖> sheet"

#### Scenario: 多奖池场景 [F6 待 design 阶段细化]

- **WHEN** 源 plan 含多奖池，表格内多个奖池 sheet（约定命名如「抽奖-1」「抽奖-2」）
- **THEN** 解析为 `List<LotteryResourceEntry>`（按 sheet 顺序）；与源奖池的对齐策略由 xinyu-lottery-clone 实现

### Requirement: 返回结构

本 skill 必须按结构化格式返回解析结果。

#### Scenario: 解析成功

- **WHEN** 表格解析完成
- **THEN** 必须返回：
  - `success`: boolean
  - `missionEntries`: List<MissionResourceEntry>（任务记录列表，可为空）
  - `lotteryEntries`: List<LotteryResourceEntry>（抽奖记录列表，按 sheet 顺序，可为空）
  - `errors`: List<string>（解析过程中遇到的格式错误明细）

#### Scenario: 解析失败

- **WHEN** 表格读取或必需字段缺失等不可恢复错误
- **THEN** `success` = false，`errors` 中包含人类可读的失败原因，由主 skill 反馈给运营

