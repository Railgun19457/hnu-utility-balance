"""extract_openid 脚本中纯函数的单元测试。"""

from __future__ import annotations

import json

import extract_openid
from extract_openid import choose_mode, parse_capture_line, save_config

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


def test_choose_mode_defaults_to_scan(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _prompt: "")
    assert choose_mode() == "scan"


def test_choose_mode_accepts_proxy(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _prompt: "2")
    assert choose_mode() == "proxy"


def test_choose_mode_retries_invalid_input(monkeypatch):
    answers = iter(["x", "2"])
    monkeypatch.setattr("builtins.input", lambda _prompt: next(answers))
    assert choose_mode() == "proxy"


def test_choose_mode_falls_back_to_scan_on_eof(monkeypatch):
    def raise_eof(_prompt):
        raise EOFError

    monkeypatch.setattr("builtins.input", raise_eof)
    assert choose_mode() == "scan"
