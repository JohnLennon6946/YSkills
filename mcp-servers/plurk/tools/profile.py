"""plurk_get_profile Tool — 获取用户资料"""
from typing import Optional
import plurk_client as client
from utils import ok, err


async def plurk_get_profile(username: Optional[str] = None) -> str:
    """
    获取用户资料。

    Args:
        username: 目标用户名，不传则返回当前登录账号资料
    """
    try:
        if username:
            data = client.get_public_profile(username)
            user_info = data.get("user_info") or data
        else:
            data = client.get_own_profile()
            user_info = data

        result = {
            "user_id": user_info.get("id"),
            "nick_name": user_info.get("nick_name"),
            "display_name": user_info.get("display_name") or user_info.get("full_name"),
            "avatar_url": _build_avatar_url(user_info),
            "fans_count": user_info.get("fans_count", 0),
            "friends_count": user_info.get("friends_count", 0),
            "about": user_info.get("about", ""),
        }
        return ok(result)
    except client.PlurkAPIError as e:
        return err(e.code, e.message)


def _build_avatar_url(user_info: dict) -> str:
    """构建头像 URL"""
    avatar = user_info.get("avatar_big") or user_info.get("avatar_medium") or user_info.get("avatar")
    if avatar:
        return f"https://avatars.plurk.com/{avatar}-big2.jpg"
    uid = user_info.get("id")
    return f"https://avatars.plurk.com/{uid}-big2.jpg" if uid else ""
