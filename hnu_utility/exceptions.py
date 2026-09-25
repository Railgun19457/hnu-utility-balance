"""异常体系。"""

from __future__ import annotations

from typing import Any, Optional, Union


class HnuError(Exception):
    """所有异常的基类。"""


class HnuNetworkError(HnuError):
    """网络请求失败（超时、连接错误等），对应 :class:`httpx.HTTPError`。"""

    def __init__(self, message: str, *, url: Optional[str] = None) -> None:
        super().__init__(message)
        self.url = url


class HnuResponseError(HnuError):
    """响应不符合预期：HTTP 状态码非 200、非 JSON、或结构异常。"""

    def __init__(
        self,
        message: str,
        *,
        status_code: Optional[int] = None,
        body: Optional[str] = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.body = body


class HnuApiError(HnuError):
    """业务错误：HTTP 200，但响应中的 ``statusCode`` 不是 ``"200"``。

    常见情况：

    - ``500``：参数缺失、签名校验失败、服务端无数据等；
    - ``201``：调用合法但没有数据（部分接口用它表示"无记录"）。
    """

    def __init__(
        self,
        code: Union[str, int, None],
        message: Optional[str] = None,
        *,
        result: Any = None,
        http_status: Optional[int] = None,
    ) -> None:
        self.code = code
        self.message = message
        self.result = result
        self.http_status = http_status
        super().__init__(f"[{code}] {message or '未知错误'}")

    @property
    def is_no_data(self) -> bool:
        """是否为"无数据"类业务码（201）。"""
        return str(self.code) == "201"
