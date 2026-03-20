#!/usr/bin/env python3
"""
测试 Hello MCP Server 的客户端脚本
模拟 OpenClaw 如何调用 MCP Tool
"""

import subprocess
import json
import sys

def call_mcp_server():
    """调用 MCP Server 并测试 say_hello Tool"""
    
    # 启动 MCP Server 进程
    process = subprocess.Popen(
        ["/Users/mima1234/Desktop/YSkills/mcp-servers/hello/.venv/bin/python", 
         "/Users/mima1234/Desktop/YSkills/mcp-servers/hello/server.py"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    try:
        # Step 1: 发送初始化请求
        init_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "test-client", "version": "1.0.0"}
            }
        }
        
        print("📤 发送初始化请求...")
        process.stdin.write(json.dumps(init_request) + "\n")
        process.stdin.flush()
        
        # 读取初始化响应
        init_response = process.stdout.readline()
        print(f"📥 初始化响应: {init_response}")
        
        # Step 2: 发送 initialized 通知
        initialized_notification = {
            "jsonrpc": "2.0",
            "method": "notifications/initialized"
        }
        process.stdin.write(json.dumps(initialized_notification) + "\n")
        process.stdin.flush()
        
        # Step 3: 获取工具列表
        list_tools_request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list"
        }
        
        print("\n📤 获取工具列表...")
        process.stdin.write(json.dumps(list_tools_request) + "\n")
        process.stdin.flush()
        
        tools_response = process.stdout.readline()
        print(f"📥 工具列表: {tools_response}")
        
        # Step 4: 调用 say_hello Tool
        call_tool_request = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "say_hello",
                "arguments": {
                    "name": "小明",
                    "language": "zh"
                }
            }
        }
        
        print("\n📤 调用 say_hello Tool...")
        print(f"   参数: name='小明', language='zh'")
        process.stdin.write(json.dumps(call_tool_request) + "\n")
        process.stdin.flush()
        
        tool_response = process.stdout.readline()
        print(f"📥 Tool 响应: {tool_response}")
        
        # 解析响应
        response_data = json.loads(tool_response)
        if "result" in response_data:
            content = response_data["result"]["content"][0]["text"]
            print(f"\n✅ 成功！MCP Server 返回: {content}")
        else:
            print(f"\n❌ 错误: {response_data.get('error', 'Unknown error')}")
        
        # 再测试英文
        call_tool_request["id"] = 4
        call_tool_request["params"]["arguments"] = {"name": "Alice", "language": "en"}
        
        print("\n📤 测试英文问候...")
        process.stdin.write(json.dumps(call_tool_request) + "\n")
        process.stdin.flush()
        
        tool_response2 = process.stdout.readline()
        response_data2 = json.loads(tool_response2)
        if "result" in response_data2:
            content2 = response_data2["result"]["content"][0]["text"]
            print(f"✅ 英文问候: {content2}")
        
        # 再测试日文
        call_tool_request["id"] = 5
        call_tool_request["params"]["arguments"] = {"name": "田中", "language": "jp"}
        
        print("\n📤 测试日文问候...")
        process.stdin.write(json.dumps(call_tool_request) + "\n")
        process.stdin.flush()
        
        tool_response3 = process.stdout.readline()
        response_data3 = json.loads(tool_response3)
        if "result" in response_data3:
            content3 = response_data3["result"]["content"][0]["text"]
            print(f"✅ 日文问候: {content3}")
        
    finally:
        process.terminate()
        process.wait()

if __name__ == "__main__":
    print("=" * 60)
    print("🧪 Hello MCP Server 测试")
    print("=" * 60)
    call_mcp_server()
    print("\n" + "=" * 60)
    print("✨ 测试完成！")
    print("=" * 60)
