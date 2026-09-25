"""config 模块的单元测试。"""

from __future__ import annotations

import json

import pytest

from hnu_utility.config import load_config, load_open_id


def test_load_missing_returns_empty(tmp_path):
    assert load_config(tmp_path / "nope.json") == {}
    assert load_open_id(tmp_path / "nope.json") is None


def test_load_reads_dict(tmp_path):
    path = tmp_path / "hnu_config.json"
    path.write_text(json.dumps({"openId": "ofTEST"}), encoding="utf-8")
    assert load_config(path) == {"openId": "ofTEST"}
    assert load_open_id(path) == "ofTEST"


def test_load_invalid_json_warns(tmp_path):
    path = tmp_path / "hnu_config.json"
    path.write_text("{ not json", encoding="utf-8")
    with pytest.warns(RuntimeWarning):
        assert load_config(path) == {}


def test_load_non_dict_warns(tmp_path):
    path = tmp_path / "hnu_config.json"
    path.write_text("[1, 2]", encoding="utf-8")
    with pytest.warns(RuntimeWarning):
        assert load_config(path) == {}
    with pytest.warns(RuntimeWarning):
        assert load_open_id(path) is None


def test_load_open_id_rejects_empty(tmp_path):
    path = tmp_path / "hnu_config.json"
    path.write_text(json.dumps({"openId": ""}), encoding="utf-8")
    assert load_open_id(path) is None
