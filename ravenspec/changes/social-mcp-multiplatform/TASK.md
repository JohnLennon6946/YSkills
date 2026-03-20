# social-mcp-multiplatform 实现任务

> 基于 DESIGN.md 拆分 | 创建日期: 2026-03-20

## Phase 1: 基础设施

<!-- Phase 1 全部无依赖，可并行执行 -->

- [ ] 1.1 创建 `mcp-servers/social/` 目录结构（`adapters/`、`tools/` 子目录）及 `requirements.txt`（mcp / requests / requests-oauthlib / tweepy / pyyaml / python-dotenv）
- [ ] 1.2 创建 `mcp-servers/social/accounts.yaml.example`，包含 Plurk（oauth + password）、Facebook、X 四种账号配置示例
- [ ] 1.3 将 `mcp-servers/social/accounts.yaml` 加入 `.gitignore`
- [ ] 1.4 创建 `mcp-servers/social/utils.py`，复用 `mcp-servers/plurk/utils.py` 的 `ok()` / `err()` 实现

## Phase 2: AccountManager 与 Adapter 接口

- [ ] 2.1 实现 `adapters/base.py`：`BaseAdapter` 抽象类，定义 `account_id`、`platform` 属性，以及 `post()`、`reply()` 抽象方法 `blockedBy: 1.1`
- [ ] 2.2 实现 `account_manager.py`：`AccountManager` 类，含 `load()` 方法（解析 yaml、按 platform 分发创建 Adapter）、`get(account_id)` 方法、`accounts.yaml` git 追踪安全检查 `blockedBy: 2.1`
- [ ] 2.3 实现 `account_manager.py`：账号初始化失败跳过逻辑，记录警告日志并将失败账号标记为 `ACCOUNT_INIT_FAILED` `blockedBy: 2.2`

## Phase 3: Platform Adapters 实现

- [ ] 3.1 实现 `adapters/plurk.py`：`PlurkAdapter` 类，将现有 `plurk_client.py` + `auth.py` 逻辑迁移为类实例方法，每个实例独立管理 session 和 `functools.lru_cache(maxsize=500)` 用户名缓存，支持 OAuth 和 password 双模式 `blockedBy: 2.1`
- [ ] 3.2 实现 `adapters/facebook.py`：`FacebookAdapter` 类，封装 Graph API v21.0 的 `post()`（POST /{page_id}/feed）、`reply_comment()`（POST /{comment_id}/comments）、`get_posts()`（GET /{page_id}/posts），含 token 过期（error code 190）→ `AUTH_EXPIRED` 的错误映射 `blockedBy: 2.1`
- [ ] 3.3 实现 `adapters/twitter.py`：`TwitterAdapter` 类，使用 `tweepy.Client`（OAuth 1.0a User Context）封装 `post()`（POST /2/tweets）和 `reply()`（POST /2/tweets with in_reply_to_tweet_id），含 280 字符校验和 429 → `RATE_LIMITED` 映射 `blockedBy: 2.1`

## Phase 4: Plurk Tools（多账号版）

- [ ] 4.1 实现 `tools/plurk_post.py`：新增 `account_id` 参数，通过 AccountManager 路由到 PlurkAdapter，复用现有参数校验逻辑 `blockedBy: 3.1`
- [ ] 4.2 实现 `tools/plurk_reply.py`：新增 `account_id` 参数，LRU 缓存改为从 PlurkAdapter 实例调用 `blockedBy: 3.1`
- [ ] 4.3 实现 `tools/plurk_timeline.py`、`tools/plurk_responses.py`、`tools/plurk_delete.py`、`tools/plurk_like.py`、`tools/plurk_profile.py`：各自新增 `account_id` 参数，路由逻辑同上 `blockedBy: 3.1`

## Phase 5: Facebook Tools

- [ ] 5.1 实现 `tools/fb_post.py`：`fb_post` Tool，含空内容校验，调用 FacebookAdapter.post() `blockedBy: 3.2`
- [ ] 5.2 实现 `tools/fb_reply_comment.py`：`fb_reply_comment` Tool，含空内容校验，调用 FacebookAdapter.reply_comment() `blockedBy: 3.2`
- [ ] 5.3 实现 `tools/fb_get_posts.py`：`fb_get_posts` Tool，调用 FacebookAdapter.get_posts()，空结果返回空列表 `blockedBy: 3.2`

## Phase 6: X Tools

- [ ] 6.1 实现 `tools/x_post.py`：`x_post` Tool，含 280 字符校验，调用 TwitterAdapter.post() `blockedBy: 3.3`
- [ ] 6.2 实现 `tools/x_reply.py`：`x_reply` Tool，含 280 字符校验，调用 TwitterAdapter.reply()，文档说明 tweet_id 需外部传入 `blockedBy: 3.3`

## Phase 7: 统一 MCP Server 主入口与文档

- [ ] 7.1 实现 `server.py`：统一 MCP Server，启动时实例化 AccountManager 并调用 `load()`，注册全部 12 个 Tools，stdio 传输模式 `blockedBy: 4.1, 4.2, 4.3, 5.1, 5.2, 5.3, 6.1, 6.2`
- [ ] 7.2 编写 `mcp-servers/social/README.md`：安装步骤、`accounts.yaml` 配置说明（三平台）、OpenClaw 配置示例、Facebook 长期 token 获取方法 `blockedBy: 7.1`
- [ ] 7.3 更新 `.agents/skills/plurk-mcp/SKILL.md`：改名为 `social-mcp`，新增多账号使用说明（account_id 用法）、Facebook 和 X 场景调用链示例、x_reply 的 tweet_id 来源说明 `blockedBy: 7.1`

## Phase 8: 集成验证

- [ ] 8.1 验证 AccountManager：配置 3 种平台各 1 个账号，启动 Server 确认全部初始化成功并打印状态汇总 `blockedBy: 7.1`
- [ ] 8.2 验证 Plurk 多账号：配置 2 个 Plurk 账号，调用 `plurk_post` 分别以不同 account_id 发帖，确认各自独立发送 `blockedBy: 7.1`
- [ ] 8.3 验证 Facebook：调用 `fb_post` 发帖到主页，`fb_get_posts` 查看帖子，`fb_reply_comment` 回复评论 `blockedBy: 7.1`
- [ ] 8.4 验证 X：调用 `x_post` 发推文，`x_reply` 回复已知 tweet_id 的推文 `blockedBy: 7.1`
- [ ] 8.5 验证错误场景：传入无效 account_id 返回 `ACCOUNT_NOT_FOUND`；某账号凭据失效时不影响其他账号正常调用 `blockedBy: 8.1`
