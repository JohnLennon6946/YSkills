---
name: plurk-mcp
description: 通过 Plurk MCP Server 操作 Plurk 平台，支持自动发帖、回复时间线帖子、获取动态等功能，适合 OpenClaw AI Agent 定时发帖和自动互动场景。
---

# Plurk MCP Skill

## 概述

本 Skill 让 AI Agent 能够通过 MCP 协议与 Plurk 社交平台交互，支持：
- 每日定时自动发帖
- 获取时间线，筛选需要回复的帖子
- 基于上下文 AI 生成回复文案并发送
- 点赞、查看用户资料、删除帖子

## 前置配置

### 1. 启动 MCP Server

```bash
cd mcp-servers/plurk
pip install -r requirements.txt
cp .env.example .env   # 填写认证凭据
python server.py
```

### 2. 在 OpenClaw 中注册 MCP Server

```json
{
  "mcpServers": {
    "plurk": {
      "command": "python",
      "args": ["/absolute/path/to/mcp-servers/plurk/server.py"]
    }
  }
}
```

### 3. 认证模式选择

| 模式 | 适用场景 | 稳定性 |
|------|----------|--------|
| `oauth`（推荐） | 有条件申请 Plurk App | 高，官方支持 |
| `password` | 快速接入，无需申请 App | 中，依赖模拟登录 |

申请 OAuth App：[https://www.plurk.com/API/OAuth](https://www.plurk.com/API/OAuth)

---

## 场景一：每日定时自动发帖

**调用链**：OpenClaw Scheduler → 生成文案 → `plurk_post`

```
# Step 1: 由 Agent 生成当天的帖子内容
content = "<AI 生成的帖子文案>"

# Step 2: 调用 plurk_post
plurk_post(content=content, qualifier=":")

# Step 3: 处理返回结果
# 成功：{"ok": true, "data": {"plurk_id": 123456, "url": "https://www.plurk.com/p/xxxxx"}}
# 失败：{"ok": false, "error": "CONTENT_TOO_LONG", "message": "..."}
```

**注意**：
- 帖子内容不超过 360 字符
- MCP 不内置定时器，调度由 OpenClaw scheduler 负责

---

## 场景二：自动回复时间线帖子

**调用链**：`plurk_get_timeline` → 筛选 → `plurk_get_responses` → 生成回复 → `plurk_reply`

```
# Step 1: 获取最新时间线
plurk_get_timeline(limit=20)
# 返回: {"ok": true, "data": {"plurks": [...], "plurk_users": {...}}}
# 每条 plurk 包含：plurk_id, owner_id, content, posted, response_count

# Step 2: 选取需要回复的帖子（Agent 自行决策）
target_plurk_id = <选中的 plurk_id>
target_owner_id = <该帖子的 owner_id>

# Step 3: 获取帖子现有回复，了解上下文
plurk_get_responses(plurk_id=target_plurk_id)
# 返回: {"ok": true, "data": {"responses": [...], "response_users": {...}}}

# Step 4: Agent 根据帖子内容和回复上下文生成回复文案
reply_content = "<AI 生成的回复文案>"

# Step 5: 发送回复（自动 @ 目标用户）
plurk_reply(plurk_id=target_plurk_id, user_id=target_owner_id, content=reply_content)
# 返回: {"ok": true, "data": {"response_id": 789}}
```

---

## 错误处理建议

| Error Code | 含义 | Agent 建议行为 |
|------------|------|----------------|
| `AUTH_FAILED` | 认证凭据无效 | 停止任务，通知用户检查 `.env` 配置 |
| `AUTH_EXPIRED` | Session 过期且重认证失败 | 尝试重启 MCP Server |
| `RATE_LIMITED` | API 请求过频 | 等待 60s 后重试；减少调用频率 |
| `NOT_FOUND` | 帖子或用户不存在 | 跳过该条目，继续处理下一条 |
| `FORBIDDEN` | 无权限（如删除他人帖子） | 记录日志，不重试 |
| `INVALID_PARAMS` | 参数校验失败 | 检查 content 是否为空 |
| `CONTENT_TOO_LONG` | 内容超 360 字符 | 截断内容后重试 |
| `NETWORK_ERROR` | 网络错误（已重试 3 次） | 等待网络恢复后重试整个任务 |
| `username_fallback: true` | user_id 解析用户名失败，已用 ID 代替 | 可接受，正常继续 |

---

## 可用 Tools 一览

| Tool | 必填参数 | 可选参数 | 返回 |
|------|----------|----------|------|
| `plurk_post` | `content` | `qualifier` | `plurk_id`, `url` |
| `plurk_reply` | `plurk_id`, `user_id`, `content` | — | `response_id` |
| `plurk_get_timeline` | — | `offset`, `limit` | `plurks[]`, `plurk_users` |
| `plurk_get_responses` | `plurk_id` | — | `responses[]`, `response_users` |
| `plurk_delete` | `plurk_id` | — | `deleted` |
| `plurk_get_profile` | — | `username` | 用户资料 |
| `plurk_like` | `plurk_id` | — | `liked` |
