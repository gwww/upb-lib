"""
UPB message encode/decode.
"""


import logging
from collections import namedtuple
from functools import reduce

from .const import UpbCommand

LOG = logging.getLogger(__name__)
PIM_ID = 0xFF

Message = namedtuple(
    "Message",
    "link repeater_req length ack_req tx_count tx_seq network_id dest_id src_id msg_id data",
)


class MessageDecode:
    """Message decode and dispatcher."""

    def __init__(self):
        """Initialize a new Message instance."""
        self._handlers = {}

    def add_handler(self, message_type, handler):
        """Manage callbacks for message handlers."""
        upb_command = message_type
        if upb_command not in self._handlers:
            self._handlers[upb_command] = []

        if handler not in self._handlers[upb_command]:
            self._handlers[upb_command].append(handler)

    def call_handlers(self, cmd, message):
        """Call the message/event handlers."""
        for handler in self._handlers.get(cmd, []):
            if isinstance(message, dict):
                handler(**message)
            else:
                handler(message)

    def decode(self, msg) -> Message:
        """
        Decode and return a UPB message

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
        return Message(
            link=(control & 0x8000) != 0,
            repeater_req=(control >> 13) & 3,
            length=(control >> 8) & 31,
            ack_req=(control >> 4) & 7,
            tx_count=(control >> 2) & 3,
            tx_seq=control & 3,
            network_id=msg[2],
            dest_id=msg[3],
            src_id=msg[4],
            msg_id=msg[5],
            data=msg[6:],
        )

    def handle(self, msg):
        """ Decode a UPB message, and invoke appropriate handlers """
        message = self.decode(msg)
        self.call_handlers(message.msg_id, message)


class MessageEncode:
    """Encodes UPB commands."""

    def __init__(self, tx_count):
        """Initialize a new MessageEncode instance."""
        self.tx_count = tx_count

    def _create_control_word(self, link, repeater=0, ack=0):
        """Create a control word in UPB message."""
        ctl = (1 if link else 0) << 15
        ctl = ctl | (repeater << 13)
        ctl = ctl | (ack << 4)
        # Value of 00 corresponds to 1 transmit.
        ctl = ctl | (self.tx_count - 1 << 2)
        ctl = ctl | 0
        return ctl

    def _encode_message(self, ctl, addr, src_id, msg_code, data=""):
        """Encode a message for the PIM, assumes data formatted"""
        ctl = self._create_control_word(addr.is_link) if ctl == -1 else ctl
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

    def activate_link(self, addr, ctl=-1):
        """Activate link"""
        return self._encode_message(ctl, addr, PIM_ID, UpbCommand.ACTIVATE.value)

    def deactivate_link(self, addr, ctl=-1):
        """Activate link"""
        return self._encode_message(ctl, addr, PIM_ID, UpbCommand.DEACTIVATE.value)

    def _encode_common(self, ctl, addr, cmd, level, rate):
        """Goto/fade_start, device or link"""
        rate = int(rate)
        args = bytearray([level])
        if addr.is_device and addr.multi_channel:
            args.append(0xFF if rate == -1 else rate)
            args.append(addr.channel + 1)
        elif rate != -1:
            args.append(rate)

        return self._encode_message(ctl, addr, PIM_ID, cmd, args)

    def goto(self, addr, level, rate, ctl=-1):
        """Goto level, device or link"""
        return self._encode_common(ctl, addr, UpbCommand.GOTO.value, level, rate)

    def fade_start(self, addr, level, rate, ctl=-1):
        """Fade start level, device or link"""
        return self._encode_common(ctl, addr, UpbCommand.FADE_START.value, level, rate)

    def fade_stop(self, addr, ctl=-1):
        """Fade stop, device or link."""
        return self._encode_message(ctl, addr, PIM_ID, UpbCommand.FADE_STOP.value)

    def blink(self, addr, rate, ctl=-1):
        """Blink, device or link."""
        args = bytearray([rate])
        return self._encode_message(ctl, addr, PIM_ID, UpbCommand.BLINK.value, args)

    def report_state(self, addr, ctl=-1):
        """Report state message."""
        return self._encode_message(ctl, addr, PIM_ID, UpbCommand.REPORT_STATE.value)
