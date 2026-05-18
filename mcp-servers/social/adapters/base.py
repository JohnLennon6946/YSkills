"""BaseAdapter — 各平台 Adapter 的统一抽象接口"""
from abc import ABC, abstractmethod


class SocialAPIError(Exception):
    """统一 API 错误"""
    def __init__(self, code: str, message: str, status_code: int = 0):
        self.code = code
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class BaseAdapter(ABC):
    """各平台 Adapter 必须继承此类"""

    def __init__(self, account_id: str, platform: str):
        self.account_id = account_id
        self.platform = platform

    @abstractmethod
    def init(self) -> None:
        """初始化认证，启动时调用"""

    @abstractmethod
    def post(self, **kwargs) -> dict:
        """发帖"""

    @abstractmethod
    def reply(self, **kwargs) -> dict:
        """回复"""
