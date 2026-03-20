#!/usr/bin/env python3
"""
Hello MCP Server - 最简单的 MCP Server 示例
功能：提供 say_hello Tool，接收名字返回问候语
"""

import asyncio
from mcp.server.models import InitializationOptions
from mcp.server import NotificationOptions, Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    Resource,
    Tool,
    TextContent,
    LoggingLevel,
    CallToolRequestParams,
)

# 创建 MCP Server 实例
server = Server("hello-mcp")


# ========== 工具列表 ==========
@server.list_tools()
async def list_tools() -> list[Tool]:
    """告诉客户端我有哪些工具可用"""
    return [
        Tool(
            name="say_hello",
            description="向指定的人打招呼",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "要问候的人的名字"
                    },
                    "language": {
                        "type": "string",
                        "description": "语言（zh=中文, en=英文, jp=日文）",
                        "enum": ["zh", "en", "jp"],
                        "default": "zh"
                    }
                },
                "required": ["name"]
            }
        )
    ]


# ========== 工具执行 ==========
@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """执行工具调用"""
    
    if name == "say_hello":
        name = arguments.get("name", "World")
        language = arguments.get("language", "zh")
        
        # 根据语言返回不同问候语
        greetings = {
            "zh": f"你好，{name}！👋",
            "en": f"Hello, {name}! 👋",
            "jp": f"こんにちは、{name}さん！👋"
        }
        
        message = greetings.get(language, greetings["zh"])
        
        return [TextContent(type="text", text=message)]
    
    else:
        raise ValueError(f"未知工具: {name}")


# ========== 主入口 ==========
async def main():
    """启动 MCP Server"""
    
    # 配置服务器选项
    options = server.create_initialization_options(
        notification_options=NotificationOptions(),
        experimental_capabilities={}
    )
    
    # 使用 stdio 传输（标准输入输出）
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            options
        )


if __name__ == "__main__":
    asyncio.run(main())
