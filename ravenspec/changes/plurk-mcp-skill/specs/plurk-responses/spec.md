## ADDED Requirements

### Requirement: 获取指定帖子的回复列表
系统必须提供 `plurk_get_responses` MCP Tool，返回指定帖子下的所有回复，供 AI Agent 了解上下文后生成更合适的回复文案。

#### Scenario: 获取回复列表成功
- **WHEN** Agent 调用 `plurk_get_responses`，传入有效的 `plurk_id`
- **THEN** 返回该帖子的所有回复列表，每条包含 `response_id`、`user_id`、`content`、`posted`（ISO 8601）

#### Scenario: 帖子下无回复时返回空列表
- **WHEN** 指定帖子存在但尚无任何回复
- **THEN** 返回 `{"ok": true, "data": {"responses": [], "response_users": {}}}`，不报错

#### Scenario: plurk_id 不存在时返回错误
- **WHEN** 指定的 `plurk_id` 不存在或已被删除
- **THEN** 返回 `{"ok": false, "error": "NOT_FOUND", "message": "Plurk <id> not found"}`
