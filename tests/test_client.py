"""基于 httpx.MockTransport 的单元测试（不访问真实网络）。"""

from __future__ import annotations

import asyncio
import hashlib
import inspect
from typing import Any

import httpx
import pytest

from hnu_utility import (
    APP_ID,
    APP_SECRET,
    AsyncHnuUtilityClient,
    ConsumeType,
    HnuApiError,
    HnuNetworkError,
    HnuResponseError,
    HnuUtilityClient,
    RoomType,
)


def ok(result: Any = None, message: Any = None) -> dict[str, Any]:
    return {"statusCode": "200", "message": message, "resultObject": result}


def fail(code: Any, message: Any = None) -> dict[str, Any]:
    return {"statusCode": str(code), "message": message, "resultObject": None}


class Handler:
    """记录所有请求，并按给定数据返回响应。"""

    def __init__(self, payload: Any) -> None:
        self.requests: list[httpx.Request] = []
        self._payload = payload

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        data = self._payload(request) if callable(self._payload) else self._payload
        return httpx.Response(200, json=data)

    @property
    def last_query(self) -> dict[str, str]:
        return dict(httpx.QueryParams(self.requests[-1].url.query))

    @property
    def last_path(self) -> str:
        return self.requests[-1].url.path


def make_client(handler: Handler, **kwargs: Any) -> HnuUtilityClient:
    return HnuUtilityClient(
        "ofTEST_openid",
        transport=httpx.MockTransport(handler),
        **kwargs,
    )


# ── 签名 ────────────────────────────────────────────────────────────


def test_sign_matches_md5_formula() -> None:
    client = HnuUtilityClient("ofTEST_openid")
    timestamp = 1700000000000
    expected = hashlib.md5(f"{APP_ID}{timestamp}{APP_SECRET}".encode()).hexdigest()
    assert client.sign(timestamp) == expected


def test_signed_request_contains_sign_fields() -> None:
    handler = Handler(ok({"user": {}}))
    with make_client(handler) as client:
        client.get_wx_user()
    query = handler.last_query
    assert query["openId"] == "ofTEST_openid"
    assert query["appid"] == APP_ID
    assert query["sign"] == hashlib.md5(f"{APP_ID}{query['timestamp']}{APP_SECRET}".encode()).hexdigest()
    assert handler.last_path == "/scanQRWaterCtrl_redis_hndx1/service/applet/getWxUser"


# ── 用户与余额 ──────────────────────────────────────────────────────


def test_get_wx_user_parses_model() -> None:
    handler = Handler(
        ok(
            {
                "hotWaterPrice": "16.5",
                "paramSetSwitch": "0",
                "registerSwitch": "0",
                "user": {
                    "openId": "ofTEST_openid",
                    "realName": "张三",
                    "studentNum": "20243000000",
                    "schoolName": "海南大学",
                    "xiaoQuName": "海甸校区",
                    "louDongName": "紫荆3公寓",
                    "roomName": "紫荆3公寓660照明",
                    "waterRoomName": "紫荆3公寓660水表",
                    "amount": "0.52",
                    "freeMoney": "1.00",
                },
            }
        )
    )
    with make_client(handler) as client:
        wx_user = client.get_wx_user()
    assert wx_user.hot_water_price == 16.5
    assert wx_user.user.real_name == "张三"
    assert wx_user.user.amount == 0.52
    assert wx_user.user.total_money == pytest.approx(1.52)


def test_get_ele_info_passes_type() -> None:
    handler = Handler(ok({"leftEle": "137.13", "leftMoney": "83.58", "loudong": "紫荆3公寓", "room": "660照明"}))
    with make_client(handler) as client:
        info = client.get_ele_info("2")
    assert handler.last_query["type"] == "2"
    assert info.left_ele == 137.13
    assert info.left_money == 83.58


def test_get_water_info() -> None:
    handler = Handler(ok({"leftWater": "21.13", "leftMoney": "66.35", "monTime": "2026-09-26 01:06:12"}))
    with make_client(handler) as client:
        info = client.get_water_info()
    assert info.left_water == 21.13
    assert info.mon_time.startswith("2026-09-26")


