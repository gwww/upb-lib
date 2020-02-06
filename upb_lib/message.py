"""
UPB message encode/decode.
"""


import logging
from collections import namedtuple
from functools import reduce

from .const import PIM_ID, UpbCommand

LOG = logging.getLogger(__name__)

MessageEncode = namedtuple("MessageEncode", ["message", "response_command"])


class MessageDecode:
    """Message decode and dispatcher."""

    def __init__(self):
        """Initialize a new Message instance."""
        self._handlers = {}
        self._last_message = bytearray()
        self._last_sequence = 0

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

        Minimum length is 14 bytes (all the bytes except the '...' bit)
        """
        if len(msg) < 14:
            raise ValueError("UPB message less than 14 characters")

        # Convert message to binary, stripping checksum as PIM checks it
        msg = bytearray.fromhex(msg[:-2])
        if self._repeated_message(msg):
            LOG.debug("Repeated message!!!")
            return

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

        self.index = "{}_{}".format(self.network_id, self.src_id)

        for handler in self._handlers.get(self.msg_id, []):
            handler(self)

        # LOG.debug( "Lnk %d Repeater %x Len %d Ack %x Transmit %d Seq %d",
        #           self.link, self.repeater_request,
        #           self.length, self.ack_request,
        #           self.transmit_count, self.transmit_sequence )
        # LOG.debug( "NID %d Dst %d Src %d Cmd 0x%x", self.network_id,
        #           self.dest_id, self.src_id, self.msg_id)

    def _repeated_message(self, msg):
        current_message = msg.copy()
        current_sequence = current_message[1] & 0b00000011

        if current_sequence <= self._last_sequence:
            self._last_sequence = current_sequence
            self._last_message = current_message
            return False

        self._last_sequence = current_sequence

        # Clear sequence field
        current_message[1] = current_message[1] & 0b11111100
        if current_message == self._last_message:
            return True

        self._last_message = current_message
        return False


def get_control_word(link, repeater=0, ack=0, tx_cnt=0, tx_seq=0):
    control = (1 if link else 0) << 15
    control = control | (repeater << 13)
    control = control | (ack << 4)
    control = control | (tx_cnt << 2)
    control = control | tx_seq
    return control


def encode_message(control, network_id, dest_id, src_id, msg_code, data=""):
    """Encode a message for the PIM, assumes data formatted"""
    length = 7 + len(data)
    control = control | (length << 8)
    msg = bytearray(length)
    msg[0:2] = control.to_bytes(2, byteorder="big")
    msg[2] = network_id
    msg[3] = dest_id
    msg[4] = src_id
    msg[5] = msg_code
    if data:
        msg[6 : len(data) + 6] = data

    # Checksum
    msg[-1] = (256 - reduce(lambda x, y: x + y, msg)) % 256

    return msg.hex().upper()


def _ctl(ctl, link=False):
    if ctl == -1:
        return get_control_word(link)
    return ctl


def encode_activate_link(network_id, dest_id, ctl=-1):
    """Activate link"""
    return encode_message(
        _ctl(ctl, True), network_id, dest_id, PIM_ID, UpbCommand.ACTIVATE.value
    )


def encode_deactivate_link(network_id, dest_id, ctl=-1):
    """Activate link"""
    return encode_message(
        _ctl(ctl, True), network_id, dest_id, PIM_ID, UpbCommand.DEACTIVATE.value
    )


def _encode_common(cmd, link, network_id, dest_id, channel, level, rate, ctl):
    """Goto/fade_start, light or link"""
    rate = int(rate)
    if ctl == -1:
        ctl = get_control_word(link)
    args = bytearray([level])
    if not link and channel > 0:
        args.append(0xFF if rate == -1 else rate)
        args.append(channel)
    elif rate != -1:
        args.append(rate)

    return encode_message(ctl, network_id, dest_id, PIM_ID, cmd, args)


def encode_goto(link, network_id, dest_id, channel, level, rate, ctl=-1):
    """Goto level, light or link"""
    return _encode_common(
        UpbCommand.GOTO.value, link, network_id, dest_id, channel, level, rate, ctl
    )


def encode_fade_start(link, network_id, dest_id, channel, level, rate, ctl=-1):
    """Fade start level, light or link"""
    return _encode_common(
        UpbCommand.FADE_START.value,
        link,
        network_id,
        dest_id,
        channel,
        level,
        rate,
        ctl,
    )


def encode_fade_stop(link, network_id, dest_id, channel, ctl=-1):
    """Fade stop, light or link."""
    if ctl == -1:
        ctl = get_control_word(link)
    return encode_message(ctl, network_id, dest_id, PIM_ID, UpbCommand.FADE_STOP.value)


def encode_blink(link, network_id, dest_id, channel, rate, ctl=-1):
    """Blink, light or link."""
    if ctl == -1:
        ctl = get_control_word(link)
    args = bytearray([rate])
    return encode_message(
        ctl, network_id, dest_id, PIM_ID, UpbCommand.BLINK.value, args
    )


def encode_report_state(network_id, dest_id, ctl=-1):
    return encode_message(
        _ctl(ctl), network_id, dest_id, PIM_ID, UpbCommand.REPORT_STATE.value
    )
