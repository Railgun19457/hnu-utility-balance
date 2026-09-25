"""从本机微信数据中扫描 openId（无需抓包）。

PC 微信运行过「海大售电」小程序后，webview 的 HTTP 磁盘缓存会保留接口
响应原文（例如 ``/applet/getOpenId`` 的返回 ``{"statusCode":"200",
"resultObject":"ofDET4_..."}``），其中包含 openId。本模块扫描这些文件
提取候选 openId。

用法::

    from hnu_utility import scan_open_ids

    for open_id in scan_open_ids():
        ...  # 建议再用 get_wx_user() 验证
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import List, Optional, Sequence, Tuple, Union

PathLike = Union[str, "os.PathLike[str]"]

# openId 形如：o + 27 位 [0-9A-Za-z_-]，共 28 字符
_OPEN_ID_BYTES = rb"o[0-9A-Za-z_\-]{27}"

# 按特异性排列：getOpenId 响应 > 用户信息 JSON > URL 查询串
_PATTERNS = (
    re.compile(rb'"resultObject"\s*:\s*"(' + _OPEN_ID_BYTES + rb')"'),
    re.compile(rb'"openId"\s*:\s*"(' + _OPEN_ID_BYTES + rb')"'),
    re.compile(rb"[?&]openId=(" + _OPEN_ID_BYTES + rb")"),
)

MAX_SCAN_FILE_SIZE = 256 * 1024 * 1024
_CHUNK_SIZE = 1024 * 1024
_OVERLAP = 64  # 保证跨块边界的匹配也能被找到


def default_search_paths() -> List[Path]:
    """返回常见的微信数据目录（存在才返回）。

    - 微信 4.x：``%APPDATA%\\Tencent\\xwechat\\radium\\web\\profiles\\*``
      与 ``%APPDATA%\\Tencent\\xwechat\\radium\\users\\*``
    - 微信 3.x：``~/Documents/WeChat Files/Applet``
    """
    paths: List[Path] = []

    appdata = os.getenv("APPDATA")
    if appdata:
        radium = Path(appdata) / "Tencent" / "xwechat" / "radium"
        profiles = radium / "web" / "profiles"
        if profiles.is_dir():
            paths.extend(p for p in profiles.iterdir() if p.is_dir())
        users = radium / "users"
        if users.is_dir():
            paths.append(users)

    legacy = Path.home() / "Documents" / "WeChat Files" / "Applet"
    if legacy.is_dir():
        paths.append(legacy)

    return paths


def _scan_file(path: Path) -> List[str]:
    """流式扫描单个文件，结果按模式特异性排序。"""
    hits: List[Tuple[int, str]] = []
    tail = b""
    with path.open("rb") as fp:
        while True:
            chunk = fp.read(_CHUNK_SIZE)
            if not chunk:
                break
            data = tail + chunk
            for priority, pattern in enumerate(_PATTERNS):
                for match in pattern.finditer(data):
                    hits.append((priority, match.group(1).decode("ascii")))
            tail = data[-_OVERLAP:]
    hits.sort(key=lambda item: item[0])
    return [value for _, value in hits]


def scan_open_ids(
    paths: Optional[Sequence[PathLike]] = None,
    *,
    max_file_size: int = MAX_SCAN_FILE_SIZE,
) -> List[str]:
    """扫描目录下的文件，返回去重后的候选 openId 列表。

    按目录遍历顺序扫描；同一文件内按模式特异性排序（getOpenId 响应最优）。
    文件分块读取，内存占用与文件大小无关；不可读的文件 / 目录会被跳过。
    """
    if paths is None:
        paths = default_search_paths()

    found: List[str] = []
    seen = set()

    for root in paths:
        root_path = Path(root)
        if not root_path.is_dir():
            continue
        for dir_path, _dir_names, file_names in os.walk(root_path, onerror=lambda _: None):
            for file_name in file_names:
                file = Path(dir_path) / file_name
                try:
                    if file.stat().st_size > max_file_size:
                        continue
                    values = _scan_file(file)
                except OSError:
                    continue
                for value in values:
                    if value not in seen:
                        seen.add(value)
                        found.append(value)

    return found
