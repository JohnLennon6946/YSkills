## ADDED Requirements

### Requirement: MCP Server 注册并暴露所有 Plurk Tools
系统必须提供一个 MCP Server 主入口（`server.py`），将所有 Plurk 操作能力注册为标准 MCP Tools，并以 stdio 传输模式运行，供 OpenClaw 及其他 MCP 兼容 Agent 框架调用。

#### Scenario: Server 正常启动
- **WHEN** 执行 `python server.py`，且 `.env` 中认证配置完整有效
- **THEN** Server 完成认证初始化后进入监听状态，所有 Tools 可被调用

#### Scenario: 配置缺失时拒绝启动
- **WHEN** `.env` 中认证相关环境变量缺失
- **THEN** Server 打印缺失字段说明后退出，不进入监听状态

#### Scenario: Tool 列表完整
- **WHEN** MCP Client 请求 `tools/list`
- **THEN** 返回包含以下全部 7 个 Tool 的列表：`plurk_post`、`plurk_reply`、`plurk_get_timeline`、`plurk_get_responses`、`plurk_delete`、`plurk_get_profile`、`plurk_like`
