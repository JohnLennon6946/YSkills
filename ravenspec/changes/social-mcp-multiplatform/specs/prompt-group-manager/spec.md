## ADDED Requirements

### Requirement: accounts.yaml 支持 prompt_groups 配置，AccountManager 提供 get_prompt 方法
系统必须支持在 `accounts.yaml` 中定义 `prompt_groups`，每个账号可通过 `group` 字段绑定一个 prompt 分组；AccountManager 提供 `get_prompt(account_id)` 方法，MCP Server 通过 `get_account_prompt` Tool 对外暴露。

#### Scenario: 账号有绑定 group 且 group 存在时返回 prompt
- **WHEN** Agent 调用 `get_account_prompt`，传入有效 `account_id`，该账号配置了 `group` 且 `group` 在 `prompt_groups` 中存在
- **THEN** 返回 `{"ok": true, "data": {"group": "<group>", "post_prompt": "...", "reply_prompt": "...", "language": "..."}}`

#### Scenario: 账号未配置 group 时返回空 prompt
- **WHEN** 账号配置中没有 `group` 字段
- **THEN** 返回 `{"ok": true, "data": {"group": null, "post_prompt": null, "reply_prompt": null, "language": null}}`，由 Agent 使用自身默认 prompt

#### Scenario: group 值在 prompt_groups 中不存在时返回错误
- **WHEN** 账号的 `group` 值在 `accounts.yaml` 的 `prompt_groups` 区块中找不到对应定义
- **THEN** 返回 `{"ok": false, "error": "GROUP_NOT_FOUND", "message": "Prompt group '<group>' not found in accounts.yaml"}`

#### Scenario: account_id 不存在时返回错误
- **WHEN** 传入的 `account_id` 不在账号池中
- **THEN** 返回 `{"ok": false, "error": "ACCOUNT_NOT_FOUND", "message": "Account '<id>' not found"}`

#### Scenario: 同一 group 的多个账号共享同一套 prompt
- **WHEN** accounts.yaml 中 10 个账号绑定同一 group（如 `tech_zh`）
- **THEN** 这 10 个账号调用 `get_account_prompt` 均返回相同的 `post_prompt` 和 `reply_prompt`

#### Scenario: prompt_groups 配置热更新（重启生效）
- **WHEN** 用户修改 accounts.yaml 中的 prompt_groups 内容
- **THEN** 重启 MCP Server 后生效；运行时修改不自动热更新（本期不做）
