"""JSON 解析器测试：与标准库 roundtrip 对照 + 严格错误路径。pytest -q"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "cs"))

from json_parser import JSONParseError, dumps, loads, minify  # noqa: E402

SAMPLES = [
    1, -3, 2.5, -1.25e-3, "hello", "中文\n换行\t制表", True, False, None,
    [], [1, [2, [3]]], {}, {"a": 1},
    {"name": "燕云", "tags": ["武侠", "开放世界"], "meta": {"year": 2024, "free": True}},
    {"nested": {"deep": {"deeper": [1, {"x": None}]}}},
]


@pytest.mark.parametrize("value", SAMPLES)
def test_roundtrip_with_stdlib(value):
    ours = loads(dumps(value))
    theirs = json.loads(json.dumps(value, ensure_ascii=False))
    assert ours == theirs


def test_parse_stdlib_output():
    obj = {"list": [1, 2.5, "混合", None, True], "obj": {"k": "v"}}
    text = json.dumps(obj, ensure_ascii=False, indent=2)
    assert loads(text) == obj


def test_string_escapes():
    assert loads(r'"a\nb"') == "a\nb"
    assert loads(r'"A"') == "A"
    assert loads(r'"\u4e2d\u6587"') == "中文"
    # 代理对：😀 = \uD83D\uDE00
    assert loads(r'"\ud83d\ude00"') == "\U0001F600"


def test_number_edge_cases():
    assert loads("0") == 0
    assert loads("-0") == 0
    assert loads("1e3") == 1000.0
    assert loads("2.5E-2") == 0.025
    assert loads("-12.75") == -12.75
    for bad in ("01", "1.", ".5", "1e", "-", "+1", "0x1"):
        with pytest.raises(JSONParseError):
            loads(bad)


def test_error_positions():
    with pytest.raises(JSONParseError) as e:
        loads('{\n  "a": 1,\n}')
    assert "第 3 行" in str(e.value)
    with pytest.raises(JSONParseError) as e:
        loads("[1, 2")
    assert "第 1 行" in str(e.value)


def test_trailing_content_rejected():
    with pytest.raises(JSONParseError):
        loads('{"a": 1} extra')
    with pytest.raises(JSONParseError):
        loads("null null")


def test_duplicate_keys_last_wins():
    assert loads('{"a": 1, "a": 2}') == {"a": 2}


def test_minify_and_dumps_indent():
    assert minify('{ "a" : 1 , "b" : [ 1 , 2 ] }') == '{"a":1,"b":[1,2]}'
    assert json.loads(minify('{ "a" : 1 , "b" : [ 1 , 2 ] }')) == {"a": 1, "b": [1, 2]}
    pretty = dumps({"a": [1, 2]}, indent=2)
    assert pretty == '{\n  "a": [\n    1,\n    2\n  ]\n}'
    assert json.loads(pretty) == {"a": [1, 2]}


def test_dumps_ensure_ascii_and_solidus():
    assert dumps("<a>") == '"<a>"'                      # 不强制转义 / 与 <
    assert dumps("中文", ensure_ascii=True) == '"\\u4e2d\\u6587"'
    assert json.loads(dumps("中文", ensure_ascii=True)) == "中文"


def test_nan_rejected():
    with pytest.raises(ValueError):
        dumps(float("nan"))


def test_deep_nesting():
    depth = 60
    value = json.loads("[" * depth + "]" * depth)
    assert loads("[" * depth + "]" * depth) == value
