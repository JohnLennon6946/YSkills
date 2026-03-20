## ADDED Requirements

### Requirement: 获取当前账号时间线帖子列表
系统必须提供 `plurk_get_timeline` MCP Tool，返回当前登录账号的时间线帖子列表，供 AI Agent 决策是否进行互动。

#### Scenario: 获取最新时间线成功
- **WHEN** Agent 调用 `plurk_get_timeline`，不传 `offset`
- **THEN** 返回最新最多 20 条帖子，每条包含 `plurk_id`、`owner_id`、`content`、`posted`（ISO 8601）、`response_count`、`qualifier`

#### Scenario: 分页获取时间线
- **WHEN** Agent 调用 `plurk_get_timeline`，传入 `offset`（ISO 8601 时间戳）
- **THEN** 返回该时间点之前最多 20 条帖子

#### Scenario: 自定义每页条数
- **WHEN** Agent 调用 `plurk_get_timeline`，传入 `limit`（1~30 之间的整数）
- **THEN** 返回不超过 `limit` 条帖子

#### Scenario: 时间线为空时返回空列表
- **WHEN** 时间线上暂无帖子
- **THEN** 返回 `{"ok": true, "data": {"plurks": [], "plurk_users": {}}}`，不报错
