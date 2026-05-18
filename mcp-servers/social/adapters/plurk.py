"""
PlurkAdapter — 单个 Plurk 账号的封装
将 plurk_client.py + auth.py 逻辑迁移为类实例方法，支持多账号独立 session
"""
import functools
import logging
import time
from typing import Any, Optional

import requests
from requests_oauthlib import OAuth1Session

from adapters.base import BaseAdapter, SocialAPIError

logger = logging.getLogger(__name__)

PLURK_API_BASE = "https://www.plurk.com/APP"
PLURK_LOGIN_URL = "https://www.plurk.com/Users/login"
MAX_RETRIES = 3
RETRY_INTERVAL = 5


class PlurkAdapter(BaseAdapter):
    def __init__(self, account_id: str, auth_mode: str = "oauth",
                 app_key: str = "", app_secret: str = "",
                 access_token: str = "", access_token_secret: str = "",
                 username: str = "", password: str = ""):
        super().__init__(account_id, "plurk")
        self.auth_mode = auth_mode.lower()
        self._app_key = app_key
        self._app_secret = app_secret
        self._access_token = access_token
        self._access_token_secret = access_token_secret
        self._username = username
        self._password = password
        self._session: Optional[OAuth1Session | requests.Session] = None
        # 实例级 LRU 缓存（通过字典模拟，避免 functools.lru_cache 跨实例共享）
        self._username_cache: dict[int, Optional[str]] = {}

    def init(self) -> None:
        """初始化认证 session"""
        if self.auth_mode == "oauth":
            self._session = self._init_oauth()
        elif self.auth_mode == "password":
            self._session = self._init_password()
        else:
            raise ValueError(f"不支持的 auth_mode：'{self.auth_mode}'，支持：oauth / password")

    def _init_oauth(self) -> OAuth1Session:
        if not all([self._app_key, self._app_secret, self._access_token, self._access_token_secret]):
            raise ValueError(f"[{self.account_id}] OAuth 凭据不完整，请检查 app_key/app_secret/access_token/access_token_secret")
        session = OAuth1Session(
            client_key=self._app_key,
            client_secret=self._app_secret,
            resource_owner_key=self._access_token,
            resource_owner_secret=self._access_token_secret,
        )
        resp = session.get(f"{PLURK_API_BASE}/Users/me")
        if resp.status_code == 401:
            raise PermissionError(f"[{self.account_id}] OAuth 凭据无效")
        resp.raise_for_status()
        return session

    def _init_password(self) -> requests.Session:
        if not self._username or not self._password:
            raise ValueError(f"[{self.account_id}] 密码模式需要配置 username 和 password")
        session = requests.Session()
        session.headers.update({"User-Agent": "Mozilla/5.0 (compatible; SocialMCPBot/1.0)"})
        resp = session.post(PLURK_LOGIN_URL, data={
            "nick_name": self._username, "password": self._password
        })
        resp.raise_for_status()
        check = session.get(f"{PLURK_API_BASE}/Users/me")
        if check.status_code == 401:
            raise PermissionError(f"[{self.account_id}] 账号密码登录失败")
        return session

    def _reauth(self) -> None:
        logger.info(f"[{self.account_id}] session 过期，重新认证...")
        self.init()

    def _request(self, method: str, endpoint: str, _reauth_attempted: bool = False, **params) -> dict:
        url = f"{PLURK_API_BASE}{endpoint}"
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                if method.upper() == "GET":
                    resp = self._session.get(url, params=params)
                else:
                    resp = self._session.post(url, data=params)

                if resp.status_code == 401 and not _reauth_attempted:
                    self._reauth()
                    return self._request(method, endpoint, _reauth_attempted=True, **params)

                if not resp.ok:
                    try:
                        body = resp.json()
                    except Exception:
                        body = {}
                    raise self._map_error(resp.status_code, body)

                return resp.json()

            except SocialAPIError:
                raise
            except (requests.ConnectionError, requests.Timeout) as e:
                if attempt < MAX_RETRIES:
                    logger.warning(f"[{self.account_id}] 网络错误，{RETRY_INTERVAL}s 后重试 ({attempt}/{MAX_RETRIES})")
                    time.sleep(RETRY_INTERVAL)
                else:
                    raise SocialAPIError("NETWORK_ERROR", f"网络错误，已重试 {MAX_RETRIES} 次：{e}")

        raise SocialAPIError("NETWORK_ERROR", f"请求失败，已重试 {MAX_RETRIES} 次")

    @staticmethod
    def _map_error(status_code: int, body: dict) -> SocialAPIError:
        text = body.get("error_text", "")
        if status_code == 401:
            return SocialAPIError("AUTH_FAILED", f"认证失败：{text}", status_code)
        if status_code == 403:
            return SocialAPIError("FORBIDDEN", f"无权限：{text}", status_code)
        if status_code == 404:
            return SocialAPIError("NOT_FOUND", f"资源不存在：{text}", status_code)
        if status_code == 429:
            return SocialAPIError("RATE_LIMITED", f"请求过频：{text}", status_code)
        return SocialAPIError("API_ERROR", f"API 错误 {status_code}：{text}", status_code)

    def get_username_by_id(self, user_id: int) -> Optional[str]:
        """通过 user_id 查询 nick_name，结果缓存于实例字典"""
        if user_id in self._username_cache:
            return self._username_cache[user_id]
        try:
            data = self._request("GET", "/Users/getPublicProfile", user_id=user_id)
            user_info = data.get("user_info") or data
            nick = user_info.get("nick_name") or user_info.get("display_name")
        except SocialAPIError:
            nick = None
        self._username_cache[user_id] = nick
        return nick

    # ── Plurk API 方法 ────────────────────────────────

    def post(self, content: str, qualifier: str = ":") -> dict:
        return self._request("POST", "/Timeline/plurkAdd",
                             content=content, qualifier=qualifier, lang="tr_ch")

    def reply(self, plurk_id: int, content: str) -> dict:
        return self._request("POST", "/Responses/responseAdd",
                             plurk_id=plurk_id, content=content, qualifier=":")

    def get_timeline(self, offset: Optional[str] = None, limit: int = 20) -> dict:
        params: dict[str, Any] = {"limit": min(max(limit, 1), 30)}
        if offset:
            params["offset"] = offset
        return self._request("GET", "/Timeline/getPlurks", **params)

    def get_responses(self, plurk_id: int) -> dict:
        return self._request("GET", "/Responses/get", plurk_id=plurk_id)

    def delete_plurk(self, plurk_id: int) -> dict:
        return self._request("POST", "/Timeline/plurkDelete", plurk_id=plurk_id)

    def get_public_profile(self, username: str) -> dict:
        return self._request("GET", "/Users/getPublicProfile", user_id=username)

    def get_own_profile(self) -> dict:
        return self._request("GET", "/Users/me")

    def like_plurk(self, plurk_id: int) -> dict:
        return self._request("POST", "/Timeline/mutePlurks", ids=f"[{plurk_id}]")
