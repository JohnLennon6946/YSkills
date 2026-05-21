# mws-xinyu-activity-create 技术方案

## 方案概述

本方案以 **5 个 Markdown skill 文件**（1 主 + 4 子）实现心遇活动发布计划克隆能力。所有 skill 通过 LLM 编排执行，业务调用全部委托 `bash` 工具调 `mws moyi-activity-backend.*` 命令，资源表格读取委托现有 `popo-doc-read` skill（design 阶段已确认有兼容性风险，见风险表）。主 skill 持有「源 ID → 新 ID」映射表（M1-M6）作为上下文跨子 skill 传递，每个子 skill 独立返回结构化结果（成功/失败/兜底事件清单）。所有 5 个 skill 文件落在 YSkills 仓的 `.claude/skills/` 目录下，与现有的 `sdd-mws-cli`、`popo-doc-read` 同级。

## 关键决策

### 决策 1：skill 形态 = 纯 Markdown SKILL.md + bash 委托执行

**选择**：每个 skill 由一个 SKILL.md 文件承载，内含 YAML frontmatter（name/description/metadata）+ Markdown 正文（业务指令）。skill 不携带独立可执行脚本，所有 mws 调用通过 Bash 工具委托 `mws ...` 命令。

**理由**：
- 与仓内现有 skill（sdd-mws-cli、popo-doc-read 等）形态一致，便于维护与升级
- 业务逻辑全部跑在 LLM 编排层，不需要单独部署服务
- 调用 mws 已经过 mws-shared 标准化（公共账号鉴权），不需要重复鉴权代码

**备选**：
- 写 Python/Node.js 脚本并通过 skill 调用：放弃，引入额外语言依赖、与仓内现有 skill 形态不一致
- 把全部 5 个 skill 合并为 1 个大 SKILL.md：放弃，违背 PRD 中"独立可测试"的 capability 拆分原则

### 决策 2：主 skill 与子 skill 的调用模式 = LLM 委托调用 + 结构化返回

**选择**：主 skill (`xinyu-plan-clone`) 在 Markdown 指令中**明确指示** LLM 在合适时机使用 `skill` 工具调用各子 skill，并要求每个子 skill 在响应末尾输出**约定结构的 JSON 块**（含 success / mapping / events 字段），主 skill 从该 JSON 块解析数据后继续编排。

**理由**：
- LLM 解析 JSON 比解析自然语言可靠
- 各子 skill 独立可测试，不耦合主 skill 内部状态
- 与 raven-autopilot 等仓内现有"主 skill 编排子 skill"模式一致

**备选**：
- 用 todo state 跨 skill 传递：放弃，todo 是任务跟踪机制不适合数据传递，且 state 在子 skill 内会被覆盖
- 把所有逻辑塞主 skill：放弃，违背 capability 拆分

### 决策 3：mws 调用 — 缺失接口的应对策略

**选择**：采用「分级降级」方案：
- **优先**：调 `mws moyi-activity-backend copy-mundo`（首选，最少代码）
- **如 mws 暂未暴露**：fallback 到「mundo-query + info-save」组合手工构造（即遍历源 mundo 树，对每个 mission 独立保存）
- **风险记录**：currently `mws moyi-activity-backend -h` 列出 14 个方法中**不含 copy-mundo**，本期实施前必须确认 mws 团队是否已暴露（用户曾告知"接口补充了"，需 verify）

**理由**：
- copy-mundo 是后端已有的成熟接口，能一次性完成树结构克隆
- mws 暴露是工程依赖而非业务问题，预期 1-2 天可推动
- 同时保留 fallback 路径避免阻塞

**备选**：
- 直接手工构造 mundo+box+mission：放弃首选，代码量增加 4-5 倍且容易遗漏字段
- 等 mws 暴露后再启动：放弃，可在 fallback 路径下先跑通整体编排

### 决策 4：POPO 在线表格读取 — 优先复用 popo-doc-read + 兜底新建 popo-sheet-read

**选择**：
- 第一阶段（MVP）：`xinyu-resource-sheet-parser` 直接调用 `popo-doc-read` skill，将返回的文本通过 LLM 二次解析为结构化数据
- 第二阶段（如第一阶段失败）：design 阶段实测后若 popo-doc-read 完全无法识别 sheet 结构，由 `xinyu-resource-sheet-parser` 的 SKILL.md 增加新建 `popo-sheet-read` skill 的提案

**理由**：
- 仓内无专用 sheet skill，新建依赖增加 setup 成本
- popo-doc-read 本身能拉 POPO 文档原始内容，LLM 解析能补足结构识别能力
- 真实需要时再升级，避免提前优化

**备选**：
- 第一天就新建 popo-sheet-read：放弃，未实测 popo-doc-read 能力前不增加新 skill
- 让运营手动粘贴表格内容到 POPO 消息：放弃，运营负担重 + 易出错

