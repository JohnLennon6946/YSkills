---
name: xinyu-resource-sheet-parser
description: 解析心遇活动资源配置表格（POPO 在线表格），提取任务 sheet 和抽奖 sheet 数据为结构化 JSON。供 xinyu-plan-clone 主 skill 调用。
---

# xinyu-resource-sheet-parser

解析运营提供的 POPO 在线表格链接，提取任务和抽奖两个 sheet 的结构化数据。

## 输入

主 skill 传入：
- `sheetUrl`: POPO 在线表格链接
- `modules`: 需要解析的模块列表（如 `["mission", "spinach"]`）

## 工作流程

### Step 1: 读取表格内容

调用 `popo-doc-read` skill 读取表格：

```bash
node scripts/read_popo_doc.mjs '<sheetUrl>'
```

若读取失败，返回失败结果并附原因。

### Step 2: 多 sheet 区分

按 sheet 名称中的关键词区分：
- 含「任务」→ 任务 sheet
- 含「抽奖」→ 抽奖 sheet（多奖池场景：「抽奖-1」「抽奖-2」按顺序排列）

若 modules 包含 `mission` 但表格缺少任务 sheet → 返回失败。
若 modules 包含 `spinach` 但表格缺少抽奖 sheet → 返回失败。

### Step 3: 解析任务 sheet

**必需列**：「任务名称」、「奖励包 ID」

其他列（任务描述 / 任务类型 / 完成条件 / 任务周期）仅供运营参考，本 skill 不消费。

解析规则：
- 按行遍历，跳过表头行
- 每行提取 `missionName`（任务名称列）和 `rewardBoxId`（奖励包 ID 列）
- `rewardBoxId` 为空时保留空字符串（下游按"保留源值"处理）
- 同名 `missionName` 不去重，全部保留（下游自行处理重复）

缺少必需列 → 返回失败 + "任务 sheet 缺少列 <列名>"。

### Step 4: 解析抽奖 sheet

**表头区**（前 3 行）：
- 第 1 行：「抽奖」标识（仅辨识用）
- 第 2 行：「资产币ID」标签
- 第 3 行：资产币 ID 数值（如 `2003754`）

**奖品表区**（第 4 行起）：
- 第 4 行为列名行，必需列：「奖励包 ID」「基础权重」「保底权重」「是否未中奖奖品」「作弊权重」「库存类型」「库存数量」
- 第 5 行起为奖品数据行

解析规则：
- `interestId` = 第 3 行数值
- 每行奖品提取 7 个字段
- `基础权重` / `保底权重` / `作弊权重` / `库存数量` 必须为非负整数，否则返回失败 + "抽奖 sheet 第 N 行 <字段名> 必须为整数"
- `是否未中奖奖品` 必须为「是」或「否」，映射为 boolean（是→true，否→false），否则返回失败
- `库存类型` 做容错映射（见下方映射表），无法识别时返回原始字符串由下游处理

缺少必需列 → 返回失败 + "抽奖 sheet 缺少 <字段名>"。

### 库存类型容错映射

| code | enum 名 | 精确匹配 desc | 模糊匹配关键词 |
|------|---------|--------------|---------------|
| 1 | DAILY | "每日库存" | 含"每日" |
| 2 | HALF | "半天库存" | 含"半天" |
| 3 | HOURLY | "每小时库存" | 含"每小时" |
| 4 | ONCE | "一次性库存" | 含"一次" |
| 5 | NO_LIMIT | "无限库存" | 含"无限" |
| 6 | THREE | "3小时库存" | 含"3小时"或"三小时" |
| 7 | SIX | "6小时库存" | 含"6小时"或"六小时" |
| 8 | MIN_10 | "10分钟库存" | 含"10分钟"或"十分钟" |

匹配优先级：精确匹配 > 模糊匹配。均不命中则返回原始字符串。

## 返回格式

在响应末尾输出以下 JSON 块（用 ` ```json ``` ` 包裹）：

**成功时**：
```json
{
  "skill": "xinyu-resource-sheet-parser",
  "success": true,
  "missionEntries": [
    {"missionName": "签到", "rewardBoxId": "8439053"},
    {"missionName": "送礼", "rewardBoxId": ""}
  ],
  "lotteryEntries": [
    {
      "interestId": 2003754,
      "awards": [
        {
          "rewardBoxId": "8440046",
          "baseWeight": 100,
          "floorWeight": 100,
          "cheatWeight": 100,
          "isLose": false,
          "inventoryType": 4,
          "inventoryNum": 0
        }
      ]
    }
  ],
  "errors": []
}
```

**失败时**：
```json
{
  "skill": "xinyu-resource-sheet-parser",
  "success": false,
  "missionEntries": [],
  "lotteryEntries": [],
  "errors": ["任务 sheet 缺少列 奖励包 ID"]
}
```

## 注意事项

- `missionEntries` 和 `lotteryEntries` 可为空列表（当 modules 不含对应模块时）
- 多奖池场景：`lotteryEntries` 按 sheet 顺序排列，每个元素对应一个奖池 sheet
- 本 skill 不负责权重和校验（100%），也不负责库存类型映射失败的处理，这些由下游 xinyu-lottery-clone 处理
