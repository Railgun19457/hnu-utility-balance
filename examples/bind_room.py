#!/usr/bin/env python3
"""房间绑定示例（写操作，默认只读预览）。

用法::

    # 打印当前绑定，不会修改任何数据
    python examples/bind_room.py

    # 以当前绑定原样重新保存（幂等，用于验证写接口）
    python examples/bind_room.py --confirm

解绑接口（调用即生效，请谨慎）：

- ``client.clear_light_room()`` 解绑照明
- ``client.clear_air_room()``   解绑空调

切换房间时，先用 ``browse_rooms.py`` 找到目标房间的 ID，
再调用 ``client.save_room_info(...)`` / ``client.save_water_room_info(...)``。
"""

from __future__ import annotations

import sys

from _config import build_parser, resolve_open_id

from hnu_utility import HnuError, HnuUtilityClient


def main() -> int:
    parser = build_parser("房间绑定示例")
    parser.add_argument("--confirm", action="store_true", help="确认重新保存当前绑定（幂等写操作）")
    args = parser.parse_args()
    open_id = resolve_open_id(parser, args)

    with HnuUtilityClient(open_id) as client:
        try:
            user = client.get_wx_user().user
        except HnuError as exc:
            print(f"查询失败：{exc}", file=sys.stderr)
            return 1

        print("当前绑定：")
        print(f"  校区：{user.xiao_qu_name}（id={user.xiao_qu_id}）")
        print(f"  照明：{user.lou_dong_name} / {user.room_name}（id={user.room_id}）")
        print(f"  空调：{user.kt_lou_dong_name} / {user.kt_room_name}（id={user.kt_room_id}）")
        print(f"  水表：{user.water_lou_dong_name} / {user.water_room_name}（id={user.water_room_id}）")

        if not args.confirm:
            print("\n（只读预览结束；加 --confirm 可按当前绑定原样重新保存）")
            return 0

        if not all((user.xiao_qu_id, user.lou_dong_id, user.room_id, user.kt_lou_dong_id, user.kt_room_id)):
            print("\n绑定信息不完整，无法演示保存")
            return 1

        try:
            message = client.save_room_info(
                xiao_qu_id=user.xiao_qu_id,
                xiao_qu_name=user.xiao_qu_name,
                lou_dong_id=user.lou_dong_id,
                lou_dong_name=user.lou_dong_name,
                room_id=user.room_id,
                kt_lou_dong_id=user.kt_lou_dong_id,
                kt_lou_dong_name=user.kt_lou_dong_name,
                kt_room_id=user.kt_room_id,
            )
        except HnuError as exc:
            print(f"\n保存失败：{exc}", file=sys.stderr)
            return 1
        print(f"\nsave_room_info -> {message}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
