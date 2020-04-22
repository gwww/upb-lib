"""
UPB message encode/decode.
"""


import logging
from collections import namedtuple
from functools import reduce

from .const import UpbCommand

LOG = logging.getLogger(__name__)
PIM_ID = 0xFF

MessageEncode = namedtuple("MessageEncode", ["message", "response_command"])


class MessageDecode:
    """Message decode and dispatcher."""

    def __init__(self):
        """Initialize a new Message instance."""
        self._handlers = {}

    def add_handler(self, message_type, handler):
        """Manage callbacks for message handlers."""
        upb_command = message_type.value
        if upb_command not in self._handlers:
            self._handlers[upb_command] = []

        if handler not in self._handlers[upb_command]:
            self._handlers[upb_command].append(handler)

    def decode(self, msg):
        """
        Decode an UPB message

        ASCII Message format: PPCCCCNNDDSSMM...KK

        PP - PIM command (PA, PB, PU, etc)
        CCCC - control word, includes length
        NN - Network ID
        DD - Destination ID
        SS - Source ID
        MM - UPB Message type
        ... - contents of UPB message, vary by type
        KK - checksum
        """
        # PIM command and checksum already stripped off of msg at this point
        if len(msg) < 6:
            raise ValueError("UPB message less than 12 characters")

        control = int.from_bytes(msg[0:2], byteorder="big")
        self.link = (control & 0x8000) != 0
        self.repeater_request = (control >> 13) & 3
        self.length = (control >> 8) & 31
        self.ack_request = (control >> 4) & 7
        self.transmit_count = (control >> 2) & 3
        self.transmit_sequence = control & 3

        self.network_id = msg[2]
        self.dest_id = msg[3]
        self.src_id = msg[4]
        self.msg_id = msg[5]
        self.data = msg[6:]

        for handler in self._handlers.get(self.msg_id, []):
            handler(self)

        # LOG.debug( "NID %d Dst %d Src %d Cmd 0x%x", self.network_id,
        #           self.dest_id, self.src_id, self.msg_id)


def create_control_word(link, repeater=0, ack=0, tx_cnt=0, tx_seq=0):
    ctl = (1 if link else 0) << 15
    ctl = ctl | (repeater << 13)
    ctl = ctl | (ack << 4)
    ctl = ctl | (tx_cnt << 2)
    ctl = ctl | tx_seq
    return ctl


def encode_message(ctl, addr, src_id, msg_code, data=""):
    """Encode a message for the PIM, assumes data formatted"""
    ctl = create_control_word(addr.is_link) if ctl == -1 else ctl
    length = 7 + len(data)
    ctl = ctl | (length << 8)
    msg = bytearray(length)
    msg[0:2] = ctl.to_bytes(2, byteorder="big")
    msg[2] = addr.network_id
    msg[3] = addr.upb_id
    msg[4] = src_id
    msg[5] = msg_code
    if data:
        msg[6 : len(data) + 6] = data
    msg[-1] = (256 - reduce(lambda x, y: x + y, msg)) % 256  # Checksum
    return msg.hex().upper()


def encode_activate_link(addr, ctl=-1):
    """Activate link"""
    return encode_message(ctl, addr, PIM_ID, UpbCommand.ACTIVATE.value)


def encode_deactivate_link(addr, ctl=-1):
    """Activate link"""
    return encode_message(ctl, addr, PIM_ID, UpbCommand.DEACTIVATE.value)


def _encode_common(ctl, addr, cmd, level, rate):
    """Goto/fade_start, device or link"""
    rate = int(rate)
    args = bytearray([level])
    if addr.is_device and addr.multi_channel:
        args.append(0xFF if rate == -1 else rate)
        args.append(addr.channel + 1)
    elif rate != -1:
        args.append(rate)

    return encode_message(ctl, addr, PIM_ID, cmd, args)


def encode_goto(addr, level, rate, ctl=-1):
    """Goto level, device or link"""
    return _encode_common(ctl, addr, UpbCommand.GOTO.value, level, rate)


def encode_fade_start(addr, level, rate, ctl=-1):
    """Fade start level, device or link"""
    return _encode_common(ctl, addr, UpbCommand.FADE_START.value, level, rate)


def encode_fade_stop(addr, ctl=-1):
    """Fade stop, device or link."""
    return encode_message(ctl, addr, PIM_ID, UpbCommand.FADE_STOP.value)


def encode_blink(addr, rate, ctl=-1):
    """Blink, device or link."""
    args = bytearray([rate])
    return encode_message(ctl, addr, PIM_ID, UpbCommand.BLINK.value, args)


def encode_report_state(addr, ctl=-1):
    return encode_message(ctl, addr, PIM_ID, UpbCommand.REPORT_STATE.value)
