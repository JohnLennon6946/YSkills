## ADDED Requirements

### Requirement: 提供面向 OpenClaw Agent 的 Skill 接入文档
系统必须提供 `SKILL.md` 文档，指导 OpenClaw AI Agent 正确配置并使用本 Plurk MCP Server，包含环境变量配置、认证模式选择、Tool 调用示例和错误处理建议。

#### Scenario: 文档包含完整的环境变量配置说明
- **WHEN** 用户阅读 `SKILL.md`
- **THEN** 文档中应包含所有必填和可选环境变量的名称、说明、示例值，以及 `.env.example` 文件的参考链接

#### Scenario: 文档包含 OAuth 与模拟登录的选择指引
- **WHEN** 用户不确定选择哪种认证模式
- **THEN** 文档中说明两种模式的适用场景、优缺点，以及 OAuth App 申请入口

#### Scenario: 文档包含定时发帖场景的调用示例
- **WHEN** OpenClaw Agent 需要配置每日定时发帖任务
- **THEN** `SKILL.md` 中提供完整的调用链示例：触发条件 → 生成文案 → 调用 `plurk_post` → 处理返回结果

#### Scenario: 文档包含自动回复场景的调用示例
- **WHEN** OpenClaw Agent 需要配置自动回复任务
- **THEN** `SKILL.md` 中提供完整的调用链示例：`plurk_get_timeline` → `plurk_get_responses` → 生成回复文案 → `plurk_reply`

#### Scenario: 文档包含错误处理建议
- **WHEN** Agent 调用 Tool 收到 `ok: false` 响应
- **THEN** `SKILL.md` 中说明各 error code 的含义及建议的 Agent 侧处理策略（如 `RATE_LIMITED` 建议等待后重试，`AUTH_FAILED` 建议检查配置）
