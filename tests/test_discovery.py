"""discovery 模块的单元测试（不访问真实网络与真实微信目录）。"""

from __future__ import annotations

from hnu_utility import discovery
from hnu_utility.discovery import scan_open_ids

OID_A = "otest00000000000000000000000"  # 28 位，o 开头（合成值）
OID_B = "oABCDEFGHIJKLMNOPQRSTUVWXYZ1"  # 28 位（合成值）


def test_scan_finds_open_id_in_getopenid_response(tmp_path):
    cache = tmp_path / "Cache_Data" / "data_1"
    cache.parent.mkdir()
    body = (
        b"a10bv0w3IFj373MK61w34Uqg100bv06\x00"
        b'{"statusCode":"200","message":null,"resultObject":"' + OID_A.encode() + b'"}\x00'
    )
    cache.write_bytes(body)
    assert scan_open_ids([tmp_path]) == [OID_A]


def test_scan_finds_open_id_in_json_field(tmp_path):
    f = tmp_path / "resp.bin"
    f.write_bytes(b'{"statusCode":"200","resultObject":{"user":{"openId":"' + OID_B.encode() + b'"}}}')
    assert scan_open_ids([tmp_path]) == [OID_B]


def test_scan_finds_open_id_in_query_string(tmp_path):
    f = tmp_path / "url.bin"
    f.write_bytes(b"GET /service/applet/getWxUser?openId=" + OID_A.encode() + b"&appid=x HTTP/1.1")
    assert scan_open_ids([tmp_path]) == [OID_A]


def test_scan_dedupes_and_orders(tmp_path):
    f = tmp_path / "mix.bin"
    f.write_bytes(b'"openId":"' + OID_B.encode() + b'" "resultObject":"' + OID_A.encode() + b'"')
    ids = scan_open_ids([tmp_path])
    assert ids == [OID_A, OID_B]  # resultObject 模式优先


def test_scan_skips_oversized_files(tmp_path):
    f = tmp_path / "big.bin"
    with f.open("wb") as fp:
        fp.write(b'"openId":"' + OID_A.encode() + b'"')
        fp.truncate(300 * 1024 * 1024)  # sparse，不实际分配磁盘
    assert scan_open_ids([tmp_path], max_file_size=1024) == []


def test_scan_matches_across_chunk_boundaries(tmp_path, monkeypatch):
    monkeypatch.setattr(discovery, "_CHUNK_SIZE", 32)
    f = tmp_path / "boundary.bin"
    f.write_bytes(b"padding" * 3 + b'"openId":"' + OID_B.encode() + b'"')
    assert scan_open_ids([tmp_path]) == [OID_B]


def test_scan_orders_by_specificity_across_files(tmp_path):
    weak = tmp_path / "a_weak.bin"
    weak.write_bytes(b"GET /service/applet/getWxUser?openId=" + OID_B.encode() + b"&appid=x HTTP/1.1")
    strong = tmp_path / "b_strong.bin"
    strong.write_bytes(b'{"statusCode":"200","resultObject":"' + OID_A.encode() + b'"}')
    assert scan_open_ids([tmp_path]) == [OID_A, OID_B]


def test_scan_missing_path(tmp_path):
    assert scan_open_ids([tmp_path / "nope"]) == []


def test_scan_ignores_invalid_candidates(tmp_path):
    f = tmp_path / "short.bin"
    f.write_bytes(b'"openId":"oSHORT123"')  # 长度不足 28
    f2 = tmp_path / "bad.bin"
    f2.write_bytes(b'"openId":"X' + b"A" * 27 + b'"')  # 非 o 开头
    assert scan_open_ids([tmp_path]) == []
