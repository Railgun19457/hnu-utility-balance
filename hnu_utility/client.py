"""同步 / 异步客户端。

本模块是全库的核心：封装了「海大售电」小程序后端的全部查询类接口，
以及房间绑定 / 解绑操作。

示例（同步）::

    from hnu_utility import HnuUtilityClient

    with HnuUtilityClient("ofDET4_xxx") as client:
        wx_user = client.get_wx_user()
        print(wx_user.user.real_name, wx_user.user.total_money)

示例（异步）::

    import asyncio
    from hnu_utility import AsyncHnuUtilityClient

    async def main():
        async with AsyncHnuUtilityClient("ofDET4_xxx") as client:
            wx_user = await client.get_wx_user()
            print(wx_user.user.real_name)

    asyncio.run(main())

未封装的接口（支付、蓝牙控水、上传等）可以通过 :meth:`raw_request` 直接调用。
"""

from __future__ import annotations

import hashlib
import time
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, Optional, Union

import httpx

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
)
from .exceptions import HnuApiError, HnuNetworkError, HnuResponseError
from .models import (
    BuyOrder,
    ConsumeRecord,
    EleInfo,
    NamedItem,
    PersonalBuyInfo,
    RoomBuyInfo,
    UsedEleInfo,
    User,
    WaterInfo,
    WxUser,
    parse_list,
)

__all__ = ["BaseClient", "HnuUtilityClient", "AsyncHnuUtilityClient"]

_Num = Union[int, float]


class BaseClient:
    """同步 / 异步客户端共享的配置、签名与响应解析逻辑。"""

    def __init__(
        self,
        open_id: Optional[str] = None,
        *,
        base_url: str = BASE_URL,
        app_id: str = APP_ID,
        app_secret: str = APP_SECRET,
        timeout: _Num = DEFAULT_TIMEOUT,
        retries: int = DEFAULT_RETRIES,
        verify: Union[bool, str] = True,
        headers: Optional[Mapping[str, str]] = None,
        user_agent: str = USER_AGENT,
    ) -> None:
        self._open_id = open_id
        self._base_url = base_url.rstrip("/")
        self._app_id = app_id
        self._app_secret = app_secret
        self.timeout = timeout
        self.retries = retries
        self.verify = verify
        self._headers: dict[str, str] = {
            "User-Agent": user_agent,
            "Accept": "application/json",
        }
        if headers:
            self._headers.update(headers)

    # ── 基础属性 ────────────────────────────────────────────────

    @property
    def open_id(self) -> Optional[str]:
        """当前使用的 openId。"""
        return self._open_id

    @open_id.setter
    def open_id(self, value: Optional[str]) -> None:
        self._open_id = value

    @property
    def base_url(self) -> str:
        """接口根地址（默认海大部署地址，可换成其他学校的同款部署）。"""
        return self._base_url

    @property
    def app_id(self) -> str:
        return self._app_id

    @property
    def app_secret(self) -> str:
        return self._app_secret

    # ── 签名与参数 ──────────────────────────────────────────────

    def sign(self, timestamp: int) -> str:
        """计算 ``MD5(appid + timestamp + appSecret)``。"""
        raw = f"{self._app_id}{timestamp}{self._app_secret}"
        return hashlib.md5(raw.encode("utf-8"), usedforsecurity=False).hexdigest()

    def _require_open_id(self) -> str:
        if not self._open_id:
            raise ValueError("此接口需要 openId，请先提供（hnu_config.json 或构造参数）")
        return self._open_id

    def _open_id_params(self) -> dict[str, Any]:
        return {"openId": self._require_open_id()}

    def _signed_params(self) -> dict[str, Any]:
        timestamp = int(time.time() * 1000)
        return {
            "openId": self._require_open_id(),
            "appid": self._app_id,
            "timestamp": timestamp,
            "sign": self.sign(timestamp),
        }

    def _url(self, path: str) -> str:
        if path.startswith(("http://", "https://")):
            return path
        return f"{self._base_url}/{path.lstrip('/')}"

    # ── 响应解析 ────────────────────────────────────────────────

    @staticmethod
    def _network_error(exc: httpx.HTTPError) -> HnuNetworkError:
        url = str(exc.request.url) if exc.request is not None else None
        return HnuNetworkError(f"请求失败：{exc}", url=url)

    @staticmethod
    def _parse_response(response: httpx.Response) -> Mapping[str, Any]:
        if response.status_code != 200:
            raise HnuResponseError(
                f"HTTP {response.status_code}",
                status_code=response.status_code,
                body=response.text[:500],
            )
        try:
            payload = response.json()
        except ValueError as exc:
            raise HnuResponseError(
                "响应不是合法 JSON",
                status_code=response.status_code,
                body=response.text[:500],
            ) from exc
        if not isinstance(payload, Mapping):
            raise HnuResponseError(
                "响应结构异常",
                status_code=response.status_code,
                body=response.text[:500],
            )
        return payload

    @staticmethod
    def _unwrap(payload: Mapping[str, Any]) -> Any:
        code = payload.get("statusCode")
        if str(code) != "200":
            raise HnuApiError(
                code,
                payload.get("message"),
                result=payload.get("resultObject"),
            )
        return payload.get("resultObject")

    @classmethod
    def _list(cls, model: Any, payload: Mapping[str, Any]) -> list[Any]:
        return parse_list(model, cls._unwrap(payload))


