## ADDED Requirements

### Requirement: 点赞指定帖子
系统必须提供 `plurk_like` MCP Tool，对指定帖子执行点赞操作。

#### Scenario: 点赞成功
- **WHEN** Agent 调用 `plurk_like`，传入有效的 `plurk_id`
- **THEN** 返回 `{"ok": true, "data": {"plurk_id": <id>, "liked": true}}`

#### Scenario: 帖子不存在时返回错误
- **WHEN** 指定的 `plurk_id` 不存在或已被删除
- **THEN** 返回 `{"ok": false, "error": "NOT_FOUND", "message": "Plurk <id> not found"}`

#### Scenario: 重复点赞时静默成功
- **WHEN** 当前账号已对该帖子点过赞，再次调用 `plurk_like`
- **THEN** 返回 `{"ok": true, "data": {"plurk_id": <id>, "liked": true, "already_liked": true}}`，不报错
