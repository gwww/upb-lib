"""Definition of UPB devices."""

import logging

from .const import UpbCommand
from .elements import Addr, Element, Elements
from .message import (
    encode_blink,
    encode_fade_start,
    encode_fade_stop,
    encode_goto,
    encode_report_state,
)
from .util import seconds_to_rate

LOG = logging.getLogger(__name__)


class UpbAddr(Addr):
    def __init__(self, network_id, upb_id, channel, multi_channel=False):
        super().__init__(network_id, upb_id)
        self._channel = channel
        self._multi_channel = multi_channel
        self._index = f"{self.network_id}_{self.upb_id}_{self.channel}"

    @property
    def channel(self):
        return self._channel

    @property
    def multi_channel(self):
        return self._multi_channel


class UpbDevice(Element):
    """Class representing a UPB device."""

    def __init__(self, addr, pim):
        super().__init__(addr.index, pim)
        self._addr = addr
        self.status = None
        self.version = None
        self.product = None
        self.kind = None
        self.dimmable = None

    def _level(self, brightness, rate):
        if rate >= 0 and not self._pim.flags.get("use_raw_rate"):
            rate = seconds_to_rate(rate)

        if rate > 255:
            rate = 255

        self._pim.send(encode_goto(self._addr, brightness, rate), False)
        self.setattr("status", brightness)

    def turn_on(self, brightness=100, rate=-1):
        """(Helper) Set device to specified level"""
        if not self.dimmable or brightness > 100:
            brightness = 100
        self._level(brightness, rate)

    def turn_off(self, rate=-1):
        """(Helper) Turn device off."""
        self._level(0, rate)

    def fade_start(self, brightness, rate=-1):
        """(Helper) Start fading a device."""
        self._pim.send(encode_fade_start(self._addr, brightness, rate), False)
        self.setattr("status", brightness)

    def fade_stop(self):
        """(Helper) Stop fading a device."""
        self._pim.send(encode_fade_stop(self._addr), False)
        self._pim.send(encode_report_state(self._addr))

    def blink(self, rate=-1):
        """(Helper) Blink a device."""
        if rate < 30 and not self._pim.flags.get("unlimited_blink_rate"):
            rate = 30
        self._pim.send(encode_blink(self._addr, rate), False)
        self.setattr("status", 100)

    def update_status(self):
        """(Helper) Get status of a device."""
        self._pim.send(encode_report_state(self._addr))


class UpbDevices(Elements):
    """Handling for multiple devices."""

    def __init__(self, pim):
        super().__init__(pim)
        pim.add_handler(
            UpbCommand.DEVICE_STATE_REPORT, self._device_state_report_handler
        )
        pim.add_handler(
            UpbCommand.REGISTER_VALUES_REPORT, self._register_values_report_handler
        )
        pim.add_handler(UpbCommand.GOTO, self._goto_handler)

    def sync(self):
        for device_id in self.elements:
            device = self.elements[device_id]
            if device._addr.channel > 0:
                continue
            self.pim.send(encode_report_state(device._addr))

    def _device_state_report_handler(self, msg):
        status_length = len(msg.data)
        for i in range(0, 100):
            if i >= status_length:
                break

            index = UpbAddr(msg.network_id, msg.src_id, i).index
            device = self.pim.devices.elements.get(index)
            if not device:
                break

            level = msg.data[i]
            device.setattr("status", level)
            LOG.debug("(DSR) Device %s level is %d", device.name, device.status)

    def _goto_handler(self, msg):
        if msg.link:
            return
        channel = msg.data[2] if len(msg.data) > 2 else 0
        index = UpbAddr(msg.network_id, msg.dest_id, channel).index
        device = self.pim.devices.elements.get(index)
        if device:
            level = msg.data[0]
            device.setattr("status", level)
            LOG.debug(
                f"(GOTO) Device {device.name}/{device.index} level is {device.status}"
            )

    def _register_values_report_handler(self, msg):
        data = msg.data
        if len(data) != 17:
            LOG.debug("Parse register values only accepts 16 registers")
            return
        start_register = data[0]
        if start_register == 0:
            pass
        elif start_register == 16:
            network_name = data[1:].decode("UTF-8").strip()
            LOG.debug("Network name '{}'".format(network_name))
        elif start_register == 32:
            room_name = data[1:].decode("UTF-8").strip()
            LOG.debug("Room name '{}'".format(room_name))
        elif start_register == 48:
            device_name = data[1:].decode("UTF-8").strip()
            LOG.debug("Device name '{}'".format(device_name))