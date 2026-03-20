# Plurk MCP Server

为 OpenClaw AI Agent 提供 Plurk 平台操作能力的 MCP Server，支持自动发帖、回复、获取时间线等功能。

## 功能

| Tool | 说明 |
|------|------|
| `plurk_post` | 发布新帖子 |
| `plurk_reply` | 回复指定帖子（自动 @ 用户） |
| `plurk_get_timeline` | 获取时间线帖子列表 |
| `plurk_get_responses` | 获取帖子回复列表 |
| `plurk_delete` | 删除自己的帖子 |
| `plurk_get_profile` | 获取用户资料 |
| `plurk_like` | 点赞帖子 |

## 快速开始

### 1. 安装依赖

```bash
cd mcp-servers/plurk
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. 配置认证

```bash
cp .env.example .env
```

编辑 `.env` 文件，选择认证模式并填写对应凭据：

**OAuth 模式（推荐）**：前往 [https://www.plurk.com/API/OAuth](https://www.plurk.com/API/OAuth) 申请 App，获取以下信息：
```
PLURK_AUTH_MODE=oauth
PLURK_APP_KEY=你的 App Key
PLURK_APP_SECRET=你的 App Secret
PLURK_ACCESS_TOKEN=你的 Access Token
PLURK_ACCESS_TOKEN_SECRET=你的 Access Token Secret
```

**账号密码模式**：
```
PLURK_AUTH_MODE=password
PLURK_USERNAME=你的 Plurk 用户名
PLURK_PASSWORD=你的密码
```

### 3. 启动 Server

```bash
python server.py
```

启动成功后会输出：
```
Plurk MCP Server 启动成功，等待调用...
```

## 在 OpenClaw 中配置

在 OpenClaw 的 MCP 配置文件中添加：

```json
{
  "mcpServers": {
    "plurk": {
      "command": "python",
      "args": ["/path/to/mcp-servers/plurk/server.py"],
      "env": {
        "PLURK_AUTH_MODE": "oauth",
        "PLURK_APP_KEY": "...",
        "PLURK_APP_SECRET": "...",
        "PLURK_ACCESS_TOKEN": "...",
        "PLURK_ACCESS_TOKEN_SECRET": "..."
      }
    }
  }
}
```

> **安全提示**：建议通过系统环境变量或 `.env` 文件注入凭据，不要在配置文件中硬编码。

## 错误码说明

| Error Code | 含义 | 建议处理 |
|------------|------|----------|
| `AUTH_FAILED` | 认证失败 | 检查凭据配置 |
| `AUTH_EXPIRED` | Session 过期且重认证失败 | 重启 Server |
| `RATE_LIMITED` | API 限流 | 等待后重试 |
| `NOT_FOUND` | 资源不存在 | 检查 plurk_id / username |
| `FORBIDDEN` | 无操作权限 | 确认是否为本人资源 |
| `INVALID_PARAMS` | 参数校验失败 | 检查参数格式 |
| `CONTENT_TOO_LONG` | 内容超过 360 字符 | 截断后重试 |
| `NETWORK_ERROR` | 网络错误（已重试 3 次） | 检查网络连接 |

## 项目结构

```
mcp-servers/plurk/
├── server.py          # MCP Server 主入口
├── auth.py            # 认证模块（OAuth + 模拟登录）
├── plurk_client.py    # Plurk API 封装层
├── utils.py           # 工具函数（统一返回格式）
├── tools/
│   ├── post.py        # plurk_post
│   ├── reply.py       # plurk_reply
│   ├── timeline.py    # plurk_get_timeline
│   ├── responses.py   # plurk_get_responses
│   ├── delete.py      # plurk_delete
│   ├── profile.py     # plurk_get_profile
│   └── like.py        # plurk_like
├── requirements.txt
├── .env.example
└── README.md
```
