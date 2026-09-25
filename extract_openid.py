#!/usr/bin/env python3
r"""
海南大学水电费 - 提取 openId 工具

优先从本机微信缓存中直接扫描 openId（无需抓包）；
找不到时进入监听模式，打开小程序即可自动捕获；
仍失败可回退到 mitmproxy 抓包流程（--proxy 可直接进入）。

用法:
    python extract_openid.py            # 扫描 -> 监听 -> (可选)抓包
    python extract_openid.py --proxy    # 直接走 mitmproxy 抓包
"""

import os
import re
import sys
import time
import json
import threading
import subprocess
import ctypes
import tempfile

CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hnu_config.json")
ADDON_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_capture_addon.py")
OUTPUT_FILE = os.path.join(tempfile.gettempdir(), "hnu_openid.txt")
PROXY_PORT = 18889
PROXY_TIMEOUT_SECONDS = 120
WATCH_SECONDS = 180
POLL_INTERVAL = 2

ADDON_CODE_TEMPLATE = r'''
import json
from mitmproxy import http

TARGET = "sdxt.hainanu.edu.cn"
OUTPUT_FILE = r"{output_file}"

def response(flow: http.HTTPFlow):
    if TARGET not in flow.request.pretty_host:
        return
    url = flow.request.pretty_url
    if "getWxUser" in url or "getOpenId" in url or "getLeftMoney" in url:
        openid = flow.request.query.get("openId")
        if openid:
            print("\n*** OPENID_CAPTURED:" + openid + " ***\n", flush=True)
            try:
                with open(OUTPUT_FILE, "w") as f:
                    f.write(openid.strip())
            except OSError:
                pass
'''


def mask(open_id):
    return open_id[:8] + "..." + open_id[-4:] if len(open_id) > 14 else open_id


_CAPTURE_RE = re.compile(r"OPENID_CAPTURED:(\S+)")


def parse_capture_line(line):
    """从 mitmdump 输出行中解析 openId，未命中返回 None。"""
    match = _CAPTURE_RE.search(line)
    return match.group(1) if match else None


def save_config(open_id):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump({"openId": open_id}, f, ensure_ascii=False)


def verify_open_id(open_id):
    """调用 getWxUser 验证 openId，返回 (姓名, 错误信息)。"""
    try:
        from hnu_utility import HnuUtilityClient
    except ImportError:
        return None, "缺少依赖：请先 pip install -e . 或 pip install httpx"
    try:
        with HnuUtilityClient(open_id, timeout=8) as client:
            user = client.get_wx_user().user
            return (user.real_name or user.nick_name or "未知用户"), None
    except Exception as exc:
        return None, f"{type(exc).__name__}: {exc}"


# ─────────────────────────── 方式一：本地扫描 ───────────────────────────


def scan_once():
    from hnu_utility import scan_open_ids

    return scan_open_ids()


def pick_valid(candidates):
    """逐个验证候选 openId，返回 [(open_id, 姓名), ...]。"""
    valid = []
    for candidate in candidates:
        name, error = verify_open_id(candidate)
        if name:
            print(f"    [有效] {mask(candidate)}  {name}")
            valid.append((candidate, name))
        else:
            print(f"    [无效] {mask(candidate)}  ({error})")
    return valid


def confirm_and_save(valid):
    if len(valid) > 1:
        print(f"\n  发现 {len(valid)} 个有效 openId：")
        for i, (_, name) in enumerate(valid, 1):
            print(f"    {i}. {name}")
        choice = input("  输入序号选择 [1]: ").strip() or "1"
        try:
            open_id, _ = valid[int(choice) - 1]
        except (ValueError, IndexError):
            print("  [取消] 无效序号")
            return False
    else:
        open_id, name = valid[0]
        print(f"\n  匹配到：{name}")

    save_config(open_id)
    print(f"\n  {'='*40}")
    print(f"  V 配置成功！openId: {mask(open_id)}")
    print(f"  V 已保存到 {CONFIG_FILE}")
    print(f"  {'='*40}\n")
    return True


def scan_flow(watch):
    """本地扫描流程。watch=True 时轮询等待用户打开小程序。返回是否成功。"""
    if watch:
        print(f"  请在 PC 微信中打开「海大售电」小程序（任意页面即可），最长等待 {WATCH_SECONDS}s")
        deadline = time.time() + WATCH_SECONDS
        candidates = []
        while time.time() < deadline:
            candidates = scan_once()
            if candidates:
                break
            print(f"\r  监听中... 剩余 {int(deadline - time.time())}s ", end="", flush=True)
            time.sleep(POLL_INTERVAL)
        print()
    else:
        print("  [1/2] 扫描本机微信缓存...")
        candidates = scan_once()

    if not candidates:
        return False

    print(f"  [2/2] 找到 {len(candidates)} 个候选，正在向服务器验证...\n")
    valid = pick_valid(candidates)
    if not valid:
        return False
    return confirm_and_save(valid)


