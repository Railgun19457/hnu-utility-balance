#!/usr/bin/env python3
r"""
海大售电 - openId 提取工具

先在 PC 微信中打开一次「海大售电」小程序，再从本机微信缓存中直接扫描 openId（无需抓包）；
扫描失败可回退到 mitmproxy 抓包流程。

用法:
    python extract_openid.py            # 交互式选择模式
    python extract_openid.py --scan     # 直接扫描本机微信缓存
    python extract_openid.py --proxy    # 直接走 mitmproxy 抓包
"""

import json
import os
import re
import subprocess
import sys
import tempfile
import threading
import time

CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hnu_config.json")
ADDON_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_capture_addon.py")
OUTPUT_FILE = os.path.join(tempfile.gettempdir(), "hnu_openid.txt")
PROXY_PORT = 18889
PROXY_TIMEOUT_SECONDS = 120

ADDON_CODE_TEMPLATE = r"""
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
"""


def mask(open_id):
    return open_id[:8] + "..." + open_id[-4:] if len(open_id) > 14 else open_id


_CAPTURE_RE = re.compile(r"OPENID_CAPTURED:(\S+)")


def parse_capture_line(line):
    """从 mitmdump 输出行中解析 openId，未命中返回 None。"""
    match = _CAPTURE_RE.search(line)
    return match.group(1) if match else None


def save_config(open_id):
    """写入 openId，保留配置文件中已有的其他键。"""
    config = {}
    try:
        with open(CONFIG_FILE, encoding="utf-8") as f:
            existing = json.load(f)
        if isinstance(existing, dict):
            config = existing
    except (OSError, ValueError):
        pass
    config["openId"] = open_id
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False)


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
    print(f"\n  {'=' * 40}")
    print(f"  V 配置成功！openId: {mask(open_id)}")
    print(f"  V 已保存到 {CONFIG_FILE}")
    print(f"  {'=' * 40}\n")
    return True


def scan_flow():
    """本地扫描流程。返回是否成功。"""
    print("  [1/2] 扫描本机微信缓存（前提：已在 PC 微信打开过一次「海大售电」小程序）...")
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
            ["certutil", "-addstore", "-user", "Root", cert_path], capture_output=True, text=True, timeout=10
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return store.returncode == 0


def kill_mitmproxy():
    subprocess.run(["taskkill", "/f", "/im", "mitmdump.exe"], capture_output=True)


def remove_file(path):
    try:
        os.remove(path)
    except OSError:
        pass


def proxy_flow():
    if not sys.platform.startswith("win"):
        print("\n  [错误] 抓包模式依赖 Windows 系统代理与 PC 微信，当前平台不支持")
        return

    print("\n  +-----------------------+\n  |  海大售电 - 抓包模式  |\n  +-----------------------+\n")

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
        ["mitmdump", "-s", ADDON_FILE, "-p", str(PROXY_PORT), "--set", "block_global=false"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    time.sleep(3)

    if mitm.poll() is not None:
        out = mitm.stdout.read() if mitm.stdout else ""
        print(f"  [错误] mitmdump 启动失败: {out[:200]}")
        kill_mitmproxy()
        remove_file(ADDON_FILE)
        return
    print("  [✓] 代理已启动")

    print("  [3/4] 设置系统代理...")
    captured_oid = None
    stop_event = threading.Event()
    previous_proxy = {}
    proxy_set = False

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

    def cleanup():
        stop_event.set()
        if proxy_set:
            try:
                restore_proxy(previous_proxy)
            except (ImportError, OSError):
                try:
                    set_proxy(False)
                except (ImportError, OSError):
                    print("  [警告] 系统代理恢复失败，请手动检查代理设置")
        kill_mitmproxy()
        remove_file(ADDON_FILE)
        remove_file(OUTPUT_FILE)

    try:
        try:
            previous_proxy = get_proxy_settings()
        except (ImportError, OSError):
            previous_proxy = {}
        proxy_set = True
        set_proxy(True, PROXY_PORT)
    except (ImportError, OSError):
        print("  [错误] 设置系统代理失败，请检查权限后重试")
        cleanup()
        return
    print("  [✓] 系统代理已设置")

    print("\n  +-------------------------------------+")
    print("  |  请打开微信，进入「海大售电」    |")
    print("  |  小程序，等待自动检测...            |")
    print(f"  |  超时时间: {PROXY_TIMEOUT_SECONDS} 秒     |")
    print("  +-------------------------------------+\n")

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
                    with open(OUTPUT_FILE) as f:
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
    finally:
        print()
        print("  [4/4] 清理...")
        cleanup()

    if captured_oid:
        name, error = verify_open_id(captured_oid)
        if name:
            save_config(captured_oid)
            print(f"\n  {'=' * 40}")
            print(f"  V 配置成功！openId: {mask(captured_oid)}（{name}）")
            print(f"  V 已保存到 {CONFIG_FILE}")
            print(f"  {'=' * 40}\n")
        else:
            print(f"\n  [警告] 捕获到 openId 但验证失败：{error}")
            print("  未写入配置；请确认小程序能正常打开、网络可用后重试\n")
    else:
        print("\n  [失败] 未检测到 openId")
        print("  可能的原因:")
        print("    - 微信未完全关闭后重新打开")
        print("    - 小程序未打开或网络异常")
        print("    - 代理端口被占用")
        print("  请关闭微信后重试\n")


# ─────────────────────────── 入口 ───────────────────────────


def choose_mode():
    """交互式选择运行模式，返回 ``"scan"`` 或 ``"proxy"``；无法输入时默认扫描。"""
    print("  请选择运行模式：")
    print("    1. 扫描本机微信缓存（推荐，前提：已在 PC 微信打开过一次小程序）")
    print("    2. mitmproxy 抓包（需要安装 mitmproxy）")

    while True:
        try:
            answer = input("\n  输入序号 [1]: ").strip() or "1"
        except (EOFError, KeyboardInterrupt):
            print()
            return "scan"
        if answer in ("1", "2"):
            return "scan" if answer == "1" else "proxy"
        print("  请输入 1 或 2")


def main():
    print(
        "\n  +------------------------------+\n  |  海大售电 - openId 提取工具  |\n  +------------------------------+\n"
    )

    args = sys.argv[1:]
    if "-h" in args or "--help" in args:
        print("  用法: python extract_openid.py [--scan | --proxy]\n")
        return

    if "--proxy" in args:
        proxy_flow()
        return

    mode = "scan" if "--scan" in args else choose_mode()
    if mode == "proxy":
        proxy_flow()
        return

    try:
        import hnu_utility  # noqa: F401
    except ImportError:
        print("  [提示] 未安装本库依赖，无法本地扫描（pip install -e .）\n")
        proxy_flow()
        return

    if scan_flow():
        return

    if hnu_utility.default_search_paths():
        print("\n  本地缓存中没有找到。请先在 PC 微信中打开一次「海大售电」小程序，再重新运行本脚本\n")
    else:
        print("\n  本机没有微信数据目录（可能未运行过 PC 微信），无法本地扫描\n")

    try:
        answer = input("\n  是否回退到 mitmproxy 抓包流程？[y/N]: ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        answer = ""
    if answer == "y":
        proxy_flow()
    else:
        print("\n  已退出。提示：打开小程序后重新运行本脚本即可。\n")


if __name__ == "__main__":
    main()