class _EndpointMixin:
    """全部接口方法的参数构造逻辑（同步 / 异步共用）。"""

    if TYPE_CHECKING:

        def _signed_params(self) -> dict[str, Any]: ...

        def _open_id_params(self) -> dict[str, Any]: ...

    # ── 用户与余额 ──────────────────────────────────────────────

    def _p_get_wx_user(self) -> Mapping[str, Any]:
        return self._signed_params()

    def _p_get_user(self) -> Mapping[str, Any]:
        return self._open_id_params()

    def _p_get_left_money(self) -> Mapping[str, Any]:
        return self._signed_params()

    def _p_get_ele_info(self, ele_type: Union[EleType, int, str]) -> Mapping[str, Any]:
        return {**self._open_id_params(), "type": int(ele_type)}

    def _p_get_water_info(self) -> Mapping[str, Any]:
        return self._open_id_params()

    # ── 充值 / 消费记录 ─────────────────────────────────────────

    def _p_get_personal_buy_info(self, consume_type: Union[ConsumeType, int]) -> Mapping[str, Any]:
        return {**self._open_id_params(), "consumeType": int(consume_type)}

    def _p_get_room_buy_info(
        self,
        consume_type: Union[ConsumeType, int],
        room_type: Union[RoomType, int],
    ) -> Mapping[str, Any]:
        return {
            **self._open_id_params(),
            "consumeType": int(consume_type),
            "roomType": int(room_type),
        }

    def _p_get_buy_orders(self, school_name: str) -> Mapping[str, Any]:
        return {**self._open_id_params(), "schoolName": school_name}

    def _p_get_consume_records(self, school_name: str) -> Mapping[str, Any]:
        return {**self._open_id_params(), "schoolName": school_name}

    def _p_get_last_consume(self) -> Mapping[str, Any]:
        return self._open_id_params()

    def _p_get_ele_used_info(self) -> Mapping[str, Any]:
        return self._open_id_params()

    # ── 校区 / 楼栋 / 房间 ──────────────────────────────────────

    def _p_get_buildings(
        self,
        school_id: Union[str, int],
        school_name: str,
        ele_type: Union[EleType, int],
        keyword: str,
    ) -> Mapping[str, Any]:
        return {
            "schoolId": str(school_id),
            "schoolName": school_name,
            "type": int(ele_type),
            "loudongInfo": keyword,
        }

    def _p_get_water_buildings(
        self,
        school_id: Union[str, int],
        school_name: str,
        keyword: str,
    ) -> Mapping[str, Any]:
        return {
            "schoolId": str(school_id),
            "schoolName": school_name,
            "type": 1,
            "loudongInfo": keyword,
        }

    def _p_get_rooms(self, lou_dong_id: Union[str, int], keyword: str) -> Mapping[str, Any]:
        return {"louDongId": str(lou_dong_id), "roomInfo": keyword}

    # ── 房间绑定 / 解绑 ─────────────────────────────────────────

    def _p_save_room_info(
        self,
        xiao_qu_id: Union[str, int],
        xiao_qu_name: str,
        lou_dong_id: Union[str, int],
        lou_dong_name: str,
        room_id: Union[str, int],
        kt_lou_dong_id: Union[str, int],
        kt_lou_dong_name: str,
        kt_room_id: Union[str, int],
    ) -> Mapping[str, Any]:
        return {
            **self._open_id_params(),
            "xiaoquId": xiao_qu_id,
            "xiaoQuName": xiao_qu_name,
            "loudongName": lou_dong_name,
            "loudongId": lou_dong_id,
            "ktLouDongName": kt_lou_dong_name,
            "ktLoudongId": kt_lou_dong_id,
            "roomId": room_id,
            "ktRoomId": kt_room_id,
        }

    def _p_save_water_room_info(
        self,
        xiao_qu_id: Union[str, int],
        xiao_qu_name: str,
        lou_dong_id: Union[str, int],
        lou_dong_name: str,
        room_id: Union[str, int],
        room_name: str,
    ) -> Mapping[str, Any]:
        return {
            **self._open_id_params(),
            "xiaoquId": xiao_qu_id,
            "xiaoQuName": xiao_qu_name,
            "loudongName": lou_dong_name,
            "loudongId": lou_dong_id,
            "roomId": room_id,
            "roomName": room_name,
        }

    def _p_clear_room(self) -> Mapping[str, Any]:
        return self._open_id_params()

    # ── 其他 ────────────────────────────────────────────────────

    def _p_get_info_url(self, school_name: str) -> Mapping[str, Any]:
        return {"schoolName": school_name, "type": "weixin"}

    def _p_exchange_code(self, code: str) -> Mapping[str, Any]:
        return {"code": code}


