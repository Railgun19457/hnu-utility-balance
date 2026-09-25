#!/usr/bin/env python3
"""查询充值 / 消费记录。

用法::

    python examples/records.py [openId]
"""

from __future__ import annotations

import sys

from _config import parse_open_id

from hnu_utility import ConsumeType, HnuError, HnuUtilityClient


def num(value, digits: int = 2) -> str:
    return "-" if value is None else f"{value:.{digits}f}"


def describe(exc: HnuError) -> str:
    message = getattr(exc, "message", None)
    return str(message or exc)


def main() -> int:
    open_id = parse_open_id("查询充值 / 消费记录")

    with HnuUtilityClient(open_id) as client:
        try:
            wx_user = client.get_wx_user()
        except HnuError as exc:
            print(f"查询失败：{exc}", file=sys.stderr)
            return 1

        school_name = wx_user.user.school_name

        try:
            buys = client.get_personal_buy_info(ConsumeType.ELECTRICITY)
        except HnuError as exc:
            print(f"== 个人充值记录：{describe(exc)} ==")
        else:
            print(f"== 个人充值记录（{len(buys.records)} 条）==")
            for record in buys.records[:5]:
                print(f"  {record.create_time}  {record.room_name:<16}  {num(record.pay_money):>7} 元")

        try:
            orders = client.get_buy_orders(school_name)
        except HnuError as exc:
            print(f"== 水控充值订单：{describe(exc)} ==")
        else:
            print(f"== 水控充值订单（{len(orders)} 条）==")
            for order in orders[:5]:
                print(f"  {order.create_time}  {num(order.pay_money):>7} 元  单号 {order.order_id}")

        try:
            consumes = client.get_consume_records(school_name)
        except HnuError as exc:
            print(f"== 水控消费记录：{describe(exc)} ==")
        else:
            print(f"== 水控消费记录（{len(consumes)} 条）==")
            for record in consumes[:5]:
                print(
                    f"  {record.create_time}  {num(record.cons_quantity, 1):>6}"
                    f"  {num(record.cons_price):>6} 元  {record.device_name}"
                )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
