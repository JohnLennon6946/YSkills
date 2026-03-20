## ADDED Requirements

### Requirement: 回复指定帖子并 @ 目标用户
系统必须提供 `plurk_reply` MCP Tool，接受 `plurk_id`、`user_id`、`content`，自动解析 user_id 对应的用户名并拼接 @ 前缀后发送回复。

#### Scenario: 回复成功
- **WHEN** Agent 调用 `plurk_reply`，传入有效的 `plurk_id`、`user_id` 和非空 `content`
- **THEN** MCP 内部查询 `user_id` 对应的 `nick_name`，以 `@nick_name content` 为正文发送回复，返回 `{"ok": true, "data": {"response_id": <id>}}`

#### Scenario: user_id 对应用户名查询失败时降级处理
- **WHEN** 通过 `user_id` 查询 nick_name 失败（用户不存在或网络错误）
- **THEN** 降级使用 `user_id` 字符串作为 @ 目标（`@<user_id>`），继续发送回复，并在返回中标注 `{"ok": true, "data": {..., "username_fallback": true}}`

#### Scenario: nick_name 查询结果命中缓存
- **WHEN** 同一 `user_id` 在本进程内已被查询过
- **THEN** 直接从 LRU 缓存（上限 500 条）返回 nick_name，不发起新的 API 请求

#### Scenario: plurk_id 不存在时返回错误
- **WHEN** 目标 `plurk_id` 不存在或已被删除
- **THEN** 返回 `{"ok": false, "error": "NOT_FOUND", "message": "Plurk <id> not found"}`，不重试

#### Scenario: 无权限回复时返回错误
- **WHEN** 目标帖子设置了回复限制（如仅好友可回复）且当前账号无权限
- **THEN** 返回 `{"ok": false, "error": "FORBIDDEN", "message": "No permission to reply to this plurk"}`

#### Scenario: 回复内容为空时拒绝发送
- **WHEN** `content` 为空字符串或仅含空白字符
- **THEN** 返回 `{"ok": false, "error": "INVALID_PARAMS", "message": "content must not be empty"}`，不调用 API
