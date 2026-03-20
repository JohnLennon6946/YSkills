"""plurk_get_responses Tool — 获取帖子回复列表"""
import plurk_client as client
from utils import ok, err


async def plurk_get_responses(plurk_id: int) -> str:
    """
    获取指定帖子的所有回复。

    Args:
        plurk_id: 目标帖子 ID
    """
    try:
        data = client.get_responses(plurk_id)
        responses = data.get("responses", [])
        response_users = data.get("friends", {})

        simplified = [
            {
                "response_id": r.get("id"),
                "user_id": r.get("user_id"),
                "content": r.get("content_raw") or r.get("content", ""),
                "posted": r.get("posted"),
            }
            for r in responses
        ]
        return ok({"responses": simplified, "response_users": response_users})
    except client.PlurkAPIError as e:
        return err(e.code, e.message)