### 决策 5：跨模块映射表 M1-M6 — 主 skill 上下文累积

**选择**：主 skill 维护一个内存累积的「映射表对象」，结构：

```
mappings = {
  M1: {sourcePanelActivityId -> newPanelActivityId},     # plan-create 后构建
  M2: {sourceBoxId -> newBoxId},                          # 任务子 skill 返回
  M3: {sourceTenantId -> newTenantId},                    # 抽奖子 skill 返回
  M4: {sourceToken -> newToken},                          # 抽奖子 skill 返回
  M5: {sourceInterestId -> newInterestId},                # 抽奖子 skill 返回
  M6: {sourceActResourceId -> newActResourceId}           # 小程序活动子 skill 返回（type=7）
}
```

每个子 skill 返回 JSON 中包含自己负责的映射表条目，主 skill 在调用下一个子 skill 时传入累积后的完整 mappings 对象。

**理由**：
- 显式数据传递避免"魔法状态"
- 调试时 mappings 可作为日志输出查看
- 子 skill 独立测试时可 mock mappings

**备选**：
- 持久化到外部存储（如 git notes、本地文件）：放弃，会话短期内无需持久化
- 让每个子 skill 自己查 mws 重建映射：放弃，重复请求浪费且易不一致

### 决策 6：日期 token 识别 — 单一正则集 + 多模式 union

**选择**：定义统一的正则集（全局共享，给 plan 名/任务名/box 名/资源名/ruleText 都用），按优先级匹配以下 7 种格式：

| 优先级 | 格式 | 示例 | 用于 |
|---|---|---|---|
| 1 | `M月d号HH:MM:SS-M月d号HH:MM:SS` | `5月19号15:00:00-5月24号23:59:59` | ruleText |
| 2 | `M月d日HH:MM:SS-M月d日HH:MM:SS` | `5月19日15:00:00-5月24日23:59:59` | ruleText 变体 |
| 3 | `M月d号-M月d号` | `5月19号-5月24号` | ruleText 简化 |
| 4 | `M月d日-M月d日` | `5月19日-5月24日` | ruleText 简化 |
| 5 | `M.d-M.d` | `5.19-5.24` | plan 名/资源名 |
| 6 | `M/d-M/d` | `5/19-5/24` | plan 名/资源名 |
| 7 | `MMdd-MMdd` | `0519-0524` | plan 名/资源名 |

替换时保持原格式（如源是 `M.d-M.d` 则新名也用 `M.d-M.d`，源是 `MMdd-MMdd` 则新名也用 `MMdd-MMdd`）。

**理由**：
- 真实生产数据已确认 #1 和 #5 格式存在（来自 FINDINGS F7）
- 七种格式覆盖绝大多数运营常用写法
- 单一正则集便于维护

**备选**：
- 用 LLM 自由识别日期：放弃，不稳定且不可测试
- 仅支持单一格式：放弃，运营自由度太低

### 决策 7：失败兜底事件 — 累积上报 + 单次汇总通知

**选择**：每个子 skill 返回的 events 数组结构：
```
{
  level: "warn" | "error",
  path: "<计划名> → <主任务名> → <任务组名> → <子任务名>",
  reason: "<人类可读的失败原因>"
}
```

主 skill 在最终汇总时按模块 + level 分组，统一通过 POPO 消息发送。**仅会话内存**，不持久化。

**理由**：
- 与 PRD 决策 15 一致
- level 区分让运营优先处理 error
- path 字段让运营能精确定位

**备选**：
- 实时逐条推送：放弃，POPO 消息会被淹没
- 持久化到外部存储：放弃，会话短期内运营能看完

### 决策 8：POPO bot 集成 — 把本 skill 作为 bot 后端的"执行模块"

**选择**：本期 5 个 skill 是**业务能力载体**，POPO bot 服务是**入口适配器**：bot 负责 POPO 消息收发 + sender_id 解析 + 调用 `xinyu-plan-clone` skill；skill 内部不直接依赖 POPO API。

**理由**：
- skill 与传输层解耦，未来换企业微信 / 钉钉等渠道时复用 skill
- bot 服务可与 plurk-mcp 等现有 bot 共享部署模板
- 鉴权（公共账号）由 bot 服务统一注入，skill 不感知

**备选**：
- skill 直接调 POPO API：放弃，耦合度高、难测试
- bot 内嵌业务逻辑、不拆 skill：放弃，违背 capability 拆分

### 决策 9：奖池字段构造 — TenantConfigVO JSON 整体覆盖

**选择**：`xinyu-lottery-clone` 在构造新奖池时，把 tenant-query 返回的 TenantConfigVO **整体作为基线**，仅修改：
- basicInfo.remark / startTime / endTime / activityId
- basicInfo.token / tenantId 置 0（让后端生成）
- tenantExtInfo.interestId（来自资源表格）
- awards 数组按资源表格重建（含 awardId 置 0、currentInventoryNum 置 0、probMap 三档构造）

