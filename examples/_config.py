"""示例共用工具：解析 openId 参数；未安装本库时回退到仓库根目录。

各示例脚本通过 ``from _config import parse_open_id`` 使用；
需要额外命令行参数时用 ``build_parser`` / ``resolve_open_id``。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if __package__ in (None, ""):
    sys.path.insert(0, str(_REPO_ROOT))

from hnu_utility import load_open_id  # noqa: E402


def build_parser(description: str) -> argparse.ArgumentParser:
    """创建带 ``open_id`` 位置参数的解析器，便于示例追加自己的参数。"""
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument(
        "open_id",
        nargs="?",
        help="openId；缺省时依次查找当前目录与仓库根目录下的 hnu_config.json",
    )
    return parser


def resolve_open_id(parser: argparse.ArgumentParser, args: argparse.Namespace) -> str:
    """从解析结果取 openId，缺省时读配置文件；取不到则报错退出。"""
    open_id = (
        args.open_id
        or load_open_id("hnu_config.json")
        or load_open_id(_REPO_ROOT / "hnu_config.json")
    )
    if not open_id:
        parser.error("未提供 openId：请先运行 extract_openid.py，或以参数传入")
    return str(open_id)


def parse_open_id(description: str) -> str:
    """解析命令行中的可选 ``openId``，缺省时读取 ``hnu_config.json``。"""
    parser = build_parser(description)
    return resolve_open_id(parser, parser.parse_args())
