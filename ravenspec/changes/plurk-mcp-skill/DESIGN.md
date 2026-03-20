# plurk-mcp-skill 技术方案

## 方案概述

基于 Python MCP SDK 构建一个 Plurk MCP Server，将 Plurk 平台的操作能力封装为标准 MCP Tools，供 OpenClaw AI Agent 调用。认证层支持 OAuth 1.0a 和账号密码模拟登录双模式，运行时凭据通过 `.env` 注入，session/token 在进程内缓存复用。

---

## 关键决策

### 决策 1：MCP 框架选型

**选择**：使用官方 `mcp` Python SDK（`pip install mcp`），以 `stdio` 传输模式运行

**理由**：
- 官方 SDK 维护稳定，与 OpenClaw 等主流 Agent 框架的 MCP 客户端兼容性最佳
- `stdio` 模式部署最简单，Agent 直接通过子进程启动 MCP Server，无需额外网络配置
- 无需自行实现 MCP 协议层，聚焦业务逻辑

**备选**：
- 自行实现 MCP JSON-RPC Server（复杂度高，维护成本大，放弃）
- HTTP/SSE 传输模式（适合远程部署，但本期场景是本地 Agent 调用，暂不需要，后续可扩展）

---

### 决策 2：Plurk 接入方式——双模式认证

**选择**：同时支持 OAuth 1.0a（官方 API）和账号密码模拟登录，通过环境变量 `PLURK_AUTH_MODE` 切换

**理由**：
- OAuth 模式使用 Plurk 官方 API（`https://www.plurk.com/API/`），稳定且有速率限制保障，适合长期生产运行
- 模拟登录模式通过 `requests.Session` + cookie 维持会话，适合无法申请 OAuth App 的快速接入场景
- 两种模式共享同一套 Tool 接口，上层调用方无感知

**备选**：
- 只做 OAuth 模式（限制了灵活性，放弃）
- 只做模拟登录（不稳定，平台变更易失效，作为补充而非主力）

---

### 决策 3：session/token 缓存策略

**选择**：进程内内存缓存（`_session` 单例），启动时完成认证，过期后自动重新认证

**理由**：
- MCP Server 通常以长进程运行，进程内缓存性能最优，无需引入外部存储
- OAuth token 通常有效期较长（Plurk access token 不过期），内存缓存足够
- 模拟登录 session cookie 在会话内有效，进程重启时自动重新登录

**备选**：
- 持久化 token 到本地文件（增加复杂度，且有 token 泄露风险，放弃）
- 每次调用都重新认证（性能差，放弃）

---

### 决策 4：回复帖子的 @ 用户名解析

**选择**：`plurk_reply` Tool 接受 `user_id`，MCP 内部调用 `/APP/Users/getPublicProfile` 查询 `nick_name`，拼接 `@nick_name content` 后发送回复

**理由**：
- Agent 通过 `plurk_get_timeline` / `plurk_get_responses` 获取的数据中包含 `user_id`，直接传入更自然
- 由 MCP 统一做 user_id → username 的解析，避免每个 Agent 都重复实现此逻辑
- nick_name 查询结果可在进程内 LRU 缓存（上限 500 条），避免频繁重复查询

**备选**：
- 由 Agent 自行传入 username（增加 Agent 侧复杂度，放弃）
- 直接用 user_id 而非 @ username（不符合 Plurk 平台回复习惯，放弃）

---

### 决策 5：错误处理统一规范

**选择**：所有 Tool 返回统一的结构化结果，成功时返回 `{"ok": true, "data": {...}}`，失败时返回 `{"ok": false, "error": "ERROR_CODE", "message": "..."}`

**理由**：
- Agent 侧可以通过 `ok` 字段快速判断是否成功，无需解析异常
- 结构化的 `error` code 方便 Agent 做分支决策（如区分限流错误和认证错误）
- 与 MCP Tool 规范兼容，通过返回文本内容而非抛异常来传递错误

**备选**：
- 直接抛 Python 异常（MCP SDK 会将异常序列化为错误响应，但 Agent 侧解析不便，放弃）

---

## 改动范围

| 文件 | 操作 | 改动内容 |
|------|------|----------|
| `mcp-servers/plurk/server.py` | 新增 | MCP Server 主入口，注册所有 Tools |
| `mcp-servers/plurk/auth.py` | 新增 | 认证模块，OAuth + 模拟登录双模式，session 缓存 |
| `mcp-servers/plurk/plurk_client.py` | 新增 | Plurk API 封装层，含重试逻辑和统一错误处理 |
| `mcp-servers/plurk/tools/post.py` | 新增 | `plurk_post` Tool 实现 |
| `mcp-servers/plurk/tools/reply.py` | 新增 | `plurk_reply` Tool 实现（含 user_id → username 解析） |
| `mcp-servers/plurk/tools/timeline.py` | 新增 | `plurk_get_timeline` Tool 实现 |
| `mcp-servers/plurk/tools/responses.py` | 新增 | `plurk_get_responses` Tool 实现 |
| `mcp-servers/plurk/tools/delete.py` | 新增 | `plurk_delete` Tool 实现 |
| `mcp-servers/plurk/tools/profile.py` | 新增 | `plurk_profile` Tool 实现 |
| `mcp-servers/plurk/tools/like.py` | 新增 | `plurk_like` Tool 实现 |
| `mcp-servers/plurk/requirements.txt` | 修改 | 补全依赖版本 |
| `mcp-servers/plurk/.env.example` | 新增 | 环境变量配置模板 |
| `mcp-servers/plurk/README.md` | 新增 | 本地部署说明 |
| `.agents/skills/plurk-mcp/SKILL.md` | 新增 | OpenClaw Agent 接入文档 |

