"""
UPB message encode/decode.
"""


from base64 import b16encode
from collections import namedtuple
from functools import reduce
import logging
import re

from .const import UpbCommand, Max
from .util import light_id

LOG = logging.getLogger(__name__)

MessageEncode = namedtuple("MessageEncode", ["message", "response_command"])


class MessageDecode:
    """Message decode and dispatcher."""

    def __init__(self):
        """Initialize a new Message instance."""
        self._handlers = {}
        self._last_message = bytearray()

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

        control = int.from_bytes(msg[0:2], byteorder='big')
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

        # LOG.debug( "Lnk %d Repeater %x Len %d Ack %x Transmit %d Seq %d",
        #           self.link, self.repeater_request,
        #           self.length, self.ack_request,
        #           self.transmit_count, self.transmit_sequence )
        # LOG.debug( "NID %d Dst %d Src %d Cmd 0x%x", self.network_id,
        #           self.dest_id, self.src_id, self.msg_id)

        try:
            decoder_name = "_decode_{}".format(UpbCommand(self.msg_id).name.lower())
            decoder = getattr(self, decoder_name)
        except:
            LOG.warn("Unknown/upsupported UPB message type 0x{:02x}".
                     format(self.msg_id))
            return

        decoded_msg = decoder()
        for handler in self._handlers.get(self.msg_id, []):
            handler(**decoded_msg)

    def _repeated_message(self, msg):
        current_message = msg.copy()
        current_message[1] = current_message[1] & 0xfc # Clear sequence field
        if current_message == self._last_message:
            return True
        self._last_message = current_message
        return False

    def _light_id(self):
        return light_id(self.network_id, self.src_id, 0)

    def _decode_activate(self):
        return {'link_id': self.dest_id}

    def _decode_deactivate(self):
        return {'link_id': self.dest_id}

    def _decode_device_state_report(self):
        return {'light_id': self._light_id(), 'dim_level': self.data[0]}

    def _decode_register_values_report(self):
        return {'data': self.data}



    def _am_decode(self, msg):
        """AM: Alarm memory by area report."""
        return {"alarm_memory": [x for x in msg[4 : 4 + Max.AREAS.value]]}

    def _as_decode(self, msg):
        """AS: Arming status report."""
        return {
            "armed_statuses": [x for x in msg[4:12]],
            "arm_up_states": [x for x in msg[12:20]],
            "alarm_states": [x for x in msg[20:28]],
        }

    def _az_decode(self, msg):
        """AZ: Alarm by zone report."""
        return {"alarm_status": [x for x in msg[4 : 4 + Max.ZONES.value]]}

    def _cr_one_custom_value_decode(self, index, part):
        value = int(part[0:5])
        value_format = int(part[5])
        if value_format == 2:
            value = ((value >> 8) & 0xFF, value & 0xFF)
        return {"index": index, "value": value, "value_format": value_format}

    def _cr_decode(self, msg):
        """CR: Custom values"""
        if int(msg[4:6]) > 0:
            index = int(msg[4:6]) - 1
            return {"values": [self._cr_one_custom_value_decode(index, msg[6:12])]}
        else:
            part = 6
            ret = []
            for i in range(Max.SETTINGS.value):
                ret.append(self._cr_one_custom_value_decode(i, msg[part : part + 6]))
                part += 6
            return {"values": ret}

    def _cc_decode(self, msg):
        """CC: Output status for single output."""
        return {"output": int(msg[4:7]) - 1, "output_status": msg[7] == "1"}

    def _cs_decode(self, msg):
        """CS: Output status for all outputs."""
        output_status = [x == "1" for x in msg[4 : 4 + Max.OUTPUTS.value]]
        return {"output_status": output_status}

    def _cv_decode(self, msg):
        """CV: Counter value."""
        return {"counter": int(msg[4:6]) - 1, "value": int(msg[6:11])}

    def _ee_decode(self, msg):
        """EE: Entry/exit timer report."""
        return {
            "area": int(msg[4:5]) - 1,
            "is_exit": msg[5:6] == "0",
            "timer1": int(msg[6:9]),
            "timer2": int(msg[9:12]),
            "armed_status": msg[12:13],
        }

    def _ic_decode(self, msg):
        """IC: Send Valid Or Invalid User Code Format."""
        code = msg[4:16]
        if re.match(r"(0\d){6}", code):
            code = re.sub(r"0(\d)", r"\1", code)
        return {
            "code": code,
            "user": int(msg[16:19]) - 1,
            "keypad": int(msg[19:21]) - 1,
        }

    def _ie_decode(self, _msg):
        """IE: Installer mode exited."""
        return {}

    def _ka_decode(self, msg):
        """KA: Keypad areas for all keypads."""
        return {"keypad_areas": [ord(x) - 0x31 for x in msg[4 : 4 + Max.KEYPADS.value]]}

    def _kc_decode(self, msg):
        """KC: Keypad key change."""
        return {"keypad": int(msg[4:6]) - 1, "key": int(msg[6:8])}

    def _lw_decode(self, msg):
        """LW: temperatures from all keypads and zones 1-16."""
        keypad_temps = []
        zone_temps = []
        for i in range(16):
            keypad_temps.append(int(msg[4 + 3 * i : 7 + 3 * i]) - 40)
            zone_temps.append(int(msg[52 + 3 * i : 55 + 3 * i]) - 60)
        return {"keypad_temps": keypad_temps, "zone_temps": zone_temps}

    def _ps_decode(self, msg):
        """PS: PLC (lighting) status."""
        return {
            "bank": ord(msg[4]) - 0x30,
            "statuses": [ord(x) - 0x30 for x in msg[5:69]],
        }

    def _rp_decode(self, msg):
        """RP: Remote programming status."""
        return {"remote_programming_status": int(msg[4:6])}

    def _sd_decode(self, msg):
        """SD: Description text."""
        desc_ch1 = msg[9]
        show_on_keypad = ord(desc_ch1) >= 0x80
        if show_on_keypad:
            desc_ch1 = chr(ord(desc_ch1) & 0x7F)
        return {
            "desc_type": int(msg[4:6]),
            "unit": int(msg[6:9]) - 1,
            "desc": (desc_ch1 + msg[10:25]).rstrip(),
            "show_on_keypad": show_on_keypad,
        }

    def _ss_decode(self, msg):
        """SS: System status."""
        return {"system_trouble_status": msg[4:-2]}

    def _st_decode(self, msg):
        """ST: Temperature update."""
        group = int(msg[4:5])
        temperature = int(msg[7:10])
        if group == 0:
            temperature -= 60
        elif group == 1:
            temperature -= 40
        return {"group": group, "device": int(msg[5:7]) - 1, "temperature": temperature}

    def _tc_decode(self, msg):
        """TC: Task change."""
        return {"task": int(msg[4:7]) - 1}

    def _tr_decode(self, msg):
        """TR: Thermostat data response."""
        return {
            "thermostat_index": int(msg[4:6]) - 1,
            "mode": int(msg[6]),
            "hold": msg[7] == "1",
            "fan": int(msg[8]),
            "current_temp": int(msg[9:11]),
            "heat_setpoint": int(msg[11:13]),
            "cool_setpoint": int(msg[13:15]),
            "humidity": int(msg[15:17]),
        }

    def _xk_decode(self, msg):
        """XK: Ethernet Test."""
        return {"real_time_clock": msg[4:20]}

    def _zb_decode(self, msg):
        """ZB: Zone bypass report."""
        return {"zone_number": int(msg[4:7]) - 1, "zone_bypassed": msg[7] == "1"}

    def _zc_decode(self, msg):
        """ZC: Zone Change."""
        status = _status_decode(int(msg[7:8], 16))
        return {"zone_number": int(msg[4:7]) - 1, "zone_status": status}

    def _zd_decode(self, msg):
        """ZD: Zone definitions."""
        zone_definitions = [ord(x) - 0x30 for x in msg[4 : 4 + Max.ZONES.value]]
        return {"zone_definitions": zone_definitions}

    def _zp_decode(self, msg):
        """ZP: Zone partitions."""
        zone_partitions = [ord(x) - 0x31 for x in msg[4 : 4 + Max.ZONES.value]]
        return {"zone_partitions": zone_partitions}

    def _zs_decode(self, msg):
        """ZS: Zone statuses."""
        status = [_status_decode(int(x, 16)) for x in msg[4 : 4 + Max.ZONES.value]]
        return {"zone_statuses": status}

    def _zv_decode(self, msg):
        """ZV: Zone voltage."""
        return {"zone_number": int(msg[4:7]) - 1, "zone_voltage": int(msg[7:10]) / 10}

    def _unknown_decode(self, msg):
        """Generic handler called when no specific handler exists"""
        return {"msg_code": msg[2:4], "data": msg[4:-2]}

    def timeout_handler(self, msg_code):
        """Called directly when a timeout happens when response not received"""
        for handler in self._handlers.get("timeout", []):
            handler({"msg_code": msg_code})


def get_pim_command(line):
    """Return the 2 character command in the message."""
    if len(line) < 2:
        return ""
    return line[:2]


def encode_control_word(link, repeater, ack, tx_cnt, tx_seq):
    control = (1 if link else 0) << 15
    control = control | (repeater << 13)
    control = control | (ack << 4)
    control = control | (tx_cnt << 2)
    control = control | tx_seq
    return control


def encode_message(control, network_id, dest_id, src_id, msg_code, data=''):
    """Encode a message for the PIM, assumes data formatted"""
    length = 7 + len(data)
    control = control | (length << 8)
    msg = bytearray(length)
    msg[0:2] = control.to_bytes(2, byteorder='big')
    msg[2] = network_id
    msg[3] = dest_id
    msg[4] = src_id
    msg[5] = msg_code
    if data:
        msg[6:len(data)+6] = data

    # Checksum
    msg[-1] = 256 - reduce(lambda x, y: x + y, msg) % 256

    return msg.hex().upper()
