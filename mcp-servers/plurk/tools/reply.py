"""plurk_reply Tool — 回复帖子并 @ 目标用户"""
import plurk_client as client
from utils import ok, err


async def plurk_reply(plurk_id: int, user_id: int, content: str) -> str:
    """
    回复指定帖子，自动 @ 目标用户。

    Args:
        plurk_id: 目标帖子 ID（从 plurk_get_timeline 或 plurk_get_responses 结果中获取）
        user_id:  被回复的用户 ID（从 timeline/responses 结果中获取）
        content:  回复正文（不含 @ 前缀，系统自动拼接）
    """
    if not content or not content.strip():
        return err("INVALID_PARAMS", "content must not be empty")

    # 解析 user_id → nick_name
    username_fallback = False
    nick_name = client.get_username_by_id(user_id)
    if nick_name:
        full_content = f"@{nick_name} {content}"
    else:
        # 降级：用 user_id 字符串作为 @ 目标
        full_content = f"@{user_id} {content}"
        username_fallback = True

    try:
        data = client.response_plurk(plurk_id, full_content)
        response_id = data.get("id")
        result = {"response_id": response_id}
        if username_fallback:
            result["username_fallback"] = True
        return ok(result)
    except client.PlurkAPIError as e:
        return err(e.code, e.message)