# ── 业务错误 ────────────────────────────────────────────────────────


def test_api_error_raises() -> None:
    handler = Handler(fail(500, "参数签名校验异常"))
    with make_client(handler) as client:
        with pytest.raises(HnuApiError) as excinfo:
            client.get_left_money()
    assert excinfo.value.code == "500"
    assert excinfo.value.message == "参数签名校验异常"


def test_no_data_code_201() -> None:
    handler = Handler(fail(201, "无充值记录"))
    with make_client(handler) as client:
        with pytest.raises(HnuApiError) as excinfo:
            client.get_room_buy_info()
    assert excinfo.value.is_no_data


def test_http_error_raises_response_error() -> None:
    transport = httpx.MockTransport(lambda request: httpx.Response(502, text="bad gateway"))
    client = HnuUtilityClient("ofTEST_openid", transport=transport)
    with pytest.raises(HnuResponseError) as excinfo:
        client.get_schools()
    assert excinfo.value.status_code == 502


def test_network_error_maps_to_hnu_network_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    client = HnuUtilityClient("ofTEST_openid", transport=httpx.MockTransport(handler))
    with pytest.raises(HnuNetworkError) as excinfo:
        client.get_wx_user()
    assert excinfo.value.url is not None
    assert "connection refused" in str(excinfo.value)


# ── 记录 ────────────────────────────────────────────────────────────


def test_get_personal_buy_info() -> None:
    handler = Handler(
        ok(
            {
                "name": "张三",
                "stuNum": "20243000000",
                "list": [
                    {"createTime": "2026-09-19 00:14:42", "roomName": "660照明", "payMoney": 100.0},
                    {"createTime": "2026-09-03 21:05:24", "roomName": "660空调", "payMoney": 25},
                ],
            }
        )
    )
    with make_client(handler) as client:
        info = client.get_personal_buy_info(ConsumeType.ELECTRICITY)
    assert handler.last_query["consumeType"] == "2"
    assert [r.pay_money for r in info.records] == [100.0, 25.0]
    assert info.records[0].room_name == "660照明"


def test_get_room_buy_info_params() -> None:
    handler = Handler(ok({"xiaoQu": "海甸校区", "louDong": "紫荆3公寓", "list": []}))
    with make_client(handler) as client:
        info = client.get_room_buy_info(ConsumeType.ELECTRICITY, RoomType.AIR)
    assert handler.last_query["consumeType"] == "2"
    assert handler.last_query["roomType"] == "2"
    assert info.xiao_qu == "海甸校区"


def test_get_buy_orders_and_consume_records() -> None:
    handler = Handler(
        ok(
            [
                {
                    "id": 1037964,
                    "payMoney": 10.0,
                    "orderId": "4200002696",
                    "isPaySuccess": 1,
                    "isRefund": 0,
                    "outTradeNo": "NO_1743",
                }
            ]
        )
    )
    with make_client(handler) as client:
        orders = client.get_buy_orders("海南大学")
    assert handler.last_query["schoolName"] == "海南大学"
    assert orders[0].pay_money == 10.0
    assert orders[0].is_pay_success == 1


def test_get_last_consume_none() -> None:
    handler = Handler(ok(None))
    with make_client(handler) as client:
        assert client.get_last_consume() is None


# ── 目录接口（无需 openId） ─────────────────────────────────────────


def test_catalog_without_open_id() -> None:
    handler = Handler(
        ok(
            [
                {"id": "7,8,11,14", "text": "海甸校区"},
            ]
        )
    )
    client = HnuUtilityClient(transport=httpx.MockTransport(handler))
    schools = client.get_schools()
    assert schools[0].id == "7,8,11,14"
    assert handler.last_path.endswith("/weixinEle/schoolList")


def test_get_rooms() -> None:
    handler = Handler(ok([{"id": 48278, "text": "紫荆3公寓101照明"}]))
    client = HnuUtilityClient(transport=httpx.MockTransport(handler))
    rooms = client.get_rooms(48276)
    assert rooms[0].id == "48278"
    assert handler.last_query["louDongId"] == "48276"


# ── 绑定 / 解绑 ─────────────────────────────────────────────────────


