"""常量与枚举定义。"""

from __future__ import annotations

from enum import IntEnum

__version__ = "0.1.0"

BASE_URL = "https://sdxt.hainanu.edu.cn/scanQRWaterCtrl_redis_hndx1/service"

APP_ID = "sz@cgdz#2021$11"
APP_SECRET = "&szcgdz"

DEFAULT_TIMEOUT = 10.0
DEFAULT_RETRIES = 2

USER_AGENT = f"hnu-utility-balance/{__version__}"


class EleType(IntEnum):
    """电表类型（``/weixinEle/getEleInfo`` 的 ``type`` 参数）。"""

    LIGHT = 1
    """照明 + 插座。"""

    AIR = 2
    """空调。"""


class ConsumeType(IntEnum):
    """费用类型（充值记录类接口的 ``consumeType`` 参数）。"""

    WATER_CTRL = 1
    """水控（扫码 / 蓝牙取水）。"""

    ELECTRICITY = 2
    """电（照明 / 空调）。"""

    WATER = 3
    """水表。"""


class RoomType(IntEnum):
    """房间类型（``/weixinEle/getRoomBuyInfo`` 的 ``roomType`` 参数）。"""

    LIGHT = 1
    """照明房间。"""

    AIR = 2
    """空调房间。"""

    WATER = 3
    """水表房间。"""