其他所有字段（template / 跑马灯 / 暴走 / 扩展点 / 推送 IM 等）原样沿用。

**理由**：
- 避免遗漏字段（TenantConfigVO 含 50+ 字段，逐个映射易出错）
- 真实数据显示这些字段在 iOS 复购系列保持稳定，无需运营干预
- template-create 后端 saveOrUpdate 模式天然支持整体覆盖

**备选**：
- 逐字段映射：放弃，工作量大且易遗漏
- 调用 tenant-update 接口：放弃，是创建新奖池而非更新

### 决策 10：抽奖转盘 configJson patch — 字段级精确替换

**选择**：`xinyu-act-resource-clone` 解析 configJson 为 JSON 对象后，对**固定 7 个 key** 做精确替换（token / relatedPoolId / relatedTicketId / relatedActivityId / poolCount / taskPlayId / taskGroupId），ruleText 单独走日期识别替换分支。其余 30+ 字段（图片 URL / 颜色等）原样保留，最终序列化回 JSON 字符串。

**理由**：
- 7 个跨模块引用字段是真实数据已确认的（FINDINGS F16）
- 字段级 patch 比整体重建安全（避免漏字段导致前端展示异常）
- ruleText 单独处理是因为它是嵌套文本而非引用 id

**备选**：
- 整体重建 configJson：放弃，30+ 视觉字段需要重新提供，运营负担大
- 用通用 JSON path 替换工具：放弃，过度抽象

## 改动范围

| 文件 | 操作 | 改动内容 |
|------|------|----------|
| `.claude/skills/xinyu-plan-clone/SKILL.md` | 新增 | 主 skill：POPO 入口意图识别、运营多轮交互、模板检索、plan-create、子 skill 编排、兜底汇总 |
| `.claude/skills/xinyu-mission-clone/SKILL.md` | 新增 | 子 skill：copy-mundo 一键克隆 + mundo-query + 遍历 info-save 替换 rewardBoxId |
| `.claude/skills/xinyu-lottery-clone/SKILL.md` | 新增 | 子 skill：tenant-list + tenant-query + 构造新 TenantConfigVO + template-create |
| `.claude/skills/xinyu-act-resource-clone/SKILL.md` | 新增 | 子 skill：act-resource-page + 按 type=7→4 顺序 + configJson 7 项 patch + ruleText 日期替换 |
| `.claude/skills/xinyu-resource-sheet-parser/SKILL.md` | 新增 | 子 skill：调 popo-doc-read + 解析任务/抽奖 sheet + 库存类型映射 |

5 个 skill 同级落在 `.claude/skills/` 下，单仓内零外部新依赖。

## 关键接口

### 跨 skill 数据契约

每个子 skill 在响应末尾输出约定 JSON 块（用 ` ```json ... ``` ` 包裹），主 skill 解析。

**xinyu-mission-clone 返回**：
```json
{
  "skill": "xinyu-mission-clone",
  "success": true,
  "newMissionActivityId": 22095440,
  "boxIdMapping": {"9679761": "9679800"},
  "successCount": 3,
  "events": [
    {"level": "warn", "path": "iOS复购6.1-6.10 → 主任务A → 任务组1 → 子任务签到", "reason": "sheet 中无任务名 签到 的记录"}
  ]
}
```

**xinyu-lottery-clone 返回**：
```json
{
  "skill": "xinyu-lottery-clone",
  "success": true,
  "tenantIdMapping": {"601111": "601120"},
  "tokenMapping": {"zTklK30nLX2t3Fs8Yd8z31cUe": "aBcdEfGhIjKlMnOpQrStUvWxY"},
  "interestIdMapping": {"2003754": "2003800"},
  "successCount": 1,
  "events": []
}
```

**xinyu-act-resource-clone 返回**：
```json
{
  "skill": "xinyu-act-resource-clone",
  "success": true,
  "taskPlayIdMapping": {"844501": "844601"},
  "successCount": 2,
  "events": []
}
```

**xinyu-resource-sheet-parser 返回**：
```json
{
  "skill": "xinyu-resource-sheet-parser",
  "success": true,
  "missionEntries": [
    {"missionName": "签到", "rewardBoxId": "8439053"}
  ],
  "lotteryEntries": [
    {
      "interestId": 2003754,
      "awards": [
        {"rewardBoxId": "8440046", "baseWeight": 0, "floorWeight": 0, "cheatWeight": 0, "isLose": false, "inventoryType": 4, "inventoryNum": 0}
      ]
    }
  ],
  "errors": []
}
```

### mws 调用模板

所有 mws 调用通过 Bash 工具执行，统一格式：
```bash
mws moyi-activity-backend <method> --env <online|test> --params '<json>' --format json
```

