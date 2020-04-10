from upb_lib.message import encode_message, create_control_word
from upb_lib.devices import UpbAddr


def test_create_control_word_all_zeros():
    assert "{:04X}".format(create_control_word(False, 0, 0, 0, 0)) == "0000"


def test_create_control_word_all_ones():
    assert "{:04X}".format(create_control_word(True, 3, 7, 3, 3)) == "E07F"


def test_encode_message():
    addr = UpbAddr(194, 9, 0)
    assert (
        encode_message(0x8904, addr, 9, 0x20, bytearray([0xFF, 0xFF]))
        == "8904C2090920FFFF81"  # noqa
    )
