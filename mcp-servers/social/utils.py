"""统一返回格式工具函数"""
import json


def ok(data: dict) -> str:
    return json.dumps({"ok": True, "data": data}, ensure_ascii=False)


def err(code: str, message: str) -> str:
    return json.dumps({"ok": False, "error": code, "message": message}, ensure_ascii=False)
