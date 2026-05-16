#!/usr/bin/env python3
"""
海南大学水电费查询工具
首次使用请先运行 extract_openid.py 提取 openId
之后直接运行此脚本即可。

用法: python hnu_query.py
"""

import hashlib
import time
import json
import os
import sys
import requests
import urllib3

urllib3.disable_warnings()

BASE_URL = "https://sdxt.hainanu.edu.cn/scanQRWaterCtrl_redis_hndx1/service"
APP_ID = "sz@cgdz#2021$11"
APP_SECRET = "&szcgdz"
CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hnu_config.json")


def make_sign(timestamp):
    return hashlib.md5((APP_ID + str(timestamp) + APP_SECRET).encode()).hexdigest()


def load_openid():
    if not os.path.exists(CONFIG_FILE):
        return None
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        config = json.load(f)
    return config.get("openId")


def query(open_id):
    ts = int(time.time() * 1000)
    sign = make_sign(ts)

    resp = requests.get(f"{BASE_URL}/applet/getWxUser", params={
        "openId": open_id, "appid": APP_ID, "timestamp": ts, "sign": sign,
    }, timeout=10, verify=False)

    if resp.status_code != 200:
        return None, f"服务器错误: HTTP {resp.status_code}"

    data = resp.json()
    if data.get("statusCode") != "200":
        return None, data.get("message", "查询失败: 请确认 openId 有效，可重新运行 extract_openid.py")

    user = data["resultObject"]["user"]
    result = {
        "name": user.get("realName", user.get("nickName", "")),
        "school": user.get("schoolName", ""),
        "balance": float(user.get("amount", "0") or "0"),
        "free_balance": float(user.get("freeMoney", "0") or "0"),
        "building": user.get("louDongName", ""),
        "room": user.get("roomName", ""),
    }

    # 照明+插座
    resp = requests.get(f"{BASE_URL}/weixinEle/getEleInfo", params={
        "openId": open_id, "type": "1",
    }, timeout=10, verify=False)
    data = resp.json()
    if data.get("statusCode") == "200":
        obj = data["resultObject"]
        result["light"] = {
            "kwh": obj.get("leftEle", "0"),
            "money": obj.get("leftMoney", "0"),
            "time": obj.get("monTime", ""),
        }

    # 空调
    resp = requests.get(f"{BASE_URL}/weixinEle/getEleInfo", params={
        "openId": open_id, "type": "2",
    }, timeout=10, verify=False)
    data = resp.json()
    if data.get("statusCode") == "200":
        obj = data["resultObject"]
        result["ac"] = {
            "kwh": obj.get("leftEle", "0"),
            "money": obj.get("leftMoney", "0"),
            "time": obj.get("monTime", ""),
        }

    # 水表
    resp = requests.get(f"{BASE_URL}/weixinEle/getWaterInfo", params={
        "openId": open_id,
    }, timeout=10, verify=False)
    data = resp.json()
    if data.get("statusCode") == "200":
        obj = data["resultObject"]
        result["water"] = {
            "tons": obj.get("leftWater", "0"),
            "money": obj.get("leftMoney", "0"),
            "time": obj.get("monTime", ""),
        }

    return result, None


def fmt(n):
    """Format number: show 2 decimal places if needed"""
    try:
        f = float(n)
        if f == int(f):
            return str(int(f))
        return f"{f:.2f}"
    except:
        return str(n)


def print_result(r):
    print(f"""
  {'='*44}
   海南大学水电费查询
  {'='*44}
   姓名: {r['name']}
   学校: {r['school']}
   楼栋: {(r.get('building') or '未绑定')}
   房间: {(r.get('room') or '未绑定')}
   热水余额: {fmt(r['balance'])} 元 (赠送: {fmt(r.get('free_balance', 0))} 元)
  {'─'*44}""")

    if r.get("light"):
        e = r["light"]
        print(f"  照明+插座:  {fmt(e['kwh']):>6} 度 / {fmt(e['money']):>6} 元   [{e.get('time', '')}]")

    if r.get("ac"):
        e = r["ac"]
        print(f"  空调:       {fmt(e['kwh']):>6} 度 / {fmt(e['money']):>6} 元   [{e.get('time', '')}]")

    if r.get("water"):
        w = r["water"]
        print(f"  水表:       {fmt(w['tons']):>6} 吨 / {fmt(w['money']):>6} 元   [{w.get('time', '')}]")

    total = r["balance"] + r.get("free_balance", 0)
    for e in [r.get("light"), r.get("ac")]:
        if e:
            total += float(e.get("money", 0))
    if r.get("water"):
        total += float(r["water"].get("money", 0))

    print(f"  {'─'*44}")
    print(f"  资产总计:   {fmt(total)} 元")
    print()


def main():
    # Try argv first
    if len(sys.argv) > 1:
        open_id = sys.argv[1]
    else:
        open_id = load_openid()

    if not open_id:
        print("""
  ╔══════════════════════════════╗
  ║  首次使用请先运行:            ║
  ║  python extract_openid.py    ║
  ╚══════════════════════════════╝

  或手动指定: python hnu_query.py <你的openId>
""")
        return

    print("  正在查询...", end="", flush=True)
    result, err = query(open_id)
    print("\r" + " " * 20 + "\r", end="")

    if err:
        print(f"\n  [错误] {err}")
        return

    print_result(result)


if __name__ == "__main__":
    main()