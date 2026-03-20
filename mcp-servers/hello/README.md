# Hello MCP Server

最简单的 MCP Server 示例，演示如何创建和配置 MCP 工具。

## 功能

| Tool | 说明 | 参数 |
|------|------|------|
| `say_hello` | 向指定的人打招呼 | `name` (必填), `language` (可选) |

## 安装

```bash
cd mcp-servers/hello
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## 运行

```bash
python server.py
```

## 在 OpenClaw 中配置

编辑 `~/.openclaw/openclaw.json`：

```json
{
  "mcpServers": {
    "hello": {
      "command": "python",
      "args": ["/Users/mima1234/Desktop/YSkills/mcp-servers/hello/server.py"]
    }
  }
}
```

## 使用示例

调用 `say_hello` Tool：

```json
{
  "name": "say_hello",
  "arguments": {
    "name": "小明",
    "language": "zh"
  }
}
```

返回：
```
你好，小明！👋
```

## 代码结构

```
hello/
├── server.py          # MCP Server 主入口
├── requirements.txt   # Python 依赖
└── README.md          # 使用说明
```

## 关键概念

1. **Server**: MCP Server 实例，管理所有工具和生命周期
2. **Tool**: 可执行的功能，有名称、描述、参数 schema
3. **list_tools**: 告诉客户端有哪些工具可用
4. **call_tool**: 实际执行工具调用
