## ADDED Requirements

### Requirement: 统一 Social MCP Server，注册全部 12 个 Tools
系统必须提供统一的 MCP Server 主入口，以 stdio 传输模式运行，启动时加载 `accounts.yaml` 并注册全部平台的所有 Tools。

#### Scenario: Server 正常启动并注册所有 Tools
- **WHEN** 执行 `python server.py`，`accounts.yaml` 存在
- **THEN** 完成账号池初始化后进入监听状态；`tools/list` 返回包含以下全部 12 个 Tool 的列表：
  `plurk_post`、`plurk_reply`、`plurk_get_timeline`、`plurk_get_responses`、`plurk_delete`、`plurk_like`、`plurk_get_profile`、`fb_post`、`fb_reply_comment`、`fb_get_posts`、`x_post`、`x_reply`

#### Scenario: accounts.yaml 缺失时退出
- **WHEN** 找不到 `accounts.yaml`
- **THEN** 打印错误说明并退出，不进入监听状态

#### Scenario: 部分账号初始化失败时仍正常启动
- **WHEN** 部分账号凭据无效，其余账号有效
- **THEN** 打印失败账号的警告后继续启动，有效账号的 Tools 可正常调用
