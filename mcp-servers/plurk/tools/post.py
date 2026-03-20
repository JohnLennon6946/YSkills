"""plurk_post Tool — 发布新帖子"""
import plurk_client as client
from utils import ok, err


VALID_QUALIFIERS = {":", "says", "shares", "likes", "wishes", "needs",
                    "wants", "has", "will", "asks", "hopes", "thinks", "is"}


async def plurk_post(content: str, qualifier: str = ":") -> str:
    """
    发布一条新 Plurk 帖子。

    Args:
        content: 帖子正文（不超过 360 字符）
        qualifier: 发帖类型，可选值: : says shares likes wishes needs wants has will asks hopes thinks is
    """
    # 参数校验
    if not content or not content.strip():
        return err("INVALID_PARAMS", "content must not be empty")
    if len(content) > 360:
        return err("CONTENT_TOO_LONG", f"content exceeds 360 characters (got {len(content)})")
    if qualifier not in VALID_QUALIFIERS:
        return err("INVALID_PARAMS", f"invalid qualifier '{qualifier}', valid values: {', '.join(sorted(VALID_QUALIFIERS))}")

    try:
        data = client.add_plurk(content, qualifier)
        plurk_id = data.get("plurk_id") or data.get("id")
        plurk_url = f"https://www.plurk.com/p/{_encode_id(plurk_id)}" if plurk_id else ""
        return ok({"plurk_id": plurk_id, "url": plurk_url})
    except client.PlurkAPIError as e:
        return err(e.code, e.message)


def _encode_id(plurk_id: int) -> str:
    """将 plurk_id 编码为 base 36 短链（Plurk URL 格式）"""
    if not plurk_id:
        return ""
    chars = "0123456789abcdefghijklmnopqrstuvwxyz"
    result = ""
    n = int(plurk_id)
    while n:
        result = chars[n % 36] + result
        n //= 36
    return result or "0"
