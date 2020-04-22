"""Definition of UPB devices."""

import logging

from .const import MINIMUM_BLINK_RATE, UpbCommand
from .elements import Addr, Element, Elements
from .message import (
    encode_blink,
    encode_fade_start,
    encode_fade_stop,
    encode_goto,
    encode_report_state,
)
from .util import check_dim_params

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
        self.manufacturer = None
        self.product = None
        self.kind = None
        self.dimmable = None

    def _level(self, brightness, rate, encode_fn):
        if not self.dimmable and brightness > 0:
            brightness = 100
        brightness, rate = check_dim_params(
            brightness, rate, self._pim.flags.get("use_raw_rate")
        )

        self._pim.send(encode_fn(self._addr, brightness, rate), False)
        if self._pim.flags.get("report_state"):
            self._pim.send(encode_report_state(self._addr))
        self.setattr("status", brightness)

    def turn_on(self, brightness=100, rate=-1):
        """(Helper) Set device to specified level"""
        self._level(brightness, rate, encode_goto)

    def turn_off(self, rate=-1):
        """(Helper) Turn device off."""
        self._level(0, rate, encode_goto)

    def fade_start(self, brightness, rate=-1):
        """(Helper) Start fading a device."""
        self._level(brightness, rate, encode_fade_start)

    def fade_stop(self):
        """(Helper) Stop fading a device."""
        self._pim.send(encode_fade_stop(self._addr), False)
        self._pim.send(encode_report_state(self._addr))

    def blink(self, rate=-1):
        """(Helper) Blink a device."""
        if rate < MINIMUM_BLINK_RATE and not self._pim.flags.get(
            "unlimited_blink_rate"
        ):
            rate = MINIMUM_BLINK_RATE  # Force 1/3 of second blink rate
        self._pim.send(encode_blink(self._addr, rate), False)
        if self._pim.flags.get("report_state"):
            self._pim.send(encode_report_state(self._addr))
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
        # TODO: is the next line correct for multi-channel devices?
        channel = msg.data[2] - 1 if len(msg.data) > 2 else 0
        index = UpbAddr(msg.network_id, msg.dest_id, channel).index
        device = self.pim.devices.elements.get(index)
        if device:
            level = msg.data[0] if len(msg.data) else -1
            device.setattr("status", level)
            LOG.debug(
                f"(GOTO) Device {device.name}/{device.index} level {device.status}"
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
