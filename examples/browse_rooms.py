#!/usr/bin/env python3
"""浏览校区 → 楼栋 → 房间列表。

用法::

    python examples/browse_rooms.py [openId]
"""

from __future__ import annotations

import sys

from _config import parse_open_id

from hnu_utility import EleType, HnuError, HnuUtilityClient


def main() -> int:
    open_id = parse_open_id("浏览校区 / 楼栋 / 房间列表")

    # 目录类接口不需要 openId，这里仍复用同一个客户端
    with HnuUtilityClient(open_id) as client:
        try:
            print("== 校区 ==")
            schools = client.get_schools()
            for school in schools:
                print(f"  {school.id:<12} {school.text}")

            school = next((s for s in schools if s.text == "海甸校区"), schools[0])

            print(f"\n== {school.text} · 照明楼栋 ==")
            buildings = client.get_buildings(school.id, school.text, EleType.LIGHT)
            for building in buildings[:10]:
                print(f"  {building.id:<8} {building.text}")
            print(f"  ... 共 {len(buildings)} 栋")

            if buildings:
                building = buildings[0]
                rooms = client.get_rooms(building.id)
                print(f"\n== {building.text} · 房间（共 {len(rooms)} 间）==")
                for room in rooms[:10]:
                    print(f"  {room.id:<8} {room.text}")

                # 目录接口支持关键字过滤
                matched = client.get_rooms(building.id, keyword="101")
                print(f"\n关键字 '101' 命中 {len(matched)} 间：{[r.text for r in matched[:5]]}")
        except HnuError as exc:
            print(f"查询失败：{exc}", file=sys.stderr)
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
