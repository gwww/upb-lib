import pytest

from upb_lib.devices import UpbAddr
from upb_lib.message import Message, MessageEncode, decode


def test_create_control_word_all_zeros():
    assert f"{MessageEncode(1)._create_control_word(False, 0, 0):04X}" == "0000"


def test_create_control_word_all_ones():
    assert f"{MessageEncode(4)._create_control_word(True, 3, 7):04X}" == "E07C"


def test_encode_message():
    addr = UpbAddr(194, 9, 0)
    assert (
        MessageEncode(0)._encode_message(0x8904, addr, 9, 0x20, bytearray([0xFF, 0xFF]))
        == "8904C2090920FFFF81"  # noqa
    )


def test_decode_status_update():
    reply_from, msg = decode("0800C2FF09863276")
    assert reply_from == b"\xc2\x09"
    assert msg == Message(
        link=False,
        repeater_req=0,
        length=8,
        ack_req=0,
        tx_count=0,
        tx_seq=0,
        network_id=194,
        dest_id=255,
        src_id=9,
        msg_id=134,
        data=bytearray(b"\x32"),
    )
    assert msg.data[0] == 50


def test_decode_too_short():
    with pytest.raises(ValueError):
        decode("0800C2FF09")


def test_decode_bad_length():
    with pytest.raises(ValueError):
        decode("0800C2FF091111")


def test_decode_bad_checksum():
    with pytest.raises(ValueError):
        decode("0800C2FF09863275")
