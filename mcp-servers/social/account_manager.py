"""
AccountManager — 多平台多账号 session 池管理
负责加载 accounts.yaml、初始化各平台 Adapter、提供 get/get_prompt 查询接口
"""
import logging
import os
import subprocess
from typing import Optional

import yaml

from adapters.base import BaseAdapter, SocialAPIError

logger = logging.getLogger(__name__)


class AccountNotFoundError(SocialAPIError):
    def __init__(self, account_id: str):
        super().__init__("ACCOUNT_NOT_FOUND", f"Account '{account_id}' not found")


class AccountInitFailedError(SocialAPIError):
    def __init__(self, account_id: str, reason: str):
        super().__init__("ACCOUNT_INIT_FAILED",
                         f"Account '{account_id}' failed to initialize: {reason}")


class AccountManager:
    def __init__(self, config_path: str):
        self.config_path = config_path
        self._adapters: dict[str, BaseAdapter] = {}
        self._failed: dict[str, str] = {}          # account_id → error message
        self._prompt_groups: dict[str, dict] = {}
        self._account_groups: dict[str, Optional[str]] = {}  # account_id → group name

    def load(self) -> None:
        """加载 accounts.yaml，初始化所有账号，跳过失败账号"""
        if not os.path.exists(self.config_path):
            raise FileNotFoundError(
                f"accounts.yaml not found at '{self.config_path}'.\n"
                f"Please copy accounts.yaml.example to accounts.yaml and fill in your credentials."
            )

        self._check_git_tracked()

        with open(self.config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f) or {}

        # 加载 prompt_groups
        self._prompt_groups = config.get("prompt_groups") or {}

        accounts = config.get("accounts") or []
        if not accounts:
            logger.warning("accounts.yaml 中没有找到任何账号配置")

        for account_cfg in accounts:
            account_id = account_cfg.get("id")
            platform = account_cfg.get("platform", "").lower()
            group = account_cfg.get("group")

            if not account_id:
                logger.warning("跳过一条缺少 id 字段的账号配置")
                continue

            self._account_groups[account_id] = group

            try:
                adapter = self._create_adapter(account_id, platform, account_cfg)
                adapter.init()
                self._adapters[account_id] = adapter
                logger.info(f"✓ [{platform}] {account_id} 初始化成功")
            except Exception as e:
                msg = str(e)
                self._failed[account_id] = msg
                logger.warning(f"[WARN] account '{account_id}' init failed: {msg}")

        # 打印汇总
        total = len(accounts)
        ok_count = len(self._adapters)
        fail_count = len(self._failed)
        logger.info(f"账号初始化完成：{ok_count}/{total} 成功，{fail_count} 失败")

    def _create_adapter(self, account_id: str, platform: str, cfg: dict) -> BaseAdapter:
        """根据 platform 创建对应 Adapter"""
        # 延迟导入避免循环依赖
        from adapters.plurk import PlurkAdapter
        from adapters.facebook import FacebookAdapter
        from adapters.twitter import TwitterAdapter

        if platform == "plurk":
            return PlurkAdapter(
                account_id=account_id,
                auth_mode=cfg.get("auth_mode", "oauth"),
                app_key=cfg.get("app_key", ""),
                app_secret=cfg.get("app_secret", ""),
                access_token=cfg.get("access_token", ""),
                access_token_secret=cfg.get("access_token_secret", ""),
                username=cfg.get("username", ""),
                password=cfg.get("password", ""),
            )
        elif platform == "facebook":
            return FacebookAdapter(
                account_id=account_id,
                page_id=cfg.get("page_id", ""),
                page_access_token=cfg.get("page_access_token", ""),
            )
        elif platform == "x":
            return TwitterAdapter(
                account_id=account_id,
                api_key=cfg.get("api_key", ""),
                api_secret=cfg.get("api_secret", ""),
                access_token=cfg.get("access_token", ""),
                access_token_secret=cfg.get("access_token_secret", ""),
            )
        else:
            raise ValueError(f"不支持的平台：'{platform}'，支持：plurk / facebook / x")

    def get(self, account_id: str) -> BaseAdapter:
        """获取指定账号的 Adapter，不存在时抛出异常"""
        if account_id in self._adapters:
            return self._adapters[account_id]
        if account_id in self._failed:
            raise AccountInitFailedError(account_id, self._failed[account_id])
        raise AccountNotFoundError(account_id)

    def get_prompt(self, account_id: str) -> dict:
        """获取账号绑定的 prompt 分组内容"""
        # 账号不存在
        if account_id not in self._adapters and account_id not in self._failed \
                and account_id not in self._account_groups:
            raise AccountNotFoundError(account_id)

        group = self._account_groups.get(account_id)

        # 未配置 group，返回空 prompt
        if not group:
            return {"group": None, "post_prompt": None, "reply_prompt": None, "language": None}

        # group 不存在
        if group not in self._prompt_groups:
            raise SocialAPIError("GROUP_NOT_FOUND",
                                 f"Prompt group '{group}' not found in accounts.yaml")

        pg = self._prompt_groups[group]
        return {
            "group": group,
            "post_prompt": pg.get("post_prompt"),
            "reply_prompt": pg.get("reply_prompt"),
            "language": pg.get("language"),
        }

    def list_accounts(self) -> list[dict]:
        """返回所有账号状态列表"""
        result = [
            {"id": aid, "platform": adapter.platform, "status": "ok"}
            for aid, adapter in self._adapters.items()
        ]
        result += [
            {"id": aid, "platform": "unknown", "status": "failed", "error": msg}
            for aid, msg in self._failed.items()
        ]
        return result

    def _check_git_tracked(self) -> None:
        """检查 accounts.yaml 是否被 git 追踪，若是则发出安全警告"""
        try:
            result = subprocess.run(
                ["git", "ls-files", os.path.basename(self.config_path)],
                capture_output=True, text=True,
                cwd=os.path.dirname(os.path.abspath(self.config_path))
            )
            if result.stdout.strip():
                logger.warning(
                    "⚠️  安全警告：accounts.yaml 正被 git 追踪，凭据可能泄露！"
                    "请执行 `git rm --cached accounts.yaml` 并确认 .gitignore 已包含该文件"
                )
        except Exception:
            pass
