## ADDED Requirements

### Requirement: Facebook Graph API 封装 — 发帖、回复评论、获取帖子列表

#### Scenario: fb_post 发帖成功
- **WHEN** Agent 调用 `fb_post`，传入有效的 `account_id`、非空 `message`
- **THEN** 调用 Graph API `POST /{page_id}/feed`，返回 `{"ok": true, "data": {"post_id": "...", "url": "https://www.facebook.com/..."}}`

#### Scenario: fb_post 附带链接
- **WHEN** Agent 传入可选的 `link` 参数
- **THEN** 帖子附带链接预览发出，link 字段包含在 Graph API 请求中

#### Scenario: fb_post 内容为空时拒绝
- **WHEN** `message` 为空字符串或仅含空白
- **THEN** 返回 `{"ok": false, "error": "INVALID_PARAMS", "message": "message must not be empty"}`，不调用 API

#### Scenario: page_access_token 过期时返回 AUTH_EXPIRED
- **WHEN** Graph API 返回 token 过期错误（error code 190）
- **THEN** 返回 `{"ok": false, "error": "AUTH_EXPIRED", "message": "page_access_token expired, please refresh in Facebook Developer Console"}`

#### Scenario: fb_reply_comment 回复评论成功
- **WHEN** Agent 调用 `fb_reply_comment`，传入有效 `account_id`、`comment_id`、非空 `message`
- **THEN** 调用 Graph API `POST /{comment_id}/comments`，返回 `{"ok": true, "data": {"reply_id": "..."}}`

#### Scenario: fb_reply_comment 目标评论不存在
- **WHEN** `comment_id` 对应的评论不存在或已删除
- **THEN** 返回 `{"ok": false, "error": "NOT_FOUND", "message": "Comment <id> not found"}`

#### Scenario: fb_get_posts 获取帖子列表成功
- **WHEN** Agent 调用 `fb_get_posts`，传入有效 `account_id`
- **THEN** 调用 Graph API `GET /{page_id}/posts?fields=id,message,created_time,comments.summary(true)`，返回帖子列表，每条包含 `post_id`、`message`、`created_time`、`comments_count`

#### Scenario: fb_get_posts 无帖子时返回空列表
- **WHEN** 该主页暂无帖子
- **THEN** 返回 `{"ok": true, "data": {"posts": []}}`，不报错
