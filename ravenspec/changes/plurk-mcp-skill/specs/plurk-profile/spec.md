## ADDED Requirements

### Requirement: 获取用户资料
系统必须提供 `plurk_get_profile` MCP Tool，返回指定用户或当前登录账号的基本资料。

#### Scenario: 获取当前登录账号资料
- **WHEN** Agent 调用 `plurk_get_profile`，不传 `username`
- **THEN** 返回当前账号的资料，包含 `user_id`、`nick_name`、`display_name`、`avatar_url`、`fans_count`、`friends_count`、`about`

#### Scenario: 获取指定用户资料
- **WHEN** Agent 调用 `plurk_get_profile`，传入有效的 `username`
- **THEN** 返回该用户的公开资料，字段同上

#### Scenario: 用户不存在时返回错误
- **WHEN** 传入的 `username` 对应用户不存在
- **THEN** 返回 `{"ok": false, "error": "NOT_FOUND", "message": "User <username> not found"}`
