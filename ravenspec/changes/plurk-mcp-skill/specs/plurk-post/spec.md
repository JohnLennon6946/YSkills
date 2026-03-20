## ADDED Requirements

### Requirement: 发布新帖子到 Plurk
系统必须提供 `plurk_post` MCP Tool，供 AI Agent 调用以向 Plurk 平台发布一条新帖子。

#### Scenario: 发帖成功
- **WHEN** Agent 调用 `plurk_post`，传入非空且不超过 360 字符的 `content`
- **THEN** 返回 `{"ok": true, "data": {"plurk_id": <id>, "url": "<plurk_url>"}}`

#### Scenario: 内容为空时拒绝发帖
- **WHEN** `content` 为空字符串或仅包含空白字符
- **THEN** 返回 `{"ok": false, "error": "INVALID_PARAMS", "message": "content must not be empty"}`，不调用 Plurk API

#### Scenario: 内容超过 360 字符时拒绝发帖
- **WHEN** `content` 长度超过 360 字符
- **THEN** 返回 `{"ok": false, "error": "CONTENT_TOO_LONG", "message": "content exceeds 360 characters (got <N>)"}`，不调用 Plurk API

#### Scenario: 支持自定义 qualifier
- **WHEN** Agent 调用 `plurk_post` 并传入合法的 `qualifier`（如 `says`、`shares`）
- **THEN** 帖子以指定 qualifier 发出；若不传 `qualifier`，默认使用 `:`

#### Scenario: 网络错误时自动重试
- **WHEN** 调用 Plurk API 发帖时发生网络超时或连接错误
- **THEN** 自动重试最多 3 次，每次间隔 5 秒；3 次后仍失败则返回 `{"ok": false, "error": "NETWORK_ERROR", "message": "..."}`

#### Scenario: API 限流时返回限流错误
- **WHEN** Plurk API 返回 429 Too Many Requests
- **THEN** 返回 `{"ok": false, "error": "RATE_LIMITED", "message": "Too many requests, retry after <N>s"}`，不自动重试，由 Agent 决定重试时机
