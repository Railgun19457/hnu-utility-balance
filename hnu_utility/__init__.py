"""海南大学「海大售电」水电费接口的 Python 客户端库。

同步用法::

    from hnu_utility import HnuUtilityClient

    with HnuUtilityClient("ofDET4_xxx") as client:
        wx_user = client.get_wx_user()
        light = client.get_ele_info()          # 照明
        air = client.get_ele_info("2")         # 空调（支持字符串）

异步用法见 :class:`~hnu_utility.client.AsyncHnuUtilityClient`。
"""

from __future__ import annotations

from .client import AsyncHnuUtilityClient, BaseClient, HnuUtilityClient
from .config import load_config, load_open_id
from .const import (
    APP_ID,
    APP_SECRET,
    BASE_URL,
    DEFAULT_RETRIES,
    DEFAULT_TIMEOUT,
    USER_AGENT,
    ConsumeType,
    EleType,
    RoomType,
    __version__,
)
from .discovery import default_search_paths, scan_open_ids
from .exceptions import HnuApiError, HnuError, HnuNetworkError, HnuResponseError
from .models import (
    BuyOrder,
    BuyRecord,
    ConsumeRecord,
    EleInfo,
    NamedItem,
    PersonalBuyInfo,
    RoomBuyInfo,
    RoomBuyRecord,
    UsedEleInfo,
    User,
    WaterInfo,
    WxUser,
    parse_list,
)

__all__ = [
    "__version__",
    "APP_ID",
    "APP_SECRET",
    "BASE_URL",
    "DEFAULT_RETRIES",
    "DEFAULT_TIMEOUT",
    "USER_AGENT",
    "ConsumeType",
    "EleType",
    "RoomType",
    "BaseClient",
    "HnuUtilityClient",
    "AsyncHnuUtilityClient",
    "default_search_paths",
    "scan_open_ids",
    "HnuError",
    "HnuApiError",
    "HnuNetworkError",
    "HnuResponseError",
    "BuyOrder",
    "BuyRecord",
    "ConsumeRecord",
    "EleInfo",
    "NamedItem",
    "PersonalBuyInfo",
    "RoomBuyInfo",
    "RoomBuyRecord",
    "UsedEleInfo",
    "User",
    "WaterInfo",
    "WxUser",
    "load_config",
    "load_open_id",
    "parse_list",
]
