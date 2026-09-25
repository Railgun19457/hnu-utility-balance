"""extract_openid 脚本中纯函数的单元测试。"""

from __future__ import annotations

from extract_openid import parse_capture_line

OID = "otest00000000000000000000000"  # 合成值，非真实 openId


def test_parse_capture_line_with_marker():
    line = "\n*** OPENID_CAPTURED:" + OID + " ***\n"
    assert parse_capture_line(line) == OID


def test_parse_capture_line_without_marker():
    assert parse_capture_line("ordinary log line") is None
