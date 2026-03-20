"""plurk_like Tool — 点赞帖子"""
import plurk_client as client
from utils import ok, err


async def plurk_like(plurk_id: int) -> str:
    """
    点赞指定帖子。重复点赞时静默成功。

    Args:
        plurk_id: 目标帖子 ID
    """
    try:
        client.like_plurk(plurk_id)
        return ok({"plurk_id": plurk_id, "liked": True})
    except client.PlurkAPIError as e:
        # 已点过赞时 API 可能返回特定错误，静默处理
        if "already" in e.message.lower() or e.code == "FORBIDDEN":
            return ok({"plurk_id": plurk_id, "liked": True, "already_liked": True})
        return err(e.code, e.message)
