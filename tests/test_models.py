"""数据模型解析的单元测试。"""

from __future__ import annotations

from hnu_utility.models import BuyOrder, NamedItem, User, WxUser, parse_list


def test_from_dict_tolerates_none():
    assert User.from_dict(None).real_name == ""
    assert WxUser.from_dict(None).user.amount is None
    assert NamedItem.from_dict(None).id == ""
    assert BuyOrder.from_dict(None).id is None


def test_int_parses_decimal_strings():
    order = BuyOrder.from_dict({"id": "12.0", "isPaySuccess": "1"})
    assert order.id == 12
    assert order.is_pay_success == 1


def test_int_rejects_invalid_values():
    assert BuyOrder.from_dict({"id": "abc"}).id is None
    assert BuyOrder.from_dict({"id": ""}).id is None
    assert BuyOrder.from_dict({"id": "1.5"}).id is None


def test_num_tolerates_garbage():
    assert User.from_dict({"amount": "N/A"}).amount is None


def test_parse_list_skips_non_mappings():
    items = parse_list(NamedItem, [{"id": "1", "text": "a"}, None, "x"])
    assert [item.id for item in items] == ["1"]
    assert parse_list(NamedItem, None) == []
