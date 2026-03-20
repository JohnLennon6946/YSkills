# social-mcp-multiplatform 产品需求文档

> 创建日期: 2026-03-20

## 需求概述

在现有 `plurk-mcp-skill` 的基础上，扩展构建一个**多平台、多账号**的统一社交媒体 MCP Server（`social-mcp`），支持 Plurk、Facebook、X（Twitter）三个平台，允许 OpenClaw AI Agent 通过统一的 `account_id` 参数管理并操作多个账号，实现定时自动发帖、AI 生成回复等自动化场景。

---

## 核心功能

### 功能 1：多账号配置管理

**描述**：通过统一的 `accounts.yaml` 文件管理所有平台的所有账号凭据，MCP Server 启动时自动加载并初始化各账号的认证 session。

- **输入**：`accounts.yaml`（git ignored），每条记录包含 `id`（账号唯一标识）、`platform`（plurk / facebook / x）、认证字段
- **输出**：所有账号 session 初始化完成，可通过 `account_id` 调用
- 支持账号数量：Plurk 最多 100 个、Facebook 主页 N 个、X 账号 10 个

**边界条件**：
- 正常：所有账号初始化成功，打印各账号认证状态汇总
- 异常（某账号凭据无效）：跳过该账号并记录警告，不阻止其他账号正常初始化
- 异常（`accounts.yaml` 不存在）：打印 `accounts.yaml.example` 参考说明后退出
- 异常（`account_id` 不存在）：Tool 调用时返回 `{"ok": false, "error": "ACCOUNT_NOT_FOUND", "message": "..."}`

---

### 功能 2：Plurk 发帖（多账号）

**描述**：指定 `account_id` 向对应 Plurk 账号发布新帖子，继承现有 `plurk_post` 逻辑。

- **输入**：`account_id`、`content`（≤360 字符）、`qualifier`（默认 `:`）
- **输出**：`plurk_id`、帖子 URL

---

### 功能 3：Plurk 回复（多账号）

**描述**：指定 `account_id` 以对应 Plurk 账号回复指定帖子，自动 @ 目标用户，继承现有 `plurk_reply` 逻辑。

- **输入**：`account_id`、`plurk_id`、`user_id`、`content`
- **输出**：`response_id`

---

### 功能 4：Plurk 时间线 / 回复列表 / 删帖 / 点赞 / 用户资料（多账号）

**描述**：所有现有 Plurk Tools 均新增 `account_id` 参数，支持多账号操作，逻辑与现有实现相同。

涉及 Tools：`plurk_get_timeline`、`plurk_get_responses`、`plurk_delete`、`plurk_like`、`plurk_get_profile`

---

### 功能 5：Facebook 主页发帖

**描述**：指定 `account_id`（对应某个 Facebook 主页）发布一条新帖子到该主页。

- **接入方式**：Facebook Graph API v21，使用主页的 `page_access_token`
- **输入**：`account_id`、`message`（帖子正文）、可选 `link`（附加链接）
- **输出**：`post_id`、帖子 URL

**边界条件**：
- 正常：发帖成功，返回 post_id
- 异常（token 过期）：返回 `AUTH_EXPIRED` 错误，提示用户刷新 page_access_token
- 异常（内容为空）：返回 `INVALID_PARAMS` 错误

---

### 功能 6：Facebook 主页回复评论

**描述**：指定 `account_id` 对某条主页帖子下的指定评论发布回复。

- **输入**：`account_id`、`comment_id`（目标评论 ID）、`message`（回复正文）
- **输出**：`reply_id`

**边界条件**：
- 正常：回复成功，返回 reply_id
- 异常（comment_id 不存在）：返回 `NOT_FOUND` 错误
- 异常（无权限）：返回 `FORBIDDEN` 错误

---

### 功能 7：Facebook 获取主页帖子列表

**描述**：获取指定主页账号的最新帖子列表，供 Agent 了解动态或决策是否回复评论。

- **输入**：`account_id`、可选 `limit`（默认 10）
- **输出**：帖子列表，每条包含 `post_id`、`message`、`created_time`、`comments_count`

---

### 功能 8：X (Twitter) 发推文（多账号）

**描述**：指定 `account_id` 以对应 X 账号发布一条推文。

- **接入方式**：X API v2，OAuth 1.0a User Context
- **输入**：`account_id`、`text`（≤280 字符）
- **输出**：`tweet_id`、推文 URL
- **本期限制**：不支持读取时间线（X 免费层限制），但支持回复指定推文

**边界条件**：
- 正常：发帖成功，返回 tweet_id
- 异常（内容超过 280 字符）：返回 `CONTENT_TOO_LONG` 错误
- 异常（月度配额耗尽）：返回 `RATE_LIMITED` 错误，提示本月剩余配额为 0
- 异常（token 过期）：返回 `AUTH_EXPIRED` 错误

---

### 功能 9：X (Twitter) 回复推文（多账号）

**描述**：指定 `account_id` 以对应 X 账号回复指定推文。Agent 需提供目标 `tweet_id`（由外部传入，如 Webhook 或用户手动指定）。

