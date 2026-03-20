"""统一返回格式工具函数"""
import json


def ok(data: dict) -> str:
    """返回成功结果"""
    return json.dumps({"ok": True, "data": data}, ensure_ascii=False)


def err(code: str, message: str) -> str:
    """返回失败结果"""
    return json.dumps({"ok": False, "error": code, "message": message}, ensure_ascii=False)
