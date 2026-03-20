#!/usr/bin/env python3
"""
Hello MCP Skill 辅助脚本
简化 MCP Server 的调用
"""

import subprocess
import json
import sys

def call_say_hello(name: str, language: str = "zh") -> str:
    """
    调用 Hello MCP Server 的 say_hello Tool
    
    Args:
        name: 要问候的名字
        language: 语言代码 (zh/en/jp)
    
    Returns:
        问候语字符串
    """
    proc = subprocess.Popen(
        ['/Users/mima1234/Desktop/YSkills/mcp-servers/hello/.venv/bin/python',
         '/Users/mima1234/Desktop/YSkills/mcp-servers/hello/server.py'],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    try:
        # 初始化
        init = {
            'jsonrpc': '2.0',
            'id': 1,
            'method': 'initialize',
            'params': {
                'protocolVersion': '2024-11-05',
                'capabilities': {},
                'clientInfo': {'name': 'hello-skill', 'version': '1.0'}
            }
        }
        proc.stdin.write(json.dumps(init) + '\n')
        proc.stdin.flush()
        proc.stdout.readline()
        
        # initialized 通知
        proc.stdin.write(json.dumps({'jsonrpc': '2.0', 'method': 'notifications/initialized'}) + '\n')
        proc.stdin.flush()
        
        # 调用 say_hello
        call = {
            'jsonrpc': '2.0',
            'id': 2,
            'method': 'tools/call',
            'params': {
                'name': 'say_hello',
                'arguments': {
                    'name': name,
                    'language': language
                }
            }
        }
        proc.stdin.write(json.dumps(call) + '\n')
        proc.stdin.flush()
        
        response = proc.stdout.readline()
        result = json.loads(response)
        
        if 'result' in result:
            return result['result']['content'][0]['text']
        else:
            return f"错误: {result.get('error', 'Unknown error')}"
    
    finally:
        proc.terminate()
        proc.wait()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python helper.py <名字> [语言]")
        print("示例: python helper.py 俞思宇 zh")
        sys.exit(1)
    
    name = sys.argv[1]
    language = sys.argv[2] if len(sys.argv) > 2 else "zh"
    
    result = call_say_hello(name, language)
    print(result)
