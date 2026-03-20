"""
Plurk MCP Server 认证模块
支持 OAuth 1.0a 和账号密码模拟登录双模式
"""
import logging
import os
import subprocess
from typing import Optional

import requests
from requests_oauthlib import OAuth1Session

logger = logging.getLogger(__name__)

PLURK_LOGIN_URL = "https://www.plurk.com/Users/login"
PLURK_API_BASE = "https://www.plurk.com/APP"

# 全局认证单例
_oauth_session: Optional[OAuth1Session] = None
_password_session: Optional[requests.Session] = None
_auth_mode: Optional[str] = None


def _check_env_git_tracked() -> None:
    """检查 .env 是否被 git 追踪，若是则发出安全警告"""
    try:
        result = subprocess.run(
            ["git", "ls-files", ".env"],
            capture_output=True, text=True, cwd=os.path.dirname(__file__)
        )
        if result.stdout.strip():
            logger.warning(
                "⚠️  安全警告：.env 文件正被 git 追踪，凭据可能泄露！"
                "请执行 `git rm --cached .env` 并将 .env 加入 .gitignore"
            )
    except Exception:
        pass  # git 不可用时忽略


def _get_required_env(key: str) -> str:
    """获取必填环境变量，缺失时抛出 ValueError"""
    val = os.environ.get(key, "").strip()
    if not val:
        raise ValueError(f"缺少必填环境变量：{key}")
    return val


def _init_oauth() -> OAuth1Session:
    """初始化 OAuth 1.0a 认证"""
    app_key = _get_required_env("PLURK_APP_KEY")
    app_secret = _get_required_env("PLURK_APP_SECRET")
    access_token = _get_required_env("PLURK_ACCESS_TOKEN")
    access_token_secret = _get_required_env("PLURK_ACCESS_TOKEN_SECRET")

    session = OAuth1Session(
        client_key=app_key,
        client_secret=app_secret,
        resource_owner_key=access_token,
        resource_owner_secret=access_token_secret,
    )
    # 验证 token 有效性
    resp = session.get(f"{PLURK_API_BASE}/Users/me")
    if resp.status_code == 401:
        raise PermissionError("OAuth 凭据无效，请检查 PLURK_APP_KEY / PLURK_APP_SECRET / PLURK_ACCESS_TOKEN / PLURK_ACCESS_TOKEN_SECRET")
    resp.raise_for_status()
    logger.info("✓ Plurk OAuth 认证成功")
    return session


def _init_password() -> requests.Session:
    """初始化账号密码模拟登录"""
    username = _get_required_env("PLURK_USERNAME")
    password = _get_required_env("PLURK_PASSWORD")

    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (compatible; PlurkMCPBot/1.0)",
        "Content-Type": "application/x-www-form-urlencoded",
    })
    resp = session.post(PLURK_LOGIN_URL, data={"nick_name": username, "password": password})
    resp.raise_for_status()

    # 模拟登录成功时会设置 plurkcookie
    if "plurkcookie" not in session.cookies and resp.status_code != 200:
        raise PermissionError("账号密码登录失败，请检查 PLURK_USERNAME / PLURK_PASSWORD")

    # 二次验证：尝试访问 /APP/Users/me
    check = session.get(f"{PLURK_API_BASE}/Users/me")
    if check.status_code == 401:
        raise PermissionError("模拟登录后 API 访问失败，凭据可能不正确")

    logger.info("✓ Plurk 账号密码模拟登录成功")
    return session


def init_auth() -> None:
    """根据 PLURK_AUTH_MODE 初始化认证，启动时调用一次"""
    global _oauth_session, _password_session, _auth_mode

    _check_env_git_tracked()

    mode = os.environ.get("PLURK_AUTH_MODE", "oauth").strip().lower()
    _auth_mode = mode

    if mode == "oauth":
        _oauth_session = _init_oauth()
    elif mode == "password":
        _password_session = _init_password()
    else:
        raise ValueError(f"PLURK_AUTH_MODE 值无效：'{mode}'，支持：oauth / password")


def get_session() -> OAuth1Session | requests.Session:
    """获取当前认证 session，若未初始化则抛出异常"""
    if _auth_mode == "oauth" and _oauth_session is not None:
        return _oauth_session
    if _auth_mode == "password" and _password_session is not None:
        return _password_session
    raise RuntimeError("认证未初始化，请先调用 init_auth()")


def reauth() -> None:
    """重新认证（session 过期时调用）"""
    global _oauth_session, _password_session
    logger.info("Session 过期，触发重新认证...")
    if _auth_mode == "oauth":
        _oauth_session = _init_oauth()
    elif _auth_mode == "password":
        _password_session = _init_password()
