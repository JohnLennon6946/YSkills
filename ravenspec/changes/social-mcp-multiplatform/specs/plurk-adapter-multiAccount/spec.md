## MODIFIED Requirements

### Requirement: Plurk 全部 Tools 新增 account_id 参数
所有 Plurk MCP Tools 在现有基础上新增必填参数 `account_id`，通过 AccountManager 路由到对应账号的 PlurkAdapter 执行操作。其余业务逻辑与 `plurk-mcp-skill` 中的 specs 完全一致，不重复列举。

#### Scenario: account_id 有效时路由到对应 PlurkAdapter
- **WHEN** 任意 Plurk Tool 被调用，且 `account_id` 在账号池中存在且初始化成功
- **THEN** 操作通过该账号的 PlurkAdapter 执行，结果与 `plurk-mcp-skill` 中对应 spec 的 Scenario 一致

#### Scenario: account_id 无效时返回错误
- **WHEN** 传入的 `account_id` 不存在或该账号初始化失败
- **THEN** 返回 `{"ok": false, "error": "ACCOUNT_NOT_FOUND", "message": "Account '<id>' not found or failed to initialize"}`，不执行任何 Plurk API 调用

#### Scenario: 不同 account_id 并发调用互不干扰
- **WHEN** 多个不同 `account_id` 同时调用 Plurk Tools
- **THEN** 各账号使用独立 session 和 LRU 缓存，互不干扰，均能正常返回结果

### Requirement: PlurkAdapter 迁移现有 plurk_client 逻辑
将现有 `mcp-servers/plurk/` 的 `plurk_client.py` + `auth.py` 逻辑封装为 `PlurkAdapter` 类，支持 OAuth 和密码模拟登录双模式，每个实例独立管理 session 和 LRU 用户名缓存。

#### Scenario: 每个 PlurkAdapter 实例独立管理 session
- **WHEN** AccountManager 初始化 100 个 PlurkAdapter 实例
- **THEN** 每个实例持有独立的 session（OAuth session 或 requests.Session），互不共享

#### Scenario: 每个 PlurkAdapter 实例独立管理 LRU 缓存
- **WHEN** 同一 user_id 在不同 PlurkAdapter 实例中被查询
- **THEN** 各实例各自维护独立的 LRU 缓存（maxsize=500），不跨实例共享
