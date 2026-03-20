# social-mcp-multiplatform 发现与决策

> 创建日期: 2026-03-20

## 技术决策

### 账号配置使用 YAML 而非多 .env 文件

- **决策**：所有账号凭据统一存储在 `accounts.yaml`，启动时一次性加载
- **理由**：YAML 支持列表结构，天然适合 100+ 账号管理；单文件便于备份；一次加载后 session 池常驻内存，调用零 IO 开销
- **放弃**：多个 .env 文件（命名混乱，难以维护）；SQLite（引入额外依赖）

---

### PlatformAdapter 抽象接口隔离平台差异

- **决策**：定义 `BaseAdapter` 抽象类，各平台实现各自 Adapter；`AccountManager` 维护 `account_id → adapter` 字典
- **理由**：Tool 层只需调用 `manager.get(account_id).post(...)`，完全不感知平台差异；后续新增平台（如 Threads、Bluesky）只需新增 Adapter，server.py 无需改动
- **放弃**：在 Tool 层做平台 if/else 分支（耦合高，扩展困难）

---

### X 回复采用外部传入 tweet_id 模式

- **决策**：`x_reply` Tool 接受 Agent 传入的 `tweet_id`，不内置轮询机制
- **理由**：X 免费层 API 无法主动读取时间线，tweet_id 需外部来源；MCP 只负责执行回复动作，与 Plurk/FB 的"先拉时间线再回复"模式有本质区别，应在文档中明确说明
- **放弃**：内置 mention 轮询（需 Basic 层付费）

---

### 账号初始化失败跳过而非中止

- **决策**：单个账号初始化失败时，跳过并打印警告，Server 继续启动；该账号后续被调用时返回 `ACCOUNT_INIT_FAILED` 错误
- **理由**：100 个账号中个别凭据过期是常态场景，不能因此影响其他 99 个账号的服务；Agent 侧可以通过 error code 感知并跳过
- **放弃**：任一账号失败即中止启动（可用性太差）

---

### Plurk Adapter 迁移现有代码，保持向后兼容

- **决策**：将 `mcp-servers/plurk/` 中的 `plurk_client.py` + `auth.py` 逻辑迁移到 `PlurkAdapter` 类中，新增 `account_id` 参数，各实例独立维护 session 和 LRU 缓存
- **理由**：复用已验证的业务逻辑，降低迁移风险；每个 PlurkAdapter 实例拥有独立 session，100 个账号并发互不干扰
- **放弃**：全量重写（风险高，无必要）

---

### 使用 tweepy 接入 X API v2

- **决策**：X 平台使用 `tweepy` 官方 SDK（OAuth 1.0a User Context）
- **理由**：tweepy 是 Python 生态最成熟的 X/Twitter SDK，内置请求签名、速率限制处理；v2 API 支持发推和回复
- **放弃**：裸 requests 手动签名（实现复杂，维护成本高）

---

## 踩坑记录

<!-- 开发过程中持续填充 -->

## 变更摘要

| 日期 | 变更内容 | 原因 | 影响范围 |
|------|----------|------|----------|
| 2026-03-20 | 新增 X 回复功能（x_reply） | 用户需求 | X Adapter、x_reply Tool、TASK |
| 2026-03-20 | 初始化 SDD 文档 | 新 change 立项 | 全部 |