def test_save_room_info_params() -> None:
    handler = Handler(ok(None, "保存成功!"))
    with make_client(handler) as client:
        message = client.save_room_info(
            xiao_qu_id=14,
            xiao_qu_name="海甸校区",
            lou_dong_id=48276,
            lou_dong_name="紫荆3公寓",
            room_id=49256,
            kt_lou_dong_id=47739,
            kt_lou_dong_name="紫荆3公寓空调",
            kt_room_id=49093,
        )
    assert message == "保存成功!"
    query = handler.last_query
    assert query["openId"] == "ofTEST_openid"
    assert query["xiaoquId"] == "14"
    assert query["xiaoQuName"] == "海甸校区"
    assert query["loudongId"] == "48276"
    assert query["ktLoudongId"] == "47739"
    assert query["roomId"] == "49256"
    assert query["ktRoomId"] == "49093"


def test_save_water_room_info_params() -> None:
    handler = Handler(ok(None, "保存成功!"))
    with make_client(handler) as client:
        client.save_water_room_info(
            xiao_qu_id=14,
            xiao_qu_name="海甸校区",
            lou_dong_id=48276,
            lou_dong_name="紫荆3公寓",
            room_id=50365,
            room_name="紫荆3公寓660水表",
        )
    query = handler.last_query
    assert query["roomName"] == "紫荆3公寓660水表"
    assert query["loudongId"] == "48276"


def test_clear_room_sends_only_open_id() -> None:
    handler = Handler(ok(None, "解绑成功!"))
    with make_client(handler) as client:
        message = client.clear_light_room()
    assert message == "解绑成功!"
    assert handler.last_query == {"openId": "ofTEST_openid"}


# ── 逃生通道 ────────────────────────────────────────────────────────


def test_raw_request_signed() -> None:
    handler = Handler(ok("pong"))
    with make_client(handler) as client:
        result = client.raw_request("/some/unknown/api", {"foo": "bar"}, signed=True)
    assert result == "pong"
    query = handler.last_query
    assert query["foo"] == "bar"
    assert "sign" in query and "timestamp" in query


def test_missing_open_id_raises_value_error() -> None:
    client = HnuUtilityClient(transport=httpx.MockTransport(Handler(ok())))
    with pytest.raises(ValueError):
        client.get_wx_user()


def test_raw_request_without_open_id() -> None:
    handler = Handler(ok("pong"))
    client = HnuUtilityClient(transport=httpx.MockTransport(handler))
    assert client.raw_request("/some/unknown/api", {"foo": "bar"}, with_open_id=False) == "pong"
    assert handler.last_query == {"foo": "bar"}


def test_external_client_is_not_closed() -> None:
    external = httpx.Client(transport=httpx.MockTransport(Handler(ok())))
    client = HnuUtilityClient("ofTEST_openid", client=external)
    client.close()
    assert not external.is_closed
    external.close()


# ── 异步客户端 ──────────────────────────────────────────────────────


def test_async_client_end_to_end() -> None:
    async def run() -> None:
        handler = Handler(
            {
                "statusCode": "200",
                "message": None,
                "resultObject": {
                    "user": {"realName": "李四", "amount": "3.5", "freeMoney": "0"},
                    "hotWaterPrice": "16.5",
                },
            }
        )
        async with AsyncHnuUtilityClient("ofTEST_openid", transport=httpx.MockTransport(handler)) as client:
            wx_user = await client.get_wx_user()
            schools = await client.get_schools()
        assert handler is not None
        assert wx_user.user.real_name == "李四"
        assert wx_user.user.total_money == pytest.approx(3.5)
        assert schools == []

    asyncio.run(run())


def test_async_api_error() -> None:
    async def run() -> None:
        handler = Handler(fail(500, None))
        async with AsyncHnuUtilityClient("ofTEST_openid", transport=httpx.MockTransport(handler)) as client:
            with pytest.raises(HnuApiError):
                await client.get_wx_user()

    asyncio.run(run())


# ── 空 resultObject / 其他接口 ──────────────────────────────────────


