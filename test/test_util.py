import pytest

from upb_lib.util import parse_flags, parse_url, seconds_to_rate


def test_parse_url_valid_tcp_backward_compatible():
    url = parse_url("tcp://some.host")
    assert url == "tcp://some.host:2101"


def test_parse_url_valid_tcp_ignore_if_port():
    url = parse_url("tcp://some.host:1234")
    assert url == "tcp://some.host:1234"


def test_parse_url_valid_serial_backward_compatible():
    url = parse_url("serial:///dev/tty")
    assert url == "device:///dev/tty"


def test_parse_url_valid_serial_backward_compatible_with_baud():
    url = parse_url("serial:///dev/tty:4800")
    assert url == "device:///dev/tty"


def test_parse_url_pass_others():
    url = parse_url("unknown://something/or/other")
    assert url == "unknown://something/or/other"


def test_parse_flags_one_simple_flag():
    flags = parse_flags("foo")
    assert flags["foo"] is True


def test_parse_flags_two_simple_flags():
    flags = parse_flags("foo, yaa")
    assert flags == {"foo": True, "yaa": True}


def test_parse_flags_one_assigned_flag():
    flags = parse_flags("the_answer = 42")
    assert flags == {"the_answer": 42}


def test_parse_flags_two_assigned_flags():
    flags = parse_flags("the_answer = 42, to_the_universe=food")
    assert flags == {"the_answer": 42, "to_the_universe": "food"}


def test_parse_flags_complex_flags():
    flags = parse_flags("nonono, the_answer=42, yesyesyes, the_universe=food")
    assert flags == {
        "nonono": True,
        "yesyesyes": True,
        "the_answer": 42,
        "the_universe": "food",
    }


def test_seconds_to_rate():
    assert seconds_to_rate(0) == 0
    assert seconds_to_rate(0.1) == 0
    assert seconds_to_rate(0.7) == 1
    assert seconds_to_rate(30) == 8
    assert seconds_to_rate(1.0) == 1
    assert seconds_to_rate(1.21) == 2
    assert seconds_to_rate(45) == 8
    assert seconds_to_rate(45.1) == 9
    assert seconds_to_rate(10000) == 15
