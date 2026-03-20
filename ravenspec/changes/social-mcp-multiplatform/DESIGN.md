# social-mcp-multiplatform 技术方案

## 方案概述

将现有单账号 Plurk MCP Server 重构为**多平台、多账号**统一架构。核心设计：
- `AccountManager` 统一管理所有账号的 session 池
- `PlatformAdapter` 抽象接口屏蔽各平台 API 差异
- 所有 MCP Tool 通过 `account_id` 参数路由到对应账号的 adapter

新服务路径：`mcp-servers/social/`（原 `mcp-servers/plurk/` 可保留作历史参考）

---

## 关键决策

### 决策 1：账号配置格式 — YAML 文件

**选择**：`accounts.yaml`（git ignored），启动时一次性加载全部账号

**理由**：YAML 可读性好，适合人工维护 100+ 条目；一次加载缓存 session 池，调用时无 IO 开销

```yaml
accounts:
  - id: plurk_001
    platform: plurk
    auth_mode: oauth          # oauth | password
    app_key: xxx
    app_secret: xxx
    access_token: xxx
    access_token_secret: xxx

  - id: plurk_002
    platform: plurk
    auth_mode: password
    username: bot002
    password: xxx

  - id: fb_page_main
    platform: facebook
    page_id: "123456789"
    page_access_token: xxx

  - id: x_account_001
    platform: x
    api_key: xxx
    api_secret: xxx
    access_token: xxx
    access_token_secret: xxx
```

**放弃方案**：SQLite 数据库（增加依赖复杂度）；多个 .env 文件（维护困难）

---

### 决策 2：PlatformAdapter 抽象接口

**选择**：定义 `BaseAdapter` 抽象类，每个平台实现各自的 Adapter，`AccountManager` 维护 `account_id → adapter` 映射

```python
class BaseAdapter(ABC):
    """各平台 Adapter 的统一接口"""
    account_id: str
    platform: str

    @abstractmethod
    def post(self, **kwargs) -> dict: ...          # 发帖（各平台字段不同）
    @abstractmethod
    def reply(self, **kwargs) -> dict: ...         # 回复
    def get_timeline(self, **kwargs) -> dict: ...  # 可选（X 免费层不支持）
```

**理由**：新增平台只需实现 Adapter 并在 `accounts.yaml` 注册，server.py 无需改动

---

### 决策 3：X 回复推文的 tweet_id 来源

**选择**：`x_reply` Tool 直接接受 `tweet_id` 参数，Agent 侧负责提供（外部传入）

**理由**：X 免费层无法主动拉取时间线，tweet_id 必须由外部来源（用户手动、Webhook、或其他系统）提供；MCP 只负责执行回复动作

**放弃方案**：内置轮询（需要付费 Basic 层）

---

### 决策 4：账号初始化失败策略 — 跳过并警告

**选择**：某账号初始化失败时，记录警告日志并跳过，不阻止其他账号初始化；调用该账号时返回 `ACCOUNT_NOT_FOUND` 或 `AUTH_FAILED`

**理由**：100 个账号中个别失效是常态，不应影响整体服务可用性

---

### 决策 5：Facebook Graph API 版本

**选择**：Graph API v21.0，使用 Page Access Token（长期有效 token 由用户预先生成）

**理由**：v21 是当前稳定版；Page Access Token 通过 Facebook Developer Console 生成，有效期 60 天（可配置为永久 token）

**注意**：Page Access Token 过期时返回 `AUTH_EXPIRED`，需用户手动刷新，MCP 不自动刷新

---

## 改动范围

| 文件 | 操作 | 改动内容 |
|------|------|----------|
| `mcp-servers/social/server.py` | 新增 | 统一 MCP Server 主入口，注册全部 12 个 Tools |
| `mcp-servers/social/account_manager.py` | 新增 | 账号池管理，加载 accounts.yaml，维护 account_id → adapter 映射 |
| `mcp-servers/social/adapters/base.py` | 新增 | `BaseAdapter` 抽象接口 |
| `mcp-servers/social/adapters/plurk.py` | 新增 | Plurk Adapter（迁移现有 plurk_client.py + auth.py，支持多账号） |
| `mcp-servers/social/adapters/facebook.py` | 新增 | Facebook Graph API Adapter |
| `mcp-servers/social/adapters/twitter.py` | 新增 | X API v2 Adapter |
| `mcp-servers/social/tools/plurk_*.py` | 新增 | 全部 7 个 Plurk Tools（新增 account_id 参数） |
| `mcp-servers/social/tools/fb_*.py` | 新增 | 3 个 Facebook Tools |
| `mcp-servers/social/tools/x_*.py` | 新增 | 2 个 X Tools（x_post / x_reply） |
| `mcp-servers/social/utils.py` | 新增 | 统一返回格式（复用现有实现） |
| `mcp-servers/social/accounts.yaml.example` | 新增 | 多账号配置模板 |
| `mcp-servers/social/requirements.txt` | 新增 | 依赖（新增 tweepy / requests / pyyaml） |
| `mcp-servers/social/README.md` | 新增 | 部署文档 |
| `.agents/skills/plurk-mcp/SKILL.md` | 修改 | 更新为 social-mcp，新增多账号使用说明 |

