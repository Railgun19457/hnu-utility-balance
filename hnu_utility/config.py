"""配置文件读取（``hnu_config.json``）。"""

from __future__ import annotations

import json
import os
import warnings
from pathlib import Path
from typing import Any, Optional, Union

DEFAULT_CONFIG_FILENAME = "hnu_config.json"

_PathLike = Union[str, "os.PathLike[str]"]


def load_config(path: Optional[_PathLike] = None) -> dict[str, Any]:
    """读取配置文件，返回字典；文件不存在时返回空字典。

    默认读取当前目录下的 ``hnu_config.json``。文件存在但无法解析或内容不是
    JSON 对象时，发出 ``RuntimeWarning`` 并返回空字典。
    """
    config_path = Path(path) if path is not None else Path.cwd() / DEFAULT_CONFIG_FILENAME
    config_path = config_path.expanduser()
    if not config_path.is_file():
        return {}
    try:
        with config_path.open("r", encoding="utf-8") as fp:
            data = json.load(fp)
    except (OSError, ValueError) as exc:
        warnings.warn(f"无法解析配置文件 {config_path}：{exc}", RuntimeWarning, stacklevel=2)
        return {}
    if not isinstance(data, dict):
        warnings.warn(f"配置文件 {config_path} 的内容不是 JSON 对象，已忽略", RuntimeWarning, stacklevel=2)
        return {}
    return data


def load_open_id(path: Optional[_PathLike] = None) -> Optional[str]:
    """从配置文件读取 openId，取不到时返回 ``None``。"""
    value = load_config(path).get("openId")
    return value if isinstance(value, str) and value else None
