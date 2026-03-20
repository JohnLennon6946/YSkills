"""
PlurkClient — Plurk API 统一封装层
含网络重试、自动重认证、LRU 用户名缓存
"""
import functools
import logging
import time
from typing import Any, Optional

import requests

from auth import get_session, reauth

logger = logging.getLogger(__name__)

BASE_URL = "https://www.plurk.com/APP"
MAX_RETRIES = 3
RETRY_INTERVAL = 5  # 秒


class PlurkAPIError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 0):
        self.code = code
        self.message = message
        self.status_code = status_code
        super().__init__(message)


def _map_http_error(status_code: int, body: dict) -> PlurkAPIError:
    """将 HTTP 错误码映射为结构化错误"""
    error_text = body.get("error_text", "")
    if status_code == 401:
        return PlurkAPIError("AUTH_FAILED", f"认证失败：{error_text}", status_code)
    if status_code == 403:
        return PlurkAPIError("FORBIDDEN", f"无权限：{error_text}", status_code)
    if status_code == 404:
        return PlurkAPIError("NOT_FOUND", f"资源不存在：{error_text}", status_code)
    if status_code == 429:
        return PlurkAPIError("RATE_LIMITED", f"请求过于频繁，请稍后重试：{error_text}", status_code)
    return PlurkAPIError("API_ERROR", f"API 错误 {status_code}：{error_text}", status_code)


def _request(method: str, endpoint: str, _reauth_attempted: bool = False, **params) -> dict:
    """
    统一 API 请求入口
    - 网络错误自动重试最多 3 次，间隔 5s
    - 401 时自动触发重认证并重试（最多 1 次）
    """
    url = f"{BASE_URL}{endpoint}"
    session = get_session()

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            if method.upper() == "GET":
                resp = session.get(url, params=params)
            else:
                resp = session.post(url, data=params)

            # 401：尝试重新认证
            if resp.status_code == 401 and not _reauth_attempted:
                reauth()
                return _request(method, endpoint, _reauth_attempted=True, **params)

            # 其他 HTTP 错误
            if not resp.ok:
                try:
                    body = resp.json()
                except Exception:
                    body = {}
                raise _map_http_error(resp.status_code, body)

            return resp.json()

        except PlurkAPIError:
            raise
        except (requests.ConnectionError, requests.Timeout) as e:
            if attempt < MAX_RETRIES:
                logger.warning(f"网络错误，{RETRY_INTERVAL}s 后重试（{attempt}/{MAX_RETRIES}）：{e}")
                time.sleep(RETRY_INTERVAL)
            else:
                raise PlurkAPIError("NETWORK_ERROR", f"网络错误，已重试 {MAX_RETRIES} 次：{e}")
        except Exception as e:
            raise PlurkAPIError("UNKNOWN_ERROR", str(e))

    raise PlurkAPIError("NETWORK_ERROR", f"请求失败，已重试 {MAX_RETRIES} 次")


# ── 用户名缓存（LRU，最多 500 条） ────────────────────────────

@functools.lru_cache(maxsize=500)
def _cached_get_username(user_id: int) -> Optional[str]:
    """内部缓存层，由 get_username_by_id 调用"""
    try:
        data = _request("GET", "/Users/getPublicProfile", user_id=user_id)
        user_info = data.get("user_info") or data
        return user_info.get("nick_name") or user_info.get("display_name")
    except PlurkAPIError:
        return None


def get_username_by_id(user_id: int) -> Optional[str]:
    """通过 user_id 查询 nick_name，结果 LRU 缓存"""
    return _cached_get_username(user_id)


# ── Plurk API 封装 ────────────────────────────────────────────

def add_plurk(content: str, qualifier: str = ":") -> dict:
    """发布新帖子"""
    return _request("POST", "/Timeline/plurkAdd",
                    content=content,
                    qualifier=qualifier,
                    lang="tr_ch")


def response_plurk(plurk_id: int, content: str) -> dict:
    """回复帖子"""
    return _request("POST", "/Responses/responseAdd",
                    plurk_id=plurk_id,
                    content=content,
                    qualifier=":")


def get_plurks(offset: Optional[str] = None, limit: int = 20) -> dict:
    """获取时间线"""
    params: dict[str, Any] = {"limit": min(max(limit, 1), 30)}
    if offset:
        params["offset"] = offset
    return _request("GET", "/Timeline/getPlurks", **params)


def get_responses(plurk_id: int) -> dict:
    """获取帖子回复列表"""
    return _request("GET", "/Responses/get", plurk_id=plurk_id)


def delete_plurk(plurk_id: int) -> dict:
    """删除帖子"""
    return _request("POST", "/Timeline/plurkDelete", plurk_id=plurk_id)


def get_public_profile(username: str) -> dict:
    """获取指定用户公开资料"""
    return _request("GET", "/Users/getPublicProfile", user_id=username)


def get_own_profile() -> dict:
    """获取当前登录账号资料"""
    return _request("GET", "/Users/me")


def like_plurk(plurk_id: int) -> dict:
    """点赞帖子（通过 mute 接口实现 like）"""
    return _request("POST", "/Timeline/mutePlurks",
                    ids=f"[{plurk_id}]")