---

## 关键接口

### AccountManager

```python
class AccountManager:
    def __init__(self, config_path: str): ...

    def load(self) -> None:
        """加载 accounts.yaml，初始化所有账号 session，跳过失败账号"""

    def get(self, account_id: str) -> BaseAdapter:
        """获取指定账号的 adapter，不存在时抛 AccountNotFoundError"""

    def list_accounts(self) -> list[dict]:
        """返回所有账号的状态列表（id / platform / status）"""
```

### MCP Tools 签名（新增 account_id）

```python
# Plurk
@mcp.tool()
async def plurk_post(account_id: str, content: str, qualifier: str = ":") -> str: ...

@mcp.tool()
async def plurk_reply(account_id: str, plurk_id: int, user_id: int, content: str) -> str: ...

@mcp.tool()
async def plurk_get_timeline(account_id: str, offset: str | None = None, limit: int = 20) -> str: ...

@mcp.tool()
async def plurk_get_responses(account_id: str, plurk_id: int) -> str: ...

@mcp.tool()
async def plurk_delete(account_id: str, plurk_id: int) -> str: ...

@mcp.tool()
async def plurk_like(account_id: str, plurk_id: int) -> str: ...

@mcp.tool()
async def plurk_get_profile(account_id: str, username: str | None = None) -> str: ...

# Facebook
@mcp.tool()
async def fb_post(account_id: str, message: str, link: str | None = None) -> str: ...

@mcp.tool()
async def fb_reply_comment(account_id: str, comment_id: str, message: str) -> str: ...

@mcp.tool()
async def fb_get_posts(account_id: str, limit: int = 10) -> str: ...

# X
@mcp.tool()
async def x_post(account_id: str, text: str) -> str: ...

@mcp.tool()
async def x_reply(account_id: str, tweet_id: str, text: str) -> str: ...
```

### PlurkAdapter

```python
class PlurkAdapter(BaseAdapter):
    """封装单个 Plurk 账号，继承现有 plurk_client 逻辑"""
    def __init__(self, account_id: str, auth_mode: str, **credentials): ...
    def _init_session(self) -> None: ...   # OAuth or password login
    def reauth(self) -> None: ...
    def request(self, method, endpoint, **params) -> dict: ...
    def get_username_by_id(self, user_id: int) -> str | None: ...  # LRU cached
    # 具体 API 方法复用现有实现
```

### FacebookAdapter

```python
class FacebookAdapter(BaseAdapter):
    BASE = "https://graph.facebook.com/v21.0"

    def __init__(self, account_id: str, page_id: str, page_access_token: str): ...

    def post(self, message: str, link: str | None = None) -> dict:
        """POST /{page_id}/feed"""

    def reply_comment(self, comment_id: str, message: str) -> dict:
        """POST /{comment_id}/comments"""

    def get_posts(self, limit: int = 10) -> dict:
        """GET /{page_id}/posts?fields=id,message,created_time,comments.summary(true)"""
```

### TwitterAdapter

```python
class TwitterAdapter(BaseAdapter):
    def __init__(self, account_id: str, api_key: str, api_secret: str,
                 access_token: str, access_token_secret: str): ...

    def post(self, text: str) -> dict:
        """POST /2/tweets"""

    def reply(self, tweet_id: str, text: str) -> dict:
        """POST /2/tweets with reply.in_reply_to_tweet_id"""
```

---

## 依赖

```
mcp>=1.5.0
requests>=2.31.0
requests-oauthlib>=1.3.1
tweepy>=4.14.0          # X API v2 官方 SDK
pyyaml>=6.0.1           # accounts.yaml 解析
python-dotenv>=1.0.0
```

---

## 风险与边界

| 风险 | 影响 | 应对 |
|------|------|------|
| Facebook page_access_token 60 天过期 | 中 | 返回 `AUTH_EXPIRED`，文档说明生成长期 token 的方法 |
| X 免费层月度配额（500 条/账号）耗尽 | 中 | 返回 `RATE_LIMITED`，Agent 记录并跳过；日均 ~16 条，10 账号共 ~160 条/天，正常使用不会触发 |
| Plurk 模拟登录接口变更 | 低 | 优先使用 OAuth；模拟登录仅作补充，失效时返回 `AUTH_FAILED` |
| 100 个账号同时初始化导致启动慢 | 低 | 并发初始化（asyncio.gather），预计 < 30s 完成 |
| accounts.yaml 被意外提交至 git | 高 | .gitignore 排除；启动时 git ls-files 检查并警告 |
