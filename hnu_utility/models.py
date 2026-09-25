"""数据模型：接口返回结果的强类型封装。

每个模型都保留了原始字典（``raw`` 字段），方便访问未建模的字段。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional, Type, TypeVar

_T = TypeVar("_T")


def _num(value: Any) -> Optional[float]:
    """把接口返回的数字（可能是字符串）转成 float。"""
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _int(value: Any) -> Optional[int]:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _str(value: Any) -> str:
    return "" if value is None else str(value)


def _opt_str(value: Any) -> Optional[str]:
    return None if value is None else str(value)


def parse_list(model: Type[_T], data: Any) -> List[_T]:
    """把接口返回的对象列表解析成模型列表，容忍 None 和非列表输入。"""
    if not isinstance(data, list):
        return []
    return [model.from_dict(item) for item in data if isinstance(item, Mapping)]


@dataclass
class NamedItem:
    """通用「id + 名称」选项，用于校区 / 楼栋 / 房间列表。"""

    id: str
    text: str
    raw: Dict[str, Any] = field(default_factory=dict, repr=False, compare=False)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "NamedItem":
        return cls(id=_str(data.get("id")), text=_str(data.get("text")), raw=dict(data))


@dataclass
class User:
    """用户信息（``/applet/getWxUser`` 的 ``user``、``/applet/getUser``、``/applet/getLeftMoney``）。"""

    id: Optional[int] = None
    open_id: str = ""
    nick_name: str = ""
    real_name: str = ""
    tel: str = ""
    student_num: str = ""
    school_name: str = ""

    xiao_qu_id: Optional[int] = None
    xiao_qu_name: str = ""
    lou_dong_id: Optional[int] = None
    lou_dong_name: str = ""
    room_id: Optional[int] = None
    room_name: str = ""

    kt_lou_dong_id: Optional[int] = None
    kt_lou_dong_name: str = ""
    kt_room_id: Optional[int] = None
    kt_room_name: str = ""

    water_xiao_qu_id: Optional[int] = None
    water_xiao_qu_name: str = ""
    water_lou_dong_id: Optional[int] = None
    water_lou_dong_name: str = ""
    water_room_id: Optional[int] = None
    water_room_name: str = ""

    amount: Optional[float] = None
    free_money: Optional[float] = None

    raw: Dict[str, Any] = field(default_factory=dict, repr=False, compare=False)

    @property
    def total_money(self) -> float:
        """热水余额 + 赠送余额。"""
        return (self.amount or 0.0) + (self.free_money or 0.0)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "User":
        return cls(
            id=_int(data.get("id")),
            open_id=_str(data.get("openId")),
            nick_name=_str(data.get("nickName")),
            real_name=_str(data.get("realName")),
            tel=_str(data.get("tel")),
            student_num=_str(data.get("studentNum")),
            school_name=_str(data.get("schoolName")),
            xiao_qu_id=_int(data.get("xiaoQuId")),
            xiao_qu_name=_str(data.get("xiaoQuName")),
            lou_dong_id=_int(data.get("louDongId")),
            lou_dong_name=_str(data.get("louDongName")),
            room_id=_int(data.get("roomId")),
            room_name=_str(data.get("roomName")),
            kt_lou_dong_id=_int(data.get("ktLouDongId")),
            kt_lou_dong_name=_str(data.get("ktLouDongName")),
            kt_room_id=_int(data.get("ktRoomId")),
            kt_room_name=_str(data.get("ktRoomName")),
            water_xiao_qu_id=_int(data.get("waterXiaoQuId")),
            water_xiao_qu_name=_str(data.get("waterXiaoQuName")),
            water_lou_dong_id=_int(data.get("waterLouDongId")),
            water_lou_dong_name=_str(data.get("waterLouDongName")),
            water_room_id=_int(data.get("waterRoomId")),
            water_room_name=_str(data.get("waterRoomName")),
            amount=_num(data.get("amount")),
            free_money=_num(data.get("freeMoney")),
            raw=dict(data),
        )


@dataclass
class WxUser:
    """``/applet/getWxUser`` 的完整返回。"""

    user: User
    hot_water_price: Optional[float] = None
    param_set_switch: str = ""
    register_switch: str = ""
    raw: Dict[str, Any] = field(default_factory=dict, repr=False, compare=False)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "WxUser":
        raw_user = data.get("user")
        return cls(
            user=User.from_dict(raw_user if isinstance(raw_user, Mapping) else {}),
            hot_water_price=_num(data.get("hotWaterPrice")),
            param_set_switch=_str(data.get("paramSetSwitch")),
            register_switch=_str(data.get("registerSwitch")),
            raw=dict(data),
        )


@dataclass
class EleInfo:
    """照明 / 空调余额（``/weixinEle/getEleInfo``）。"""

    left_ele: Optional[float] = None
    left_money: Optional[float] = None
    mon_time: str = ""
    lou_dong: str = ""
    room: str = ""
    raw: Dict[str, Any] = field(default_factory=dict, repr=False, compare=False)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "EleInfo":
        return cls(
            left_ele=_num(data.get("leftEle")),
            left_money=_num(data.get("leftMoney")),
            mon_time=_str(data.get("monTime")),
            lou_dong=_str(data.get("loudong")),
            room=_str(data.get("room")),
            raw=dict(data),
        )


@dataclass
class WaterInfo:
    """水表余额（``/weixinEle/getWaterInfo``）。"""

    left_water: Optional[float] = None
    left_money: Optional[float] = None
    mon_time: str = ""
    lou_dong: str = ""
    room: str = ""
    raw: Dict[str, Any] = field(default_factory=dict, repr=False, compare=False)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "WaterInfo":
        return cls(
            left_water=_num(data.get("leftWater")),
            left_money=_num(data.get("leftMoney")),
            mon_time=_str(data.get("monTime")),
            lou_dong=_str(data.get("loudong")),
            room=_str(data.get("room")),
            raw=dict(data),
        )


@dataclass
class BuyRecord:
    """一条个人充值记录（``/weixinEle/getPersonalBuyInfo`` 的 ``list`` 元素）。"""

    create_time: str = ""
    room_name: str = ""
    pay_money: Optional[float] = None
    raw: Dict[str, Any] = field(default_factory=dict, repr=False, compare=False)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "BuyRecord":
        return cls(
            create_time=_str(data.get("createTime")),
            room_name=_str(data.get("roomName")),
            pay_money=_num(data.get("payMoney")),
            raw=dict(data),
        )


@dataclass
class PersonalBuyInfo:
    """个人充值记录（``/weixinEle/getPersonalBuyInfo``，``consumeType`` 区分电 / 水）。"""

    name: str = ""
    stu_num: str = ""
    records: List[BuyRecord] = field(default_factory=list)
    raw: Dict[str, Any] = field(default_factory=dict, repr=False, compare=False)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "PersonalBuyInfo":
        return cls(
            name=_str(data.get("name")),
            stu_num=_str(data.get("stuNum")),
            records=parse_list(BuyRecord, data.get("list")),
            raw=dict(data),
        )


@dataclass
class RoomBuyRecord:
    """一条房间充值记录（``/weixinEle/getRoomBuyInfo`` 的 ``list`` 元素）。"""

    real_name: str = ""
    create_time: str = ""
    pay_money: Optional[float] = None
    raw: Dict[str, Any] = field(default_factory=dict, repr=False, compare=False)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "RoomBuyRecord":
        return cls(
            real_name=_str(data.get("realName")),
            create_time=_str(data.get("createTime")),
            pay_money=_num(data.get("payMoney")),
            raw=dict(data),
        )


@dataclass
class RoomBuyInfo:
    """房间充值记录（``/weixinEle/getRoomBuyInfo``）。"""

    xiao_qu: str = ""
    lou_dong: str = ""
    room: Optional[str] = None
    records: List[RoomBuyRecord] = field(default_factory=list)
    raw: Dict[str, Any] = field(default_factory=dict, repr=False, compare=False)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "RoomBuyInfo":
        return cls(
            xiao_qu=_str(data.get("xiaoQu")),
            lou_dong=_str(data.get("louDong")),
            room=_opt_str(data.get("room")),
            records=parse_list(RoomBuyRecord, data.get("list")),
            raw=dict(data),
        )


@dataclass
class BuyOrder:
    """水控充值订单（``/applet/getBuyInfo``）。"""

    id: Optional[int] = None
    open_id: str = ""
    pay_money: Optional[float] = None
    create_time: str = ""
    order_id: str = ""
    out_trade_no: str = ""
    is_pay_success: Optional[int] = None
    is_refund: Optional[int] = None
    consume_type: Optional[int] = None
    room_id: Optional[int] = None
    school_id: Optional[int] = None
    pay_quantity: Optional[float] = None
    down_time: str = ""
    is_send: Optional[int] = None
    pay_state: Optional[int] = None
    raw: Dict[str, Any] = field(default_factory=dict, repr=False, compare=False)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "BuyOrder":
        return cls(
            id=_int(data.get("id")),
            open_id=_str(data.get("openId")),
            pay_money=_num(data.get("payMoney")),
            create_time=_str(data.get("createTime")),
            order_id=_str(data.get("orderId")),
            out_trade_no=_str(data.get("outTradeNo")),
            is_pay_success=_int(data.get("isPaySuccess")),
            is_refund=_int(data.get("isRefund")),
            consume_type=_int(data.get("consumeType")),
            room_id=_int(data.get("roomId")),
            school_id=_int(data.get("schoolId")),
            pay_quantity=_num(data.get("payQuantity")),
            down_time=_str(data.get("downTime")),
            is_send=_int(data.get("isSend")),
            pay_state=_int(data.get("payState")),
            raw=dict(data),
        )


@dataclass
class ConsumeRecord:
    """扫码 / 蓝牙用水消费记录（``/applet/getConsumeInfo``、``/applet/getLastConsume``）。"""

    id: Optional[int] = None
    open_id: str = ""
    before_price: Optional[float] = None
    end_price: Optional[float] = None
    cons_price: Optional[float] = None
    create_time: str = ""
    cons_time: str = ""
    cons_quantity: Optional[float] = None
    mac: str = ""
    device_id: str = ""
    device_name: str = ""
    water_ctrl_name: str = ""
    water_ctrl_sn: str = ""
    real_name: str = ""
    student_num: str = ""
    is_sync: Optional[int] = None
    alarm_data_id: Optional[int] = None
    raw: Dict[str, Any] = field(default_factory=dict, repr=False, compare=False)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ConsumeRecord":
        return cls(
            id=_int(data.get("id")),
            open_id=_str(data.get("openId")),
            before_price=_num(data.get("beforePrice")),
            end_price=_num(data.get("endPrice")),
            cons_price=_num(data.get("consPrice")),
            create_time=_str(data.get("createTime")),
            cons_time=_str(data.get("consTime")),
            cons_quantity=_num(data.get("consQuantity")),
            mac=_str(data.get("mac")),
            device_id=_str(data.get("deviceId")),
            device_name=_str(data.get("deviceName")),
            water_ctrl_name=_str(data.get("waterCtrlName")),
            water_ctrl_sn=_str(data.get("waterCtrlSn")),
            real_name=_str(data.get("realName")),
            student_num=_str(data.get("studentNum")),
            is_sync=_int(data.get("isSync")),
            alarm_data_id=_int(data.get("alarmDataId")),
            raw=dict(data),
        )


@dataclass
class UsedEleInfo:
    """电表用量（``/weixinEle/getEleUsedInfo``）。

    部分部署 / 账户没有用量数据，接口会返回业务码 500，客户端会抛出
    :class:`~hnu_utility.exceptions.HnuApiError`。
    """

    xiao_qu: str = ""
    lou_dong: str = ""
    room: str = ""
    records: List[Dict[str, Any]] = field(default_factory=list)
    raw: Dict[str, Any] = field(default_factory=dict, repr=False, compare=False)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "UsedEleInfo":
        records = data.get("list")
        return cls(
            xiao_qu=_str(data.get("xiaoQu")),
            lou_dong=_str(data.get("louDong")),
            room=_str(data.get("room")),
            records=[dict(x) for x in records if isinstance(x, Mapping)] if isinstance(records, list) else [],
            raw=dict(data),
        )