涉及的 12 个 method：`plan-list / plan-create / panel-list / list / mundo-query / info-save / tenant-list / tenant-query / template-create / act-resource-page / act-resource-create / copy-mundo`

**关键参数注意**：
- `copy-mundo`：`activityId` = 源活动 ID（被克隆的，后端从该活动读取 mundo 树），`aimActivityId` = 新活动 ID（克隆目标，后端自动创建 mundo 骨架并写入）。**注意：mws schema 描述有误，以源码为准。**
- `act-resource-create`：返回 boolean，不返回新 ID。创建后需反查 `act-resource-page` 获取新资源 ID。
- `template-create`：返回完整 TenantConfigVO（含新 tenantId / token），可直接提取映射。
- `tenant-list` / `act-resource-page`：分页接口，需循环翻页确保拉完所有数据。

### POPO bot 与 skill 的契约

POPO bot 服务在收到运营消息后，调用本仓的 `xinyu-plan-clone` skill 时需注入以下上下文：
- 环境变量 `MWS_DS_TOKEN`（公共账号 token，由 bot 服务统一管理）
- 消息文本（含运营触发语 / 后续回复）
- 回复回调（skill 可调用此回调向 POPO 发送消息）

具体集成规范由 POPO bot 服务负责，本 skill 不依赖具体 bot 实现。

## 风险与边界

| 风险 | 影响 | 应对 |
|------|------|------|
| **copy-mundo 不在 mws** | 高 — 决策 3 首选方案不可用 | 实施前 verify mws 暴露状态；若仍未暴露：推 mws 团队补；同时实现 fallback 路径（mundo-query + 逐 mission info-save 手工构造） |
| **mundo-save 不在 mws** | 高 — fallback 路径也不可用 | 与上同时推动 mws 团队补；最坏情况本期无法做任务模块复制，主 skill 跳过该模块 + 全部任务记入兜底通知 |
| **popo-doc-read 解析 sheet 能力不足** | 高 — 决策 4 第一阶段不可用 | design 阶段必须实测：拿真实运营表格跑 popo-doc-read 看返回结构；若不可解析多 sheet/表头跨行/单元格特殊字符，启动 popo-sheet-read 新建 |
| **多奖池场景未覆盖** | 中 — iOS 复购单奖池暂不阻塞 | 本期 spec 已留 [F6 待 design 细化] 标记；MVP 仅保证单奖池正确，多奖池时记入兜底事件并提示运营人工处理 |
| **probType=11 等其他动态档位** | 低 — 当前 sheet 仅覆盖 9/10/50 | 若运营反馈某些活动用了升级档位（如 probType=11），design 阶段可扩展 sheet 列（"升级权重"）+ 对应 probMap key |
| **plan-create 时间提前量校验拒绝** | 中 — 运营选当日活动会被拒 | 把 mws 报错原样反馈给运营，提示重新选日期；不预先内嵌该值（mws 未暴露 domain-module-list 取值入口） |
| **mission.tenantId 跨期混乱** | 中 — 本期决策 2 不映射，新活动任务可能指向源奖池 | iOS 复购系列实施前用 mundo-query 抽查源 mission.tenantId 是否非空；若全为空（不耦合奖池）则风险消除；若非空需重新评估是否本期补 tenantId 映射 |
| **会话超时 + 中途取消导致脏数据** | 中 — 新 plan 已建但模块未填全 | 主 skill 兜底通知中明确告知"请运营手动清理 plan id=X"；不自动删（mws 未暴露 plan-delete） |
| **LLM 意图识别误触发** | 低 — 运营随口聊天可能误进流程 | 在意图识别 prompt 中加严格判定标准（必须含"创建" + "活动/计划"双关键词类）；首轮追问二选一确认 |
| **抽奖 sheet 列名容错性** | 低 — 运营改了列名会导致解析失败 | xinyu-resource-sheet-parser 在 SKILL.md 中明确 9 个必需列名；解析失败时把"找不到列 X"原样反馈 |

## 实施依赖与验证清单

实施前必须 verify：

1. **mws 暴露状态**：`mws schema moyi-activity-backend.copy-mundo` 和 `mws schema moyi-activity-backend.mundo-save` 任一可用
2. **popo-doc-read 实测**：拿一份运营真实 POPO 在线表格链接跑一遍，记录解析能力边界
3. **iOS 复购系列 mission.tenantId 真实情况**：调 mundo-query 抽查源 mission，确认 tenantId 是否非空，决定是否本期补 tenantId 映射

实施过程中持续验证：

4. **plan-create 时间提前量** N 分钟的实际值（首次报错时观察）
5. **多奖池场景**（如有实际心遇业务用例）
6. **ruleText 日期识别全部 7 种格式** 在 iOS 复购真实历史数据上的覆盖率
