from unittest.mock import Mock

import pytest

from upb_lib.util import parse_url


def test_parse_url_valid_tcp():
    (scheme, host, port) = parse_url("tcp://some.host:1234")
    assert scheme == "tcp"
    assert host == "some.host"
    assert port == 1234


def test_parse_url_valid_serial():
    (scheme, host, port) = parse_url("serial:///dev/tty:4800")
    assert scheme == "serial"
    assert host == "/dev/tty"
    assert port == 4800


def test_parse_url_unknown_scheme():
    with pytest.raises(ValueError):
        parse_url("bad_scheme://rest")
