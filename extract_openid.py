#!/usr/bin/env python3
r"""
海南大学水电费 - 提取 openId 工具
首次使用时运行此程序，之后只需运行 query.py 即可。

用法: python extract_openid.py
"""

import os
import sys
import time
import json
import signal
import threading
import subprocess
import ctypes
import tempfile

CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hnu_config.json")
ADDON_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_capture_addon.py")
OUTPUT_FILE = os.path.join(tempfile.gettempdir(), "hnu_openid.txt")
PROXY_PORT = 18889
TIMEOUT_SECONDS = 120

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
            except:
                pass
'''


def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False


def set_proxy(enable, port=PROXY_PORT):
    import winreg
    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                         r"SOFTWARE\Microsoft\Windows\CurrentVersion\Internet Settings",
                         0, winreg.KEY_SET_VALUE)
    if enable:
        winreg.SetValueEx(key, "ProxyEnable", 0, winreg.REG_DWORD, 1)
        winreg.SetValueEx(key, "ProxyServer", 0, winreg.REG_SZ, f"127.0.0.1:{port}")
    else:
        winreg.SetValueEx(key, "ProxyEnable", 0, winreg.REG_DWORD, 0)
        try:
            winreg.DeleteValue(key, "ProxyServer")
        except:
            pass
    winreg.CloseKey(key)


def install_ca_cert():
    cert_path = os.path.expanduser(r"~\.mitmproxy\mitmproxy-ca-cert.pem")
    if not os.path.exists(cert_path):
        subprocess.run(["mitmdump", "--version"], capture_output=True, timeout=10)
        if not os.path.exists(cert_path):
            return False

    try:
        store = subprocess.run(
            ["certutil", "-addstore", "-user", "Root", cert_path],
            capture_output=True, text=True, timeout=10
        )
        return "mitmproxy" in store.stdout.lower() or store.returncode == 0
    except:
        return False


def kill_mitmproxy():
    subprocess.run(["taskkill", "/f", "/im", "mitmdump.exe"],
                   capture_output=True)


def main():
    print("\n"
          "  +--------------------------------+\n"
          "  |  海南大学水电费 - 首次配置    |\n"
          "  +--------------------------------+\n")
    print("  此程序只需运行一次，完成后再运行 query.py 即可查电费。\n")

    try:
        r = subprocess.run(["mitmdump", "--version"], capture_output=True, text=True, timeout=10)
        if r.returncode != 0:
            raise Exception("mitmdump not working")
    except:
        print("  [错误] 未找到 mitmproxy，请先安装:")
        print("         pip install mitmproxy")
        return

    kill_mitmproxy()
    time.sleep(1)

    print("  [1/4] 安装代理证书...")
    if not install_ca_cert():
        print("  [警告] 证书安装可能需要管理员权限，忽略此步骤也可能工作")
    else:
        print("  [✓] 证书已安装")

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
    set_proxy(True, PROXY_PORT)
    print("  [✓] 系统代理已设置")

    print(f"\n  +-------------------------------------+")
    print(f"  |  请打开微信，进入「海大售电」    |")
    print(f"  |  小程序，等待自动检测...            |")
    print(f"  |  超时时间: {TIMEOUT_SECONDS} 秒     |")
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
                captured_oid = line.split("OPENID_CAPTURED:")[1].strip()
                stop_event.set()
                break

    reader = threading.Thread(target=reader_thread, daemon=True)
    reader.start()

    start_time = time.time()
    try:
        while time.time() - start_time < TIMEOUT_SECONDS:
            elapsed = int(time.time() - start_time)
            if elapsed > 0 and elapsed % 5 == 0:
                print(f"\r  等待中... ({elapsed}s / {TIMEOUT_SECONDS}s)", end="", flush=True)

            if os.path.exists(OUTPUT_FILE):
                try:
                    with open(OUTPUT_FILE, "r") as f:
                        content = f.read().strip()
                        if content and len(content) >= 20:
                            captured_oid = content
                            break
                except:
                    pass

            if captured_oid:
                break

            time.sleep(1)
    except KeyboardInterrupt:
        pass

    print()
    print("  [4/4] 清理...")
    stop_event.set()
    set_proxy(False)
    kill_mitmproxy()
    try:
        os.remove(ADDON_FILE)
    except:
        pass

    if captured_oid:
        config = {"openId": captured_oid}
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False)
        print(f"\n  {'='*40}")
        print(f"  V 配置成功！openId: {captured_oid}")
        print(f"  V 已保存到 {CONFIG_FILE}")
        print(f"  V 现在可以运行 python hnu_query.py 查电费了")
        print(f"  {'='*40}\n")
    else:
        print(f"\n  [失败] 未检测到 openId")
        print(f"  可能的原因:")
        print(f"    - 微信未完全关闭后重新打开")
        print(f"    - 小程序未打开或网络异常")
        print(f"    - 代理端口被占用")
        print(f"  请关闭微信后重试\n")


if __name__ == "__main__":
    main()