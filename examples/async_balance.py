#!/usr/bin/env python3
"""异步并发查询全部余额。

用法::

    python examples/async_balance.py [openId]
"""

from __future__ import annotations

import asyncio
import sys

from _config import parse_open_id

from hnu_utility import AsyncHnuUtilityClient, EleType, HnuError


async def main() -> int:
    open_id = parse_open_id("异步并发查询海南大学宿舍水电费余额")

    async with AsyncHnuUtilityClient(open_id) as client:
        try:
            wx_user, light, air, water = await asyncio.gather(
                client.get_wx_user(),
                client.get_ele_info(EleType.LIGHT),
                client.get_ele_info(EleType.AIR),
                client.get_water_info(),
            )
        except HnuError as exc:
            print(f"查询失败：{exc}", file=sys.stderr)
            return 1

        user = wx_user.user
        print(f"{user.real_name} @ {user.school_name} {user.room_name}")
        print(f"热水余额：{user.total_money:.2f} 元")
        print(f"照明+插座：{light.left_ele} 度 / {light.left_money} 元")
        print(f"空调：{air.left_ele} 度 / {air.left_money} 元")
        print(f"水表：{water.left_water} 吨 / {water.left_money} 元")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
