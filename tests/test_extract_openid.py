"""extract_openid 脚本中纯函数的单元测试。"""

from __future__ import annotations

import json

import extract_openid
from extract_openid import parse_capture_line, save_config

OID = "otest00000000000000000000000"  # 合成值，非真实 openId


def test_parse_capture_line_with_marker():
    line = "\n*** OPENID_CAPTURED:" + OID + " ***\n"
    assert parse_capture_line(line) == OID


def test_parse_capture_line_without_marker():
    assert parse_capture_line("ordinary log line") is None


def test_save_config_preserves_existing_keys(tmp_path, monkeypatch):
    config = tmp_path / "hnu_config.json"
    config.write_text(json.dumps({"openId": "old", "other": 1}), encoding="utf-8")
    monkeypatch.setattr(extract_openid, "CONFIG_FILE", str(config))

    save_config(OID)

    data = json.loads(config.read_text(encoding="utf-8"))
    assert data == {"openId": OID, "other": 1}


def test_save_config_writes_when_missing(tmp_path, monkeypatch):
    config = tmp_path / "hnu_config.json"
    monkeypatch.setattr(extract_openid, "CONFIG_FILE", str(config))

    save_config(OID)

    assert json.loads(config.read_text(encoding="utf-8")) == {"openId": OID}
