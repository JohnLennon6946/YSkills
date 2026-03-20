# plurk-mcp-skill 发现与决策

> 创建日期: 2026-03-20
> 本文档在开发全程持续更新

## 技术决策

### 使用官方 MCP Python SDK + stdio 模式

- **决策**：采用 `mcp` 官方 Python SDK，以 `stdio` 传输模式运行 MCP Server
- **理由**：stdio 模式部署最简，OpenClaw Agent 直接通过子进程调起，无需额外端口配置；官方 SDK 协议兼容性最佳
- **放弃方案**：HTTP/SSE 传输模式——本期场景为本地 Agent 调用，暂无远程访问需求；自实现 JSON-RPC——成本过高

---

### 双模式认证（OAuth 优先，密码模拟登录兜底）

- **决策**：通过 `PLURK_AUTH_MODE` 环境变量切换 OAuth 1.0a 和账号密码模拟登录两种认证模式
- **理由**：OAuth 是 Plurk 官方推荐方式，稳定可靠；模拟登录为无法申请 App 的场景提供快速接入通道；两种模式对上层 Tool 接口透明
- **放弃方案**：仅支持 OAuth——灵活性不足；仅支持模拟登录——平台接口变更风险高

---

### 进程内内存缓存 session/token

- **决策**：OAuth token 和模拟登录 session cookie 均缓存于进程内单例，不持久化到磁盘
- **理由**：MCP Server 为长进程运行，内存缓存性能最优；Plurk OAuth access token 不设过期，内存存储足够；避免 token 持久化带来的安全隐患
- **放弃方案**：持久化到本地文件——引入安全风险且增加复杂度

---

### `plurk_reply` 内部自动解析 user_id → nick_name

- **决策**：`plurk_reply` Tool 接受 `user_id`，由 MCP 内部调用 `/APP/Users/getPublicProfile` 解析 nick_name，并拼接 `@nick_name` 前缀后发送
- **理由**：Agent 从 timeline/responses 数据中自然获取 user_id，无需额外查询；MCP 统一封装此逻辑避免 Agent 侧重复实现；nick_name 结果 LRU 缓存（上限 500 条）减少重复请求
- **放弃方案**：由 Agent 传入 username——增加 Agent 侧负担；直接 @ user_id——不符合平台习惯

---

### 统一结构化返回格式

- **决策**：所有 Tool 返回 JSON 字符串，成功为 `{"ok": true, "data": {...}}`，失败为 `{"ok": false, "error": "ERROR_CODE", "message": "..."}`
- **理由**：Agent 通过 `ok` 字段快速分支判断；结构化 error code 便于 Agent 做精细化错误处理；比抛异常更适合 MCP 场景
- **放弃方案**：抛 Python 异常——MCP SDK 序列化后 Agent 侧解析不便

---

## 踩坑记录

<!-- 开发过程中持续填充 -->

## 变更摘要

| 日期 | 变更内容 | 原因 | 影响范围 |
|------|----------|------|----------|
| 2026-03-20 | 初始化 SDD 文档（PRD / DESIGN / FINDINGS / SPECS / TASK） | 新功能立项 | 全部 |