class HnuUtilityClient(_EndpointMixin, BaseClient):
    """同步客户端（基于 ``httpx.Client``）。

    参数
    ----
    open_id:
        ``hnu_config.json`` 里的 openId；仅调用校区 / 楼栋 / 房间列表时可以不给。
    transport:
        自定义 ``httpx.BaseTransport``（测试时可传 ``httpx.MockTransport``）。
    client:
        复用外部 ``httpx.Client``；此时 ``timeout`` / ``retries`` / ``verify`` /
        ``headers`` 以该对象为准，:meth:`close` 也不会关闭它。

    其余参数（``base_url`` / ``timeout`` / ``retries`` / ``verify`` 等）见
    :class:`BaseClient`。
    """

    def __init__(
        self,
        open_id: Optional[str] = None,
        *,
        transport: Optional[httpx.BaseTransport] = None,
        client: Optional[httpx.Client] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(open_id, **kwargs)
        if client is not None:
            self._client = client
            self._owns_client = False
        else:
            if transport is None:
                transport = httpx.HTTPTransport(retries=self.retries)
            self._client = httpx.Client(
                timeout=self.timeout,
                verify=self.verify,
                headers=self._headers,
                transport=transport,
            )
            self._owns_client = True

    # ── 生命周期 ────────────────────────────────────────────────

    def close(self) -> None:
        """关闭底层连接池（外部传入的 client 不会被关闭）。"""
        if self._owns_client:
            self._client.close()

    def __enter__(self) -> HnuUtilityClient:
        return self

    def __exit__(self, *exc_info: Any) -> None:
        self.close()

    # ── 底层请求 ────────────────────────────────────────────────

    def _get_payload(self, path: str, params: Mapping[str, Any]) -> Mapping[str, Any]:
        try:
            response = self._client.get(self._url(path), params=dict(params))
        except httpx.HTTPError as exc:
            raise self._network_error(exc) from exc
        return self._parse_response(response)

    def _get(self, path: str, params: Mapping[str, Any]) -> Any:
        return self._unwrap(self._get_payload(path, params))

    def _call_message(self, path: str, params: Mapping[str, Any]) -> Optional[str]:
        payload = self._get_payload(path, params)
        self._unwrap(payload)
        message = payload.get("message")
        return None if message is None else str(message)

    def raw_request(
        self,
        path: str,
        params: Optional[Mapping[str, Any]] = None,
        *,
        signed: bool = False,
        with_open_id: bool = True,
    ) -> Any:
        """直接调用任意接口（未封装接口的逃生通道）。

        - ``signed=True`` 时自动附带 ``openId/appid/timestamp/sign``；
        - 否则 ``with_open_id=True`` 时附带 ``openId``；
        - ``params`` 中的键会覆盖自动生成的参数。
        """
        merged: dict[str, Any] = {}
        if signed:
            merged.update(self._signed_params())
        elif with_open_id:
            merged.update(self._open_id_params())
        if params:
            merged.update(params)
        return self._get(path, merged)

    # ── 用户与余额 ──────────────────────────────────────────────

    def get_wx_user(self) -> WxUser:
        """获取用户信息、房间绑定与热水余额（``/applet/getWxUser``，需签名）。"""
        return WxUser.from_dict(self._get("/applet/getWxUser", self._p_get_wx_user()))

    def get_user(self) -> User:
        """获取完整用户实体（``/applet/getUser``，字段比 getWxUser 更多）。"""
        return User.from_dict(self._get("/applet/getUser", self._p_get_user()))

    def get_left_money(self) -> User:
        """获取热水账户（``/applet/getLeftMoney``，需签名，返回结构与 ``getWxUser().user`` 相同）。"""
        return User.from_dict(self._get("/applet/getLeftMoney", self._p_get_left_money()))

    def get_ele_info(self, ele_type: Union[EleType, int, str] = EleType.LIGHT) -> EleInfo:
        """获取照明（``EleType.LIGHT``）或空调（``EleType.AIR``）余额。"""
        return EleInfo.from_dict(self._get("/weixinEle/getEleInfo", self._p_get_ele_info(ele_type)))

    def get_water_info(self) -> WaterInfo:
        """获取水表余额。"""
        return WaterInfo.from_dict(self._get("/weixinEle/getWaterInfo", self._p_get_water_info()))

    # ── 充值 / 消费记录 ─────────────────────────────────────────

    def get_personal_buy_info(
        self,
        consume_type: Union[ConsumeType, int] = ConsumeType.ELECTRICITY,
    ) -> PersonalBuyInfo:
        """个人充值记录（电 / 水，``ConsumeType`` 区分）。"""
        return PersonalBuyInfo.from_dict(
            self._get(
                "/weixinEle/getPersonalBuyInfo",
                self._p_get_personal_buy_info(consume_type),
            )
        )

    def get_room_buy_info(
        self,
        consume_type: Union[ConsumeType, int] = ConsumeType.ELECTRICITY,
        room_type: Union[RoomType, int] = RoomType.LIGHT,
    ) -> RoomBuyInfo:
        """房间充值记录（照明 / 空调 / 水表，``room_type`` 区分）。"""
        return RoomBuyInfo.from_dict(
            self._get(
                "/weixinEle/getRoomBuyInfo",
                self._p_get_room_buy_info(consume_type, room_type),
            )
        )

    def get_buy_orders(self, school_name: str) -> list[BuyOrder]:
        """水控充值订单列表（``/applet/getBuyInfo``）。

        ``school_name`` 可从 ``get_wx_user().user.school_name`` 获取。
        """
        return self._list(BuyOrder, self._get_payload("/applet/getBuyInfo", self._p_get_buy_orders(school_name)))

    def get_consume_records(self, school_name: str) -> list[ConsumeRecord]:
        """水控消费记录列表（``/applet/getConsumeInfo``）。"""
        return self._list(
            ConsumeRecord,
            self._get_payload("/applet/getConsumeInfo", self._p_get_consume_records(school_name)),
        )

    def get_last_consume(self) -> Optional[ConsumeRecord]:
        """最近一次扫码 / 蓝牙用水记录（``/applet/getLastConsume``）。"""
        result = self._get("/applet/getLastConsume", self._p_get_last_consume())
        if not isinstance(result, Mapping):
            return None
        return ConsumeRecord.from_dict(result)

    def get_ele_used_info(self) -> UsedEleInfo:
        """电表用量（``/weixinEle/getEleUsedInfo``）。

        部分部署 / 账户没有用量数据，会抛出 ``HnuApiError``（code=500）。
        """
        return UsedEleInfo.from_dict(self._get("/weixinEle/getEleUsedInfo", self._p_get_ele_used_info()))

    # ── 校区 / 楼栋 / 房间 ──────────────────────────────────────

    def get_schools(self) -> list[NamedItem]:
        """电类校区列表（``/weixinEle/schoolList``）。"""
        return self._list(NamedItem, self._get_payload("/weixinEle/schoolList", {}))

    def get_water_schools(self) -> list[NamedItem]:
        """水类校区列表（``/weixinEle/waterSchoolList``）。"""
        return self._list(NamedItem, self._get_payload("/weixinEle/waterSchoolList", {}))

    def get_buildings(
        self,
        school_id: Union[str, int],
        school_name: str,
        ele_type: Union[EleType, int] = EleType.LIGHT,
        keyword: str = "",
    ) -> list[NamedItem]:
        """校区下电类楼栋列表（``school_louDongList``，``ele_type`` 区分照明 / 空调）。"""
        return self._list(
            NamedItem,
            self._get_payload(
                "/weixinEle/school_louDongList",
                self._p_get_buildings(school_id, school_name, ele_type, keyword),
            ),
        )

    def get_water_buildings(
        self,
        school_id: Union[str, int],
        school_name: str,
        keyword: str = "",
    ) -> list[NamedItem]:
        """校区下水类楼栋列表（``waterSchool_louDongList``）。"""
        return self._list(
            NamedItem,
            self._get_payload(
                "/weixinEle/waterSchool_louDongList",
                self._p_get_water_buildings(school_id, school_name, keyword),
            ),
        )

    def get_rooms(self, lou_dong_id: Union[str, int], keyword: str = "") -> list[NamedItem]:
        """楼栋下电类房间列表（``louDong_roomList``）。"""
        return self._list(
            NamedItem,
            self._get_payload("/weixinEle/louDong_roomList", self._p_get_rooms(lou_dong_id, keyword)),
        )

    def get_water_rooms(self, lou_dong_id: Union[str, int], keyword: str = "") -> list[NamedItem]:
        """楼栋下水表房间列表（``waterLouDong_roomList``）。"""
        return self._list(
            NamedItem,
            self._get_payload("/weixinEle/waterLouDong_roomList", self._p_get_rooms(lou_dong_id, keyword)),
        )

    # ── 房间绑定 / 解绑 ─────────────────────────────────────────

    def save_room_info(
        self,
        *,
        xiao_qu_id: Union[str, int],
        xiao_qu_name: str,
        lou_dong_id: Union[str, int],
        lou_dong_name: str,
        room_id: Union[str, int],
        kt_lou_dong_id: Union[str, int],
        kt_lou_dong_name: str,
        kt_room_id: Union[str, int],
    ) -> Optional[str]:
        """保存电类房间绑定（照明 + 空调），成功返回服务端提示语。

        参数全部为关键字参数，避免顺序搞混；ID 可从 :class:`~hnu_utility.models.NamedItem`
        列表或 ``get_wx_user()`` 获取。
        """
        return self._call_message(
            "/weixinEle/saveRoomInfo",
            self._p_save_room_info(
                xiao_qu_id,
                xiao_qu_name,
                lou_dong_id,
                lou_dong_name,
                room_id,
                kt_lou_dong_id,
                kt_lou_dong_name,
                kt_room_id,
            ),
        )

    def save_water_room_info(
        self,
        *,
        xiao_qu_id: Union[str, int],
        xiao_qu_name: str,
        lou_dong_id: Union[str, int],
        lou_dong_name: str,
        room_id: Union[str, int],
        room_name: str,
    ) -> Optional[str]:
        """保存水表房间绑定，成功返回服务端提示语。"""
        return self._call_message(
            "/weixinEle/saveWaterRoomInfo",
            self._p_save_water_room_info(
                xiao_qu_id,
                xiao_qu_name,
                lou_dong_id,
                lou_dong_name,
                room_id,
                room_name,
            ),
        )

    def clear_light_room(self) -> Optional[str]:
        """解绑照明房间（``clearZmRoom``，调用即生效，请谨慎使用）。"""
        return self._call_message("/weixinEle/clearZmRoom", self._p_clear_room())

    def clear_air_room(self) -> Optional[str]:
        """解绑空调房间（``clearKtRoom``，调用即生效，请谨慎使用）。"""
        return self._call_message("/weixinEle/clearKtRoom", self._p_clear_room())

    # ── 其他 ────────────────────────────────────────────────────

    def get_info_url(self, school_name: str) -> str:
        """获取使用说明页地址（``/applet/getInfoUrl``）。"""
        result = self._get("/applet/getInfoUrl", self._p_get_info_url(school_name))
        return "" if result is None else str(result)

    def exchange_code(self, code: str) -> str:
        """用微信登录 ``code`` 换取 openId（``/applet/getOpenId``）。

        ``code`` 必须由真实微信客户端通过 ``wx.login()`` 现场获取，
        且一次性、5 分钟过期。
        """
        result = self._get("/applet/getOpenId", self._p_exchange_code(code))
        return "" if result is None else str(result)


class AsyncHnuUtilityClient(_EndpointMixin, BaseClient):
    """异步客户端（基于 ``httpx.AsyncClient``），接口与构造参数同同步版。"""

    def __init__(
        self,
        open_id: Optional[str] = None,
        *,
        transport: Optional[httpx.AsyncBaseTransport] = None,
        client: Optional[httpx.AsyncClient] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(open_id, **kwargs)
        if client is not None:
            self._client = client
            self._owns_client = False
        else:
            if transport is None:
                transport = httpx.AsyncHTTPTransport(retries=self.retries)
            self._client = httpx.AsyncClient(
                timeout=self.timeout,
                verify=self.verify,
                headers=self._headers,
                transport=transport,
            )
            self._owns_client = True

    async def aclose(self) -> None:
        """关闭底层连接池（外部传入的 client 不会被关闭）。"""
        if self._owns_client:
            await self._client.aclose()

    async def __aenter__(self) -> AsyncHnuUtilityClient:
        return self

    async def __aexit__(self, *exc_info: Any) -> None:
        await self.aclose()

    # ── 底层请求 ────────────────────────────────────────────────

    async def _get_payload(self, path: str, params: Mapping[str, Any]) -> Mapping[str, Any]:
        try:
            response = await self._client.get(self._url(path), params=dict(params))
        except httpx.HTTPError as exc:
            raise self._network_error(exc) from exc
        return self._parse_response(response)

    async def _get(self, path: str, params: Mapping[str, Any]) -> Any:
        return self._unwrap(await self._get_payload(path, params))

    async def _call_message(self, path: str, params: Mapping[str, Any]) -> Optional[str]:
        payload = await self._get_payload(path, params)
        self._unwrap(payload)
        message = payload.get("message")
        return None if message is None else str(message)

    async def raw_request(
        self,
        path: str,
        params: Optional[Mapping[str, Any]] = None,
        *,
        signed: bool = False,
        with_open_id: bool = True,
    ) -> Any:
        """直接调用任意接口（未封装接口的逃生通道），用法同同步版。"""
        merged: dict[str, Any] = {}
        if signed:
            merged.update(self._signed_params())
        elif with_open_id:
            merged.update(self._open_id_params())
        if params:
            merged.update(params)
        return await self._get(path, merged)

    # ── 用户与余额 ──────────────────────────────────────────────

    async def get_wx_user(self) -> WxUser:
        return WxUser.from_dict(await self._get("/applet/getWxUser", self._p_get_wx_user()))

    async def get_user(self) -> User:
        return User.from_dict(await self._get("/applet/getUser", self._p_get_user()))

    async def get_left_money(self) -> User:
        return User.from_dict(await self._get("/applet/getLeftMoney", self._p_get_left_money()))

    async def get_ele_info(self, ele_type: Union[EleType, int, str] = EleType.LIGHT) -> EleInfo:
        return EleInfo.from_dict(await self._get("/weixinEle/getEleInfo", self._p_get_ele_info(ele_type)))

    async def get_water_info(self) -> WaterInfo:
        return WaterInfo.from_dict(await self._get("/weixinEle/getWaterInfo", self._p_get_water_info()))

    # ── 充值 / 消费记录 ─────────────────────────────────────────

    async def get_personal_buy_info(
        self,
        consume_type: Union[ConsumeType, int] = ConsumeType.ELECTRICITY,
    ) -> PersonalBuyInfo:
        return PersonalBuyInfo.from_dict(
            await self._get(
                "/weixinEle/getPersonalBuyInfo",
                self._p_get_personal_buy_info(consume_type),
            )
        )

    async def get_room_buy_info(
        self,
        consume_type: Union[ConsumeType, int] = ConsumeType.ELECTRICITY,
        room_type: Union[RoomType, int] = RoomType.LIGHT,
    ) -> RoomBuyInfo:
        return RoomBuyInfo.from_dict(
            await self._get(
                "/weixinEle/getRoomBuyInfo",
                self._p_get_room_buy_info(consume_type, room_type),
            )
        )

    async def get_buy_orders(self, school_name: str) -> list[BuyOrder]:
        payload = await self._get_payload("/applet/getBuyInfo", self._p_get_buy_orders(school_name))
        return self._list(BuyOrder, payload)

    async def get_consume_records(self, school_name: str) -> list[ConsumeRecord]:
        payload = await self._get_payload("/applet/getConsumeInfo", self._p_get_consume_records(school_name))
        return self._list(ConsumeRecord, payload)

    async def get_last_consume(self) -> Optional[ConsumeRecord]:
        result = await self._get("/applet/getLastConsume", self._p_get_last_consume())
        if not isinstance(result, Mapping):
            return None
        return ConsumeRecord.from_dict(result)

    async def get_ele_used_info(self) -> UsedEleInfo:
        return UsedEleInfo.from_dict(await self._get("/weixinEle/getEleUsedInfo", self._p_get_ele_used_info()))

    # ── 校区 / 楼栋 / 房间 ──────────────────────────────────────

    async def get_schools(self) -> list[NamedItem]:
        return self._list(NamedItem, await self._get_payload("/weixinEle/schoolList", {}))

    async def get_water_schools(self) -> list[NamedItem]:
        return self._list(NamedItem, await self._get_payload("/weixinEle/waterSchoolList", {}))

    async def get_buildings(
        self,
        school_id: Union[str, int],
        school_name: str,
        ele_type: Union[EleType, int] = EleType.LIGHT,
        keyword: str = "",
    ) -> list[NamedItem]:
        payload = await self._get_payload(
            "/weixinEle/school_louDongList",
            self._p_get_buildings(school_id, school_name, ele_type, keyword),
        )
        return self._list(NamedItem, payload)

    async def get_water_buildings(
        self,
        school_id: Union[str, int],
        school_name: str,
        keyword: str = "",
    ) -> list[NamedItem]:
        payload = await self._get_payload(
            "/weixinEle/waterSchool_louDongList",
            self._p_get_water_buildings(school_id, school_name, keyword),
        )
        return self._list(NamedItem, payload)

    async def get_rooms(self, lou_dong_id: Union[str, int], keyword: str = "") -> list[NamedItem]:
        payload = await self._get_payload("/weixinEle/louDong_roomList", self._p_get_rooms(lou_dong_id, keyword))
        return self._list(NamedItem, payload)

    async def get_water_rooms(self, lou_dong_id: Union[str, int], keyword: str = "") -> list[NamedItem]:
        payload = await self._get_payload(
            "/weixinEle/waterLouDong_roomList",
            self._p_get_rooms(lou_dong_id, keyword),
        )
        return self._list(NamedItem, payload)

    # ── 房间绑定 / 解绑 ─────────────────────────────────────────

    async def save_room_info(
        self,
        *,
        xiao_qu_id: Union[str, int],
        xiao_qu_name: str,
        lou_dong_id: Union[str, int],
        lou_dong_name: str,
        room_id: Union[str, int],
        kt_lou_dong_id: Union[str, int],
        kt_lou_dong_name: str,
        kt_room_id: Union[str, int],
    ) -> Optional[str]:
        return await self._call_message(
            "/weixinEle/saveRoomInfo",
            self._p_save_room_info(
                xiao_qu_id,
                xiao_qu_name,
                lou_dong_id,
                lou_dong_name,
                room_id,
                kt_lou_dong_id,
                kt_lou_dong_name,
                kt_room_id,
            ),
        )

    async def save_water_room_info(
        self,
        *,
        xiao_qu_id: Union[str, int],
        xiao_qu_name: str,
        lou_dong_id: Union[str, int],
        lou_dong_name: str,
        room_id: Union[str, int],
        room_name: str,
    ) -> Optional[str]:
        return await self._call_message(
            "/weixinEle/saveWaterRoomInfo",
            self._p_save_water_room_info(
                xiao_qu_id,
                xiao_qu_name,
                lou_dong_id,
                lou_dong_name,
                room_id,
                room_name,
            ),
        )

    async def clear_light_room(self) -> Optional[str]:
        return await self._call_message("/weixinEle/clearZmRoom", self._p_clear_room())

    async def clear_air_room(self) -> Optional[str]:
        return await self._call_message("/weixinEle/clearKtRoom", self._p_clear_room())

    # ── 其他 ────────────────────────────────────────────────────

    async def get_info_url(self, school_name: str) -> str:
        result = await self._get("/applet/getInfoUrl", self._p_get_info_url(school_name))
        return "" if result is None else str(result)

    async def exchange_code(self, code: str) -> str:
        result = await self._get("/applet/getOpenId", self._p_exchange_code(code))
        return "" if result is None else str(result)
