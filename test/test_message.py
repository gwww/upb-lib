import pytest
from unittest.mock import Mock

from upb_lib.message import (
    encode_control_word,
    encode_message,
)

def test_encode_control_word_all_zeros():
    assert "{:04X}".format(encode_control_word(False, 0, 0, 0, 0)) == "0000"


def test_encode_control_word_all_ones():
    assert "{:04X}".format(encode_control_word(True, 3, 7, 3, 3)) == "E07F"


def test_encode_message():
    assert encode_message(0x8904, 194, 9, 9, 0x20, 
                bytearray([0xff, 0xff])) == "8904C2090920FFFF81"

# def test_decode_raises_value_error_on_bad_message():
#     decoder = MessageDecode()
#     with pytest.raises(ValueError):
#         decoder.decode("a really really bad message")


# def test_decode_calls_unknown_handler_on_bad_command_or_not_implemented():
#     mock_unknown_handler = Mock()
#     decoder = MessageDecode()
#     decoder.add_handler("unknown", mock_unknown_handler)
#     decoder.decode("08XXtest28")
#     mock_unknown_handler.assert_called_once_with(msg_code="XX", data="test")


# def test_decode_raises_value_error_on_length_too_long():
#     decoder = MessageDecode()
#     with pytest.raises(ValueError) as excinfo:
#         decoder.decode("42CV01000990030")
#     assert str(excinfo.value) == "PIM message length incorrect"


# def test_decode_raises_value_error_on_length_too_short():
#     decoder = MessageDecode()
#     with pytest.raises(ValueError) as excinfo:
#         decoder.decode("02CV01000990030")
#     assert str(excinfo.value) == "PIM message length incorrect"


# def test_decode_raises_value_error_on_bad_checksum():
#     decoder = MessageDecode()
#     with pytest.raises(ValueError) as excinfo:
#         decoder.decode("0DCV01000990042")
#     assert str(excinfo.value) == "PIM message checksum invalid"


# def test_encode_message_with_a_variable():
#     assert ps_encode(1) == ("07ps100", "PS")
