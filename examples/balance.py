#!/usr/bin/env python3
"""查询全部余额并打印汇总（同步）。

用法::

    python examples/balance.py [openId]
"""

from __future__ import annotations

import sys

from _config import parse_open_id

from hnu_utility import EleType, HnuError, HnuUtilityClient


def fmt(value) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    return str(int(number)) if number == int(number) else f"{number:.2f}"


def main() -> int:
    open_id = parse_open_id("查询海南大学宿舍水电费余额")

    with HnuUtilityClient(open_id) as client:
        try:
            wx_user = client.get_wx_user()
        except HnuError as exc:
            print(f"查询失败：{exc}", file=sys.stderr)
            return 1

        user = wx_user.user
        print(f"{user.real_name} @ {user.school_name} {user.room_name}")
        print(f"热水余额：{fmt(user.amount)} 元（赠送 {fmt(user.free_money)} 元）")

        total = user.total_money
        for label, fetch in (
            ("照明+插座", lambda: client.get_ele_info(EleType.LIGHT)),
            ("空调", lambda: client.get_ele_info(EleType.AIR)),
        ):
            try:
                info = fetch()
            except HnuError as exc:
                print(f"{label:>8}：查询失败（{exc}）", file=sys.stderr)
                continue
            total += info.left_money or 0.0
            print(f"{label:>8}：{fmt(info.left_ele):>7} 度 / {fmt(info.left_money):>7} 元  [{info.mon_time}]")

        try:
            water = client.get_water_info()
        except HnuError as exc:
            print(f"{'水表':>8}：查询失败（{exc}）", file=sys.stderr)
        else:
            total += water.left_money or 0.0
            print(f"{'水表':>8}：{fmt(water.left_water):>7} 吨 / {fmt(water.left_money):>7} 元  [{water.mon_time}]")

        print(f"资产总计：{fmt(total)} 元")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