- **接入方式**：X API v2 `POST /2/tweets`，附带 `reply.in_reply_to_tweet_id`
- **输入**：`account_id`、`tweet_id`（目标推文 ID）、`text`（≤280 字符）
- **输出**：`reply_tweet_id`、推文 URL
- **说明**：X 免费层不能主动拉取时间线，但可以回复已知 tweet_id 的推文。tweet_id 由 Agent 侧通过其他渠道获取（如用户手动提供、Webhook 通知等）

**边界条件**：
- 正常：回复成功，返回 reply_tweet_id
- 异常（tweet_id 不存在或已删除）：返回 `NOT_FOUND` 错误
- 异常（内容超过 280 字符）：返回 `CONTENT_TOO_LONG` 错误
- 异常（月度配额耗尽）：返回 `RATE_LIMITED` 错误

---

### 功能 10：统一 MCP Server 主入口

**描述**：将所有平台的所有 Tools 注册到同一个 MCP Server，以 stdio 传输模式运行，启动时加载 `accounts.yaml` 并初始化所有账号。

所有 Tool 名称采用 `{platform}_{action}` 命名规范：
- `plurk_post`、`plurk_reply`、`plurk_get_timeline`、`plurk_get_responses`、`plurk_delete`、`plurk_like`、`plurk_get_profile`
- `fb_post`、`fb_reply_comment`、`fb_get_posts`
- `x_post`、`x_reply`

---

## 用户场景

### 场景 1：每日定时多账号跨平台发帖

**操作流程**：
1. OpenClaw scheduler 触发每日发帖任务
2. Agent 生成当天文案（可以为各平台定制）
3. Agent 遍历所有 Plurk 账号（plurk_001 ~ plurk_100），调用 `plurk_post`
4. Agent 调用 `fb_post` 发布到各 Facebook 主页
5. Agent 调用 `x_post` 发布到各 X 账号
6. 汇总所有发帖结果，记录日志

### 场景 2：Facebook 主页自动回复评论

**操作流程**：
1. Agent 调用 `fb_get_posts` 获取最新主页帖子
2. Agent 选取评论数 > 0 的帖子，调用 Facebook Graph API 获取评论列表（通过 `fb_get_posts` 返回的帖子信息中包含评论入口）
3. Agent 基于评论内容生成 AI 回复文案
4. Agent 调用 `fb_reply_comment`，传入 `comment_id` 和生成的回复

### 场景 3：Plurk 多账号自动回复时间线

**操作流程**：（与现有 plurk-mcp-skill 场景相同，新增 `account_id` 参数）

---

## 边界条件

| 场景 | 处理方式 |
|------|----------|
| 某个账号凭据失效 | 该账号 Tool 调用返回 `AUTH_FAILED`，不影响其他账号 |
| `account_id` 不存在 | 返回 `ACCOUNT_NOT_FOUND` 错误 |
| 平台 API 限流 | 返回 `RATE_LIMITED`，由 Agent 控制重试节奏 |
| `accounts.yaml` 中账号超过合理数量（如 Plurk > 200） | 打印警告，仍正常加载 |
| Facebook page_access_token 过期（60 天有效期） | 返回 `AUTH_EXPIRED`，提示用户刷新 token |

---

## 非功能需求

- **多账号并发**：各账号 session 独立存储，互不干扰，支持并发调用不同账号
- **安全性**：`accounts.yaml` 加入 `.gitignore`，启动时检查是否被 git 追踪
- **可扩展性**：新增平台只需实现 `PlatformAdapter` 接口并注册，无需修改 server.py
- **Python 3.10+**，兼容 MCP 标准协议

---

## 非目标（本期不做）

- X 时间线读取（需付费 Basic 层）
- Facebook 私信（Messenger）
- Plurk 媒体附件发帖
- 图形化账号管理界面

---

## Capabilities

### 新增能力

- `social-account-manager`: 多平台多账号配置加载与 session 池管理
- `facebook-adapter`: Facebook Graph API 封装（发帖、回复评论、获取帖子列表）
- `twitter-adapter`: X API v2 封装（发推文）
- `fb-post-tool`: `fb_post` MCP Tool
- `fb-reply-comment-tool`: `fb_reply_comment` MCP Tool
- `fb-get-posts-tool`: `fb_get_posts` MCP Tool
- `x-post-tool`: `x_post` MCP Tool
- `x-reply-tool`: `x_reply` MCP Tool
- `social-mcp-server`: 统一 MCP Server 主入口，注册全部 Tools

### 修改能力（继承自 plurk-mcp-skill）

- `plurk-post`: 新增 `account_id` 参数
- `plurk-reply`: 新增 `account_id` 参数
- `plurk-timeline`: 新增 `account_id` 参数
- `plurk-responses`: 新增 `account_id` 参数
- `plurk-delete`: 新增 `account_id` 参数
- `plurk-like`: 新增 `account_id` 参数
- `plurk-profile`: 新增 `account_id` 参数
- `plurk-auth`: 改为支持多账号 session 池
- `plurk-mcp-server`: 迁移至 social-mcp-server，统一管理
