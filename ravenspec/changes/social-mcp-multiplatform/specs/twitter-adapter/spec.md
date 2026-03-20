## ADDED Requirements

### Requirement: X API v2 封装 — 发推文与回复推文

#### Scenario: x_post 发推文成功
- **WHEN** Agent 调用 `x_post`，传入有效 `account_id`、不超过 280 字符的 `text`
- **THEN** 调用 X API v2 `POST /2/tweets`，返回 `{"ok": true, "data": {"tweet_id": "...", "url": "https://x.com/i/web/status/..."}}`

#### Scenario: x_post 内容超过 280 字符时拒绝
- **WHEN** `text` 长度超过 280 字符
- **THEN** 返回 `{"ok": false, "error": "CONTENT_TOO_LONG", "message": "text exceeds 280 characters (got <N>)"}`, 不调用 API

#### Scenario: x_post 月度配额耗尽时返回限流错误
- **WHEN** X API 返回 429 或月度写入配额耗尽错误
- **THEN** 返回 `{"ok": false, "error": "RATE_LIMITED", "message": "Monthly tweet quota exhausted for account <id>"}`

#### Scenario: x_reply 回复推文成功
- **WHEN** Agent 调用 `x_reply`，传入有效 `account_id`、有效 `tweet_id`、不超过 280 字符的 `text`
- **THEN** 调用 X API v2 `POST /2/tweets`（附带 `reply.in_reply_to_tweet_id`），返回 `{"ok": true, "data": {"reply_tweet_id": "...", "url": "https://x.com/i/web/status/..."}}`

#### Scenario: x_reply 目标推文不存在
- **WHEN** `tweet_id` 对应推文不存在或已被删除
- **THEN** 返回 `{"ok": false, "error": "NOT_FOUND", "message": "Tweet <id> not found or deleted"}`

#### Scenario: x_reply 内容超过 280 字符时拒绝
- **WHEN** `text` 长度超过 280 字符
- **THEN** 返回 `{"ok": false, "error": "CONTENT_TOO_LONG", "message": "text exceeds 280 characters (got <N>)"}`, 不调用 API

#### Scenario: X token 过期时返回 AUTH_EXPIRED
- **WHEN** X API 返回 401 Unauthorized
- **THEN** 返回 `{"ok": false, "error": "AUTH_EXPIRED", "message": "X access token expired for account <id>, please refresh"}`

#### Scenario: tweet_id 来源说明（文档约定）
- **WHEN** Agent 需要调用 `x_reply`
- **THEN** Agent 侧需通过外部渠道获取 `tweet_id`（如用户手动提供、Webhook 通知、或其他系统传入）；MCP 不提供主动拉取 mention 的能力（X 免费层限制）
