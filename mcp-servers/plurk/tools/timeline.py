"""plurk_get_timeline Tool — 获取时间线"""
from typing import Optional
import plurk_client as client
from utils import ok, err


async def plurk_get_timeline(offset: Optional[str] = None, limit: int = 20) -> str:
    """
    获取当前账号时间线帖子列表。

    Args:
        offset: 分页时间戳（ISO 8601），不传则获取最新
        limit:  每页条数（1~30，默认 20）
    """
    try:
        data = client.get_plurks(offset=offset, limit=limit)
        plurks = data.get("plurks", [])
        plurk_users = data.get("plurk_users", {})

        simplified = [
            {
                "plurk_id": p.get("plurk_id"),
                "owner_id": p.get("owner_id"),
                "content": p.get("content_raw") or p.get("content", ""),
                "posted": p.get("posted"),
                "response_count": p.get("response_count", 0),
                "qualifier": p.get("qualifier", ":"),
            }
            for p in plurks
        ]
        return ok({"plurks": simplified, "plurk_users": plurk_users})
    except client.PlurkAPIError as e:
        return err(e.code, e.message)
