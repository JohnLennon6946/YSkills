# plurk-mcp-skill 实现任务

> 基于 DESIGN.md 拆分 | 创建日期: 2026-03-20

## Phase 1: 基础设施与配置

<!-- Phase 1 全部无依赖，可并行执行 -->

- [x] 1.1 创建项目目录结构：`mcp-servers/plurk/tools/` 子目录，补全 `requirements.txt` 依赖版本（mcp / requests / requests-oauthlib / python-dotenv / beautifulsoup4）
- [x] 1.2 创建 `.env.example` 文件，包含所有认证相关环境变量（`PLURK_AUTH_MODE` / `PLURK_APP_KEY` / `PLURK_APP_SECRET` / `PLURK_ACCESS_TOKEN` / `PLURK_ACCESS_TOKEN_SECRET` / `PLURK_USERNAME` / `PLURK_PASSWORD`）
- [x] 1.3 将 `mcp-servers/plurk/.env` 加入 `.gitignore`
- [x] 1.4 定义统一返回格式工具函数 `ok(data)` / `err(code, message)` 至 `mcp-servers/plurk/utils.py`

## Phase 2: 认证模块

- [x] 2.1 实现 `auth.py`：OAuth 1.0a 认证模式，读取环境变量，构造 `requests_oauthlib.OAuth1Session`，验证 token 有效性 `blockedBy: 1.1, 1.2`
- [x] 2.2 实现 `auth.py`：账号密码模拟登录模式，通过 `requests.Session` POST 至 Plurk 登录接口，缓存 session cookie `blockedBy: 1.1, 1.2`
- [x] 2.3 实现 `auth.py`：认证模式路由逻辑（根据 `PLURK_AUTH_MODE` 选择对应认证方式）+ `.env` git 追踪安全检查警告 `blockedBy: 2.1, 2.2`

## Phase 3: PlurkClient 核心封装

- [x] 3.1 实现 `plurk_client.py`：`PlurkClient` 基础结构，统一 `request()` 方法，含网络重试逻辑（最多 3 次，间隔 5s）和 HTTP 错误码映射（401/403/404/429） `blockedBy: 2.3`
- [x] 3.2 实现 `plurk_client.py`：session/token 过期自动重新认证逻辑（检测到 401 时触发重认证，重试原请求最多 1 次） `blockedBy: 3.1`
- [x] 3.3 实现 `plurk_client.py`：`get_username_by_id()` 方法，调用 `/APP/Users/getPublicProfile` 解析 nick_name，结果存入 `functools.lru_cache(maxsize=500)` `blockedBy: 3.1`

## Phase 4: MCP Tools 实现

- [x] 4.1 实现 `tools/post.py`：`plurk_post` Tool，含参数校验（空内容、360 字符限制）和 `PlurkClient.add_plurk()` 调用 `blockedBy: 3.1`
- [x] 4.2 实现 `tools/reply.py`：`plurk_reply` Tool，调用 `get_username_by_id()` 拼接 `@nick_name`，含降级处理（username_fallback） `blockedBy: 3.1, 3.3`
- [x] 4.3 实现 `tools/timeline.py`：`plurk_get_timeline` Tool，支持 `offset` 分页和 `limit` 参数 `blockedBy: 3.1`
- [x] 4.4 实现 `tools/responses.py`：`plurk_get_responses` Tool `blockedBy: 3.1`
- [x] 4.5 实现 `tools/delete.py`：`plurk_delete` Tool `blockedBy: 3.1`
- [x] 4.6 实现 `tools/profile.py`：`plurk_get_profile` Tool，支持传入 username 或默认查询当前账号 `blockedBy: 3.1`
- [x] 4.7 实现 `tools/like.py`：`plurk_like` Tool，含重复点赞静默处理 `blockedBy: 3.1`

## Phase 5: MCP Server 主入口与文档

- [x] 5.1 实现 `server.py`：MCP Server 主入口，注册全部 7 个 Tools，stdio 传输模式，启动时初始化认证并校验配置完整性 `blockedBy: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7`
- [x] 5.2 编写 `mcp-servers/plurk/README.md`：本地环境安装步骤、启动命令、OpenClaw 配置示例 `blockedBy: 5.1`
- [x] 5.3 编写 `.agents/skills/plurk-mcp/SKILL.md`：OpenClaw Agent 接入文档，含环境变量说明、认证模式选择指引、定时发帖和自动回复完整调用链示例、error code 处理建议 `blockedBy: 5.1`

## Phase 6: 集成验证

- [ ] 6.1 本地端到端验证：启动 MCP Server，通过 MCP Inspector 或 curl 测试 `plurk_post` 发帖成功并返回 plurk_id `blockedBy: 5.1`
- [ ] 6.2 验证 `plurk_reply`：传入有效 plurk_id 和 user_id，确认 @ 用户名正确拼接并发送成功 `blockedBy: 5.1`
- [ ] 6.3 验证 `plurk_get_timeline` + `plurk_get_responses` 返回结构符合 spec 定义字段 `blockedBy: 5.1`
- [ ] 6.4 验证错误场景：空内容发帖、越权删除、user_id 不存在的降级处理均返回预期的结构化错误 `blockedBy: 5.1`
- [ ] 6.5 验证双模式认证：分别以 OAuth 和 password 模式启动 Server，确认认证成功且 session 缓存复用正常 `blockedBy: 6.1`
