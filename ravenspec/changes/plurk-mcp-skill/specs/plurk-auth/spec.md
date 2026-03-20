## ADDED Requirements

### Requirement: 支持 OAuth 1.0a 认证
系统必须支持通过 Plurk 官方 OAuth 1.0a 协议完成认证，并将 access token 缓存于进程内以供复用。

#### Scenario: OAuth 认证成功
- **WHEN** 环境变量中配置了有效的 `PLURK_APP_KEY` / `PLURK_APP_SECRET` / `PLURK_ACCESS_TOKEN` / `PLURK_ACCESS_TOKEN_SECRET`，且 `PLURK_AUTH_MODE=oauth`
- **THEN** MCP Server 启动时完成 OAuth 认证，后续所有 API 请求携带有效签名，无需重复认证

#### Scenario: OAuth 凭据缺失时拒绝启动
- **WHEN** `PLURK_AUTH_MODE=oauth` 但任一 OAuth 环境变量未配置
- **THEN** Server 启动时立即打印明确的缺失字段提示并退出，拒绝以未认证状态运行

#### Scenario: 凭据错误时返回认证失败
- **WHEN** OAuth 凭据格式正确但 Plurk 服务器返回认证失败（401）
- **THEN** 返回 `{"ok": false, "error": "AUTH_FAILED", "message": "Invalid OAuth credentials"}`，不重试

### Requirement: 支持账号密码模拟登录
系统必须支持通过用户名和密码模拟登录 Plurk，并将登录后的 session cookie 缓存于进程内。

#### Scenario: 模拟登录成功
- **WHEN** `PLURK_AUTH_MODE=password`，且 `PLURK_USERNAME` / `PLURK_PASSWORD` 均已配置，且凭据正确
- **THEN** MCP Server 启动时完成模拟登录，session cookie 缓存于内存，后续请求复用

#### Scenario: 模拟登录失败时返回认证错误
- **WHEN** 用户名或密码错误
- **THEN** 返回 `{"ok": false, "error": "AUTH_FAILED", "message": "Invalid username or password"}`，不重试

#### Scenario: session 过期时自动重新认证
- **WHEN** 请求中途 session 失效（服务器返回未授权响应）
- **THEN** 自动触发重新登录，登录成功后重试当前操作（最多重试 1 次）；若重试失败，返回 `{"ok": false, "error": "AUTH_EXPIRED", "message": "Session expired and re-auth failed"}`

### Requirement: 凭据不得硬编码或提交至版本库
系统必须确保认证凭据仅通过环境变量或 `.env` 文件注入，且 `.env` 被 `.gitignore` 排除。

#### Scenario: .env 文件被 git 追踪时发出警告
- **WHEN** MCP Server 启动时检测到 `.env` 文件处于 git 追踪状态（`git ls-files .env` 有输出）
- **THEN** 打印安全警告日志，提示用户将 `.env` 加入 `.gitignore`，但不阻止启动