# ─────────────────────────── 方式二：mitmproxy 抓包 ───────────────────────────

_INTERNET_SETTINGS = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Internet Settings"


def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except (AttributeError, OSError):
        return False


def get_proxy_settings():
    """读取当前系统代理设置，供流程结束后恢复。"""
    import winreg
    values = {}
    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, _INTERNET_SETTINGS, 0, winreg.KEY_QUERY_VALUE)
    try:
        for name in ("ProxyEnable", "ProxyServer", "ProxyOverride"):
            try:
                values[name] = winreg.QueryValueEx(key, name)[0]
            except FileNotFoundError:
                pass
    finally:
        winreg.CloseKey(key)
    return values


def set_proxy(enable, port=PROXY_PORT):
    import winreg
    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, _INTERNET_SETTINGS, 0, winreg.KEY_SET_VALUE)
    if enable:
        winreg.SetValueEx(key, "ProxyEnable", 0, winreg.REG_DWORD, 1)
        winreg.SetValueEx(key, "ProxyServer", 0, winreg.REG_SZ, f"127.0.0.1:{port}")
    else:
        winreg.SetValueEx(key, "ProxyEnable", 0, winreg.REG_DWORD, 0)
        try:
            winreg.DeleteValue(key, "ProxyServer")
        except FileNotFoundError:
            pass
    winreg.CloseKey(key)


def restore_proxy(previous):
    """把系统代理恢复为进入抓包流程前的状态。"""
    import winreg
    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, _INTERNET_SETTINGS, 0, winreg.KEY_SET_VALUE)
    try:
        winreg.SetValueEx(key, "ProxyEnable", 0, winreg.REG_DWORD, int(previous.get("ProxyEnable", 0)))
        for name in ("ProxyServer", "ProxyOverride"):
            if name in previous:
                winreg.SetValueEx(key, name, 0, winreg.REG_SZ, str(previous[name]))
            else:
                try:
                    winreg.DeleteValue(key, name)
                except FileNotFoundError:
                    pass
    finally:
        winreg.CloseKey(key)


