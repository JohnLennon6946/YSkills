---
name: hello-mcp
description: |
  调用 Hello MCP Server 向用户问好。
  
  使用场景：
  - 用户自我介绍时说"你好，我叫XXX"
  - 用户主动要求打招呼
  - 需要测试 MCP 连接时
  
  触发词：你好、我叫、我是、我的名字是、测试 MCP、打个招呼
---

# Hello MCP Skill

## 功能

通过 Hello MCP Server 向指定的人发送问候语，支持中文、英文、日文三种语言。

## 前置条件

1. Hello MCP Server 已部署在 `~/Desktop/YSkills/mcp-servers/hello/`
2. Python 虚拟环境已配置

## 使用方法

### 场景 1：用户自我介绍

**用户输入示例**：
```
你好，我叫俞思宇
我是小明
我的名字是 Alice
```

**执行步骤**：

1. 从用户输入中提取名字
   - 匹配模式："我叫(.*)"、"我是(.*)"、"我的名字是(.*)"
   - 清理：去除标点符号和多余空格

2. 检测语言（可选）
   - 如果名字是中文 → language = "zh"
   - 如果名字是英文 → language = "en"
   - 如果名字是日文 → language = "jp"
   - 默认 → "zh"

3. 调用 Hello MCP Server
   ```bash
   cd ~/Desktop/YSkills/mcp-servers/hello
   source .venv/bin/activate
   python3 -c "
   import subprocess
   import json
   
   proc = subprocess.Popen(
       ['.venv/bin/python', 'server.py'],
       stdin=subprocess.PIPE,
       stdout=subprocess.PIPE,
       stderr=subprocess.PIPE,
       text=True
   )
   
   # 初始化
   init = {'jsonrpc': '2.0', 'id': 1, 'method': 'initialize', 'params': {'protocolVersion': '2024-11-05', 'capabilities': {}, 'clientInfo': {'name': 'openclaw', 'version': '1.0'}}}
   proc.stdin.write(json.dumps(init) + '\n')
   proc.stdin.flush()
   proc.stdout.readline()
   
   # initialized 通知
   proc.stdin.write(json.dumps({'jsonrpc': '2.0', 'method': 'notifications/initialized'}) + '\n')
   proc.stdin.flush()
   
   # 调用 say_hello
   call = {'jsonrpc': '2.0', 'id': 2, 'method': 'tools/call', 'params': {'name': 'say_hello', 'arguments': {'name': '<提取的名字>', 'language': '<检测的语言>'}}}
   proc.stdin.write(json.dumps(call) + '\n')
   proc.stdin.flush()
   
   response = proc.stdout.readline()
   proc.terminate()
   
   result = json.loads(response)
   print(result['result']['content'][0]['text'])
   "
   ```

4. 返回结果给用户
   - 成功：展示 MCP 返回的问候语
   - 失败：提示错误信息

### 场景 2：主动打招呼

**用户输入示例**：
```
测试 MCP
打个招呼
用英文向 Bob 问好
用日文向田中问好
```

**执行步骤**：

1. 解析用户意图
   - "测试 MCP" → 使用默认名字 "World"
   - "打个招呼" → 询问用户名字
   - "用英文向 Bob 问好" → name="Bob", language="en"
   - "用日文向田中问好" → name="田中", language="jp"

2. 调用 MCP（同上）

3. 返回结果

## 参数说明

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| name | string | 是 | 要问候的人的名字 |
| language | string | 否 | 语言代码（zh/en/jp），默认 zh |

## 错误处理

| 错误场景 | 处理方式 |
|---------|---------|
| MCP Server 未启动 | 提示用户检查 server.py 是否存在 |
| 虚拟环境未配置 | 提示运行 `pip install -r requirements.txt` |
| 名字提取失败 | 询问用户"请问您叫什么名字？" |
| MCP 调用超时 | 重试一次，仍失败则提示网络问题 |

## 示例输出

**输入**：你好，我叫俞思宇

**输出**：
```
🤖 调用 Hello MCP...
✅ 结果：你好，俞思宇！👋
```

**输入**：用英文向 Alice 问好

**输出**：
```
🤖 调用 Hello MCP...
✅ 结果：Hello, Alice! 👋
```

## 注意事项

- 每次调用都会启动新的 MCP Server 进程，调用结束后自动关闭
- 如需长期运行，可考虑将 Server 作为守护进程启动
- 名字长度建议不超过 20 个字符
