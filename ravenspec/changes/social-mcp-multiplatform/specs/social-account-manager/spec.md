## ADDED Requirements

### Requirement: 从 accounts.yaml 加载所有账号并初始化 session 池
系统必须在启动时读取 `accounts.yaml`，为每个账号创建对应的 PlatformAdapter 实例并完成认证初始化。

#### Scenario: 全部账号初始化成功
- **WHEN** `accounts.yaml` 存在且所有账号凭据有效
- **THEN** 所有账号 session 初始化完成，打印汇总状态表（account_id / platform / status: ok）

#### Scenario: 某账号凭据无效时跳过并继续
- **WHEN** 某账号凭据无效（认证失败）
- **THEN** 打印该账号的警告日志（`[WARN] account <id> init failed: AUTH_FAILED`），跳过该账号，其他账号正常初始化；该账号后续调用时返回 `{"ok": false, "error": "ACCOUNT_INIT_FAILED", "message": "..."}`

#### Scenario: accounts.yaml 不存在时退出
- **WHEN** 启动时找不到 `accounts.yaml`
- **THEN** 打印错误提示（含 `accounts.yaml.example` 参考路径）并退出，不进入监听状态

#### Scenario: account_id 不存在时返回错误
- **WHEN** Tool 调用时传入的 `account_id` 在账号池中不存在
- **THEN** 返回 `{"ok": false, "error": "ACCOUNT_NOT_FOUND", "message": "Account '<id>' not found"}`

#### Scenario: accounts.yaml 被 git 追踪时发出安全警告
- **WHEN** 启动时检测到 `accounts.yaml` 被 git 追踪
- **THEN** 打印安全警告，提示用户将其加入 `.gitignore`，不阻止启动