def install_ca_cert():
    cert_path = os.path.expanduser(r"~\.mitmproxy\mitmproxy-ca-cert.pem")
    if not os.path.exists(cert_path):
        try:
            subprocess.run(["mitmdump", "--version"], capture_output=True, timeout=10)
        except (OSError, subprocess.SubprocessError):
            return False
        if not os.path.exists(cert_path):
            return False

    try:
        store = subprocess.run(
            ["certutil", "-addstore", "-user", "Root", cert_path],
            capture_output=True, text=True, timeout=10
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return store.returncode == 0


def kill_mitmproxy():
    subprocess.run(["taskkill", "/f", "/im", "mitmdump.exe"],
                   capture_output=True)


def proxy_flow():
    print("\n"
          "  +--------------------------------+\n"
          "  |  海南大学水电费 - 抓包模式     |\n"
          "  +--------------------------------+\n")

    try:
        check = subprocess.run(["mitmdump", "--version"], capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        check = None
    if check is None or check.returncode != 0:
        print("  [错误] 未找到 mitmproxy，请先安装:")
        print("         pip install mitmproxy")
        return

    kill_mitmproxy()
    time.sleep(1)

    print("  [1/4] 安装代理证书...")
    try:
        consent = input("  是否将 mitmproxy 根证书安装到当前用户证书库（Root）？[y/N]: ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        consent = ""
    if consent == "y":
        if install_ca_cert():
            print("  [✓] 证书已安装")
        else:
            print("  [警告] 证书安装失败，可能需要管理员权限；HTTPS 抓包可能失败")
    else:
        print("  [跳过] 未安装证书（若之前已手动安装过，可继续）")

    if os.path.exists(OUTPUT_FILE):
        os.remove(OUTPUT_FILE)
    with open(ADDON_FILE, "w", encoding="utf-8") as f:
        f.write(ADDON_CODE_TEMPLATE.format(output_file=OUTPUT_FILE.replace("\\", "\\\\")))

    print(f"  [2/4] 启动代理 (端口 {PROXY_PORT})...")
    mitm = subprocess.Popen(
        ["mitmdump", "-s", ADDON_FILE, "-p", str(PROXY_PORT),
         "--set", "block_global=false"],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, creationflags=subprocess.CREATE_NO_WINDOW
    )
    time.sleep(3)

    if mitm.poll() is not None:
        out = mitm.stdout.read() if mitm.stdout else ""
        print(f"  [错误] mitmdump 启动失败: {out[:200]}")
        return
    print("  [✓] 代理已启动")

    print(f"  [3/4] 设置系统代理...")
    try:
        previous_proxy = get_proxy_settings()
    except (ImportError, OSError):
        previous_proxy = {}
    set_proxy(True, PROXY_PORT)
    print("  [✓] 系统代理已设置")

    print(f"\n  +-------------------------------------+")
    print(f"  |  请打开微信，进入「海大售电」    |")
    print(f"  |  小程序，等待自动检测...            |")
    print(f"  |  超时时间: {PROXY_TIMEOUT_SECONDS} 秒     |")
    print(f"  +-------------------------------------+\n")

    captured_oid = None
    stop_event = threading.Event()

    def reader_thread():
        nonlocal captured_oid
        while not stop_event.is_set():
            if mitm.stdout is None:
                break
            line = mitm.stdout.readline()
            if not line:
                break
            if "OPENID_CAPTURED:" in line:
                captured = parse_capture_line(line)
                if captured:
                    captured_oid = captured
                    stop_event.set()
                    break

    reader = threading.Thread(target=reader_thread, daemon=True)
    reader.start()

    start_time = time.time()
    try:
        while time.time() - start_time < PROXY_TIMEOUT_SECONDS:
            elapsed = int(time.time() - start_time)
            if elapsed > 0 and elapsed % 5 == 0:
                print(f"\r  等待中... ({elapsed}s / {PROXY_TIMEOUT_SECONDS}s)", end="", flush=True)

            if os.path.exists(OUTPUT_FILE):
                try:
                    with open(OUTPUT_FILE, "r") as f:
                        content = f.read().strip()
                        if content and len(content) >= 20:
                            captured_oid = content
                            break
                except OSError:
                    pass

            if captured_oid:
                break

            time.sleep(1)
    except KeyboardInterrupt:
        pass

    print()
    print("  [4/4] 清理...")
    stop_event.set()
    try:
        restore_proxy(previous_proxy)
    except (ImportError, OSError):
        set_proxy(False)
    kill_mitmproxy()
    try:
        os.remove(ADDON_FILE)
    except OSError:
        pass
    try:
        os.remove(OUTPUT_FILE)
    except OSError:
        pass

    if captured_oid:
        name, error = verify_open_id(captured_oid)
        if name:
            save_config(captured_oid)
            print(f"\n  {'='*40}")
            print(f"  V 配置成功！openId: {mask(captured_oid)}（{name}）")
            print(f"  V 已保存到 {CONFIG_FILE}")
            print(f"  {'='*40}\n")
        else:
            print(f"\n  [警告] 捕获到 openId 但验证失败：{error}")
            print("  未写入配置；请确认小程序能正常打开、网络可用后重试\n")
    else:
        print(f"\n  [失败] 未检测到 openId")
        print(f"  可能的原因:")
        print(f"    - 微信未完全关闭后重新打开")
        print(f"    - 小程序未打开或网络异常")
        print(f"    - 代理端口被占用")
        print(f"  请关闭微信后重试\n")


# ─────────────────────────── 入口 ───────────────────────────


def main():
    print("\n"
          "  +--------------------------------+\n"
          "  |  海南大学水电费 - 提取 openId  |\n"
          "  +--------------------------------+\n")

    if "--proxy" in sys.argv[1:]:
        proxy_flow()
        return

    try:
        import hnu_utility  # noqa: F401
    except ImportError:
        print("  [提示] 未安装本库依赖，跳过本地扫描（pip install -e .）\n")
        proxy_flow()
        return

    if scan_flow(watch=False):
        return

    print("\n  本地缓存中没有找到。请在 PC 微信中打开一次「海大售电」小程序\n")
    if scan_flow(watch=True):
        return

    try:
        answer = input("\n  仍未找到。是否回退到 mitmproxy 抓包流程？[y/N]: ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        answer = ""
    if answer == "y":
        proxy_flow()
    else:
        print("\n  已退出。提示：打开小程序后重新运行本脚本即可。\n")


if __name__ == "__main__":
    main()
