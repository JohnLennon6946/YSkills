"""
Plurk MCP Server 主入口
供 OpenClaw 等 AI Agent 框架通过 stdio 协议调用
"""
import logging
import os
import sys

from dotenv import load_dotenv
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

# 加载 .env
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("plurk-mcp")

# 导入认证模块和所有 Tools
import auth
from tools.post import plurk_post
from tools.reply import plurk_reply
from tools.timeline import plurk_get_timeline
from tools.responses import plurk_get_responses
from tools.delete import plurk_delete
from tools.profile import plurk_get_profile
from tools.like import plurk_like

# 初始化 MCP Server
app = Server("plurk-mcp")


@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="plurk_post",
            description="发布一条新 Plurk 帖子",
            inputSchema={
                "type": "object",
                "properties": {
                    "content": {"type": "string", "description": "帖子正文，不超过 360 字符"},
                    "qualifier": {
                        "type": "string",
                        "default": ":",
                        "description": "发帖类型，可选：: says shares likes wishes needs wants has will asks hopes thinks is",
                    },
                },
                "required": ["content"],
            },
        ),
        Tool(
            name="plurk_reply",
            description="回复指定帖子，自动 @ 目标用户",
            inputSchema={
                "type": "object",
                "properties": {
                    "plurk_id": {"type": "integer", "description": "目标帖子 ID"},
                    "user_id": {"type": "integer", "description": "被回复用户的 ID"},
                    "content": {"type": "string", "description": "回复正文（不含 @ 前缀）"},
                },
                "required": ["plurk_id", "user_id", "content"],
            },
        ),
        Tool(
            name="plurk_get_timeline",
            description="获取当前账号时间线帖子列表",
            inputSchema={
                "type": "object",
                "properties": {
                    "offset": {"type": "string", "description": "分页时间戳（ISO 8601），不传则获取最新"},
                    "limit": {"type": "integer", "default": 20, "description": "每页条数（1~30）"},
                },
            },
        ),
        Tool(
            name="plurk_get_responses",
            description="获取指定帖子的所有回复",
            inputSchema={
                "type": "object",
                "properties": {
                    "plurk_id": {"type": "integer", "description": "目标帖子 ID"},
                },
                "required": ["plurk_id"],
            },
        ),
        Tool(
            name="plurk_delete",
            description="删除当前账号发布的指定帖子",
            inputSchema={
                "type": "object",
                "properties": {
                    "plurk_id": {"type": "integer", "description": "要删除的帖子 ID"},
                },
                "required": ["plurk_id"],
            },
        ),
        Tool(
            name="plurk_get_profile",
            description="获取用户资料，不传 username 则返回当前账号资料",
            inputSchema={
                "type": "object",
                "properties": {
                    "username": {"type": "string", "description": "目标用户名（可选）"},
                },
            },
        ),
        Tool(
            name="plurk_like",
            description="点赞指定帖子",
            inputSchema={
                "type": "object",
                "properties": {
                    "plurk_id": {"type": "integer", "description": "目标帖子 ID"},
                },
                "required": ["plurk_id"],
            },
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    handlers = {
        "plurk_post": plurk_post,
        "plurk_reply": plurk_reply,
        "plurk_get_timeline": plurk_get_timeline,
        "plurk_get_responses": plurk_get_responses,
        "plurk_delete": plurk_delete,
        "plurk_get_profile": plurk_get_profile,
        "plurk_like": plurk_like,
    }

    handler = handlers.get(name)
    if not handler:
        result = f'{{"ok": false, "error": "UNKNOWN_TOOL", "message": "Unknown tool: {name}"}}'
    else:
        result = await handler(**arguments)

    return [TextContent(type="text", text=result)]


def main():
    # 校验认证配置并初始化
    try:
        auth.init_auth()
    except ValueError as e:
        logger.error(f"配置错误：{e}")
        logger.error("请参考 .env.example 文件完成配置后重新启动")
        sys.exit(1)
    except PermissionError as e:
        logger.error(f"认证失败：{e}")
        sys.exit(1)

    logger.info("Plurk MCP Server 启动成功，等待调用...")

    import asyncio
    async def _run():
        async with stdio_server() as (read_stream, write_stream):
            await app.run(read_stream, write_stream, app.create_initialization_options())

    asyncio.run(_run())


if __name__ == "__main__":
    main()
