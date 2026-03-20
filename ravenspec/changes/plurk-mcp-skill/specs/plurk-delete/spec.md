## ADDED Requirements

### Requirement: 删除当前账号的帖子
系统必须提供 `plurk_delete` MCP Tool，允许 Agent 删除当前登录账号发布的指定帖子。

#### Scenario: 删除成功
- **WHEN** Agent 调用 `plurk_delete`，传入属于当前账号的有效 `plurk_id`
- **THEN** 返回 `{"ok": true, "data": {"plurk_id": <id>, "deleted": true}}`

#### Scenario: 尝试删除他人帖子时返回权限错误
- **WHEN** 指定的 `plurk_id` 属于其他用户
- **THEN** 返回 `{"ok": false, "error": "FORBIDDEN", "message": "No permission to delete this plurk"}`，不执行删除

#### Scenario: 帖子不存在时返回错误
- **WHEN** 指定的 `plurk_id` 不存在或已被删除
- **THEN** 返回 `{"ok": false, "error": "NOT_FOUND", "message": "Plurk <id> not found"}`