---

## 关键接口

### MCP Tools 签名（Python）

```python
# 发布新帖子
@mcp.tool()
async def plurk_post(content: str, qualifier: str = ":") -> str:
    """发布一条新 Plurk 帖子。qualifier 可选值: : says shares likes wishes needs wants has will asks hopes thinks is"""

# 回复帖子
@mcp.tool()
async def plurk_reply(plurk_id: int, user_id: int, content: str) -> str:
    """回复指定帖子，自动 @ 目标用户。user_id 从 timeline/responses 结果中获取"""

# 获取时间线
@mcp.tool()
async def plurk_get_timeline(offset: str | None = None, limit: int = 20) -> str:
    """获取时间线帖子列表。offset 为 ISO 8601 时间戳，用于分页"""

# 获取帖子回复列表
@mcp.tool()
async def plurk_get_responses(plurk_id: int) -> str:
    """获取指定帖子的所有回复"""

# 删除帖子
@mcp.tool()
async def plurk_delete(plurk_id: int) -> str:
    """删除当前账号的指定帖子"""

# 获取用户资料
@mcp.tool()
async def plurk_get_profile(username: str | None = None) -> str:
    """获取用户资料。不传 username 则返回当前登录账号资料"""

# 点赞帖子
@mcp.tool()
async def plurk_like(plurk_id: int) -> str:
    """点赞指定帖子"""
```

### 统一返回格式

```python
# 成功
{"ok": True, "data": {"plurk_id": 12345678, "url": "https://www.plurk.com/p/xxxxxx"}}

# 失败
{"ok": False, "error": "RATE_LIMITED", "message": "Too many requests, retry after 60s"}
{"ok": False, "error": "AUTH_FAILED", "message": "Invalid credentials"}
{"ok": False, "error": "NOT_FOUND", "message": "Plurk 12345678 not found"}
{"ok": False, "error": "FORBIDDEN", "message": "No permission to delete this plurk"}
{"ok": False, "error": "INVALID_PARAMS", "message": "content must not be empty"}
{"ok": False, "error": "CONTENT_TOO_LONG", "message": "content exceeds 360 characters (got 400)"}
```

### 认证配置（.env）

```bash
# 认证模式：oauth 或 password
PLURK_AUTH_MODE=oauth

# OAuth 模式（向 https://www.plurk.com/API/OAuth 申请）
PLURK_APP_KEY=
PLURK_APP_SECRET=
PLURK_ACCESS_TOKEN=
PLURK_ACCESS_TOKEN_SECRET=

# 账号密码模式
PLURK_USERNAME=
PLURK_PASSWORD=
```

### PlurkClient 核心结构

```python
class PlurkClient:
    BASE_URL = "https://www.plurk.com/APP"

    def __init__(self, auth_mode: str): ...

    async def request(self, method: str, endpoint: str, **params) -> dict:
        """统一请求入口，含重试（最多3次，间隔5s）和 token 过期自动重新认证"""

    async def add_plurk(self, content: str, qualifier: str) -> dict: ...
    async def response_plurk(self, plurk_id: int, content: str) -> dict: ...
    async def get_plurks(self, offset: str | None, limit: int) -> dict: ...
    async def get_responses(self, plurk_id: int) -> dict: ...
    async def delete_plurk(self, plurk_id: int) -> dict: ...
    async def get_public_profile(self, username: str) -> dict: ...
    async def get_own_profile(self) -> dict: ...
    async def mute_plurk(self, plurk_id: int) -> dict: ...  # 用于点赞

    # LRU 缓存，user_id → nick_name
    @functools.lru_cache(maxsize=500)
    async def get_username_by_id(self, user_id: int) -> str: ...
```

---

## 风险与边界

| 风险 | 影响 | 应对 |
|------|------|------|
| Plurk 模拟登录接口变更导致失效 | 中 | 优先使用 OAuth 模式；模拟登录作为降级方案，失效时记录错误并提示切换 OAuth |
| Plurk API 速率限制触发（官方未公开具体限制） | 中 | 捕获 429 响应，返回 `RATE_LIMITED` 错误，由 Agent 控制重试节奏 |
| user_id → nick_name 查询失败（用户注销/改名） | 低 | 查询失败时回退到直接使用 `user_id` 作为 @ 目标，并在返回中标注 `username_fallback: true` |
| 认证凭据泄露 | 高 | `.env` 文件加入 `.gitignore`，`README.md` 明确警告；`server.py` 启动时检查 `.env` 是否被 git track |
| MCP SDK 版本升级导致 API 变更 | 低 | 锁定 `requirements.txt` 中 mcp 版本，升级需手动测试 |
