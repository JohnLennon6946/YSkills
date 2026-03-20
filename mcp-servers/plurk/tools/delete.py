"""plurk_delete Tool — 删除帖子"""
import plurk_client as client
from utils import ok, err


async def plurk_delete(plurk_id: int) -> str:
    """
    删除当前账号发布的指定帖子。

    Args:
        plurk_id: 要删除的帖子 ID
    """
    try:
        client.delete_plurk(plurk_id)
        return ok({"plurk_id": plurk_id, "deleted": True})
    except client.PlurkAPIError as e:
        return err(e.code, e.message)