def test_null_result_object_returns_empty_model() -> None:
    handler = Handler(ok(None))
    with make_client(handler) as client:
        wx_user = client.get_wx_user()
        info = client.get_ele_info()
        used = client.get_ele_used_info()
    assert wx_user.user.real_name == ""
    assert wx_user.user.amount is None
    assert wx_user.hot_water_price is None
    assert info.left_ele is None
    assert used.records == []


def test_get_user_parses_fields() -> None:
    handler = Handler(ok({"id": 1, "realName": "王五", "studentNum": "20240001", "amount": "8.5", "freeMoney": "1.5"}))
    with make_client(handler) as client:
        user = client.get_user()
    assert user.id == 1
    assert user.real_name == "王五"
    assert user.total_money == pytest.approx(10.0)
    assert handler.last_path.endswith("/applet/getUser")


def test_get_ele_used_info_parses_records() -> None:
    handler = Handler(
        ok({"xiaoQu": "海甸校区", "louDong": "紫荆3公寓", "room": "660照明", "list": [{"month": "2026-09"}]})
    )
    with make_client(handler) as client:
        used = client.get_ele_used_info()
    assert used.room == "660照明"
    assert used.records == [{"month": "2026-09"}]
    assert handler.last_path.endswith("/weixinEle/getEleUsedInfo")


def test_get_info_url_needs_no_open_id() -> None:
    handler = Handler(ok("https://example.com/help"))
    client = HnuUtilityClient(transport=httpx.MockTransport(handler))
    assert client.get_info_url("海南大学") == "https://example.com/help"
    assert handler.last_query == {"schoolName": "海南大学", "type": "weixin"}


def test_exchange_code() -> None:
    handler = Handler(ok("ofNEW_openid"))
    client = HnuUtilityClient(transport=httpx.MockTransport(handler))
    assert client.exchange_code("wx-code") == "ofNEW_openid"
    assert handler.last_query == {"code": "wx-code"}


def test_water_catalog_endpoints() -> None:
    handler = Handler(ok([{"id": 1, "text": "海甸校区"}]))
    client = HnuUtilityClient(transport=httpx.MockTransport(handler))
    assert client.get_water_schools()[0].text == "海甸校区"
    assert handler.last_path.endswith("/weixinEle/waterSchoolList")

    client.get_water_buildings(1, "海甸校区", keyword="紫荆")
    assert handler.last_path.endswith("/weixinEle/waterSchool_louDongList")
    assert handler.last_query["type"] == "1"
    assert handler.last_query["loudongInfo"] == "紫荆"

    client.get_water_rooms(2)
    assert handler.last_path.endswith("/weixinEle/waterLouDong_roomList")
    assert handler.last_query["louDongId"] == "2"


def test_get_consume_records() -> None:
    handler = Handler(ok([{"id": 1, "consPrice": "0.35", "consQuantity": "12.5", "deviceName": "A栋101"}]))
    with make_client(handler) as client:
        records = client.get_consume_records("海南大学")
    assert handler.last_query["schoolName"] == "海南大学"
    assert records[0].cons_price == 0.35
    assert records[0].device_name == "A栋101"


def test_async_null_result_object() -> None:
    async def run() -> None:
        handler = Handler(ok(None))
        async with AsyncHnuUtilityClient("ofTEST_openid", transport=httpx.MockTransport(handler)) as client:
            wx_user = await client.get_wx_user()
        assert wx_user.user.real_name == ""

    asyncio.run(run())


# ── 同步 / 异步 API 一致性 ──────────────────────────────────────────


def test_sync_async_api_parity() -> None:
    sync_public = {name for name in dir(HnuUtilityClient) if not name.startswith("_")}
    async_public = {name for name in dir(AsyncHnuUtilityClient) if not name.startswith("_")}
    assert sync_public - async_public == {"close"}
    assert async_public - sync_public == {"aclose"}
    for name in sorted(sync_public & async_public):
        sync_attr = getattr(HnuUtilityClient, name)
        async_attr = getattr(AsyncHnuUtilityClient, name)
        if callable(sync_attr) and callable(async_attr):
            assert inspect.signature(sync_attr) == inspect.signature(async_attr), name
