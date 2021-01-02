from unittest.mock import Mock, call

from upb_lib.proto import Connection


def test_receive_single_packet_and_pass_to_handler():
    mock_gotdata = Mock()
    connection = Connection(None, 0, None, None, mock_gotdata, 0)
    connection.data_received("PU0800C2FF068600AB\r".encode())
    mock_gotdata.assert_called_once_with(bytearray(b"\x08\x00\xc2\xff\x06\x86\x00"))


def test_receive_multiple_packets():
    mock_gotdata = Mock()
    connection = Connection(None, 0, None, None, mock_gotdata, 0)
    connection.data_received("PU0800C2FF068600AB\rPU0800C2FF068600AB\r".encode())
    mock_gotdata.assert_has_calls(
        [
            call(bytearray(b"\x08\x00\xc2\xff\x06\x86\x00")),
            call(bytearray(b"\x08\x00\xc2\xff\x06\x86\x00")),
        ]
    )


def test_received_full_packet_and_partial_packet():
    mock_gotdata = Mock()
    connection = Connection(None, 0, None, None, mock_gotdata, 0)
    connection.data_received("PU8800C2FF068600AB\rPU0".encode())
    mock_gotdata.assert_called_once_with(bytearray(b"\x88\x00\xc2\xff\x06\x86\x00"))

    connection.data_received("800C2FF068600AB\r".encode())
    mock_gotdata.assert_has_calls(
        [
            call(bytearray(b"\x88\x00\xc2\xff\x06\x86\x00")),
            call(bytearray(b"\x08\x00\xc2\xff\x06\x86\x00")),
        ]
    )
