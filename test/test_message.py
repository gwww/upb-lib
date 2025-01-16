from upb_lib.devices import UpbAddr
from upb_lib.message import MessageEncode


def test_create_control_word_all_zeros():
    assert "{:04X}".format(MessageEncode(1)._create_control_word(False, 0, 0)) == "0000"


def test_create_control_word_all_ones():
    assert "{:04X}".format(MessageEncode(4)._create_control_word(True, 3, 7)) == "E07C"


def test_encode_message():
    addr = UpbAddr(194, 9, 0)
    assert (
        MessageEncode(0)._encode_message(0x8904, addr, 9, 0x20, bytearray([0xFF, 0xFF]))
        == "8904C2090920FFFF81"  # noqa
    )
