"""Definition of UPB devices."""

import logging

from .const import MINIMUM_BLINK_RATE, UpbCommand
from .elements import Addr, Element, Elements
from .util import check_dim_params

LOG = logging.getLogger(__name__)


class UpbAddr(Addr):
    """Representation of a UPB device address."""

    def __init__(
        self, network_id: int, upb_id: int, channel: int, multi_channel: bool = False
    ):
        super().__init__(network_id, upb_id)
        self._channel = channel
        self._multi_channel = multi_channel
        self._index = f"{self.network_id}_{self.upb_id}_{self.channel}"

    @property
    def channel(self):
        """Address channel."""
        return self._channel

    @property
    def multi_channel(self):
        """Is address part of multi-channel device."""
        return self._multi_channel

    @staticmethod
    def parse(str_form: str):
        """Parses an index string into a UpbAddr instance."""
        parts = str_form.split("_")
        return UpbAddr(int(parts[0]), int(parts[1]), int(parts[2]))


class UpbDevice(Element[UpbAddr]):
    """Class representing a UPB device."""

    def __init__(self, addr: UpbAddr, pim):
        super().__init__(addr, pim)
        self.status: int | None = None
        self.version: str | None = None
        self.manufacturer: str | None = None
        self.product: str | None = None
        self.kind: str | None = None
        self.dimmable: bool | None = None

    def _level(self, brightness, rate, encode_fn):
        if not self.dimmable and brightness > 0:
            brightness = 100
        brightness, rate = check_dim_params(
            brightness, rate, self._pim.flags.get("use_raw_rate")
        )

        self._pim.send(encode_fn(self._addr, brightness, rate))
        if self._pim.flags.get("report_state"):
            self.update_status()
        self.setattr("status", brightness)

    @property
    def addr(self):
        """Get the device address."""
        return self._addr

    def turn_on(self, brightness=100, rate=-1):
        """(Helper) Set device to specified level"""
        self._level(brightness, rate, self._pim.encoder.goto)

    def turn_off(self, rate=-1):
        """(Helper) Turn device off."""
        self._level(0, rate, self._pim.encoder.goto)

    def fade_start(self, brightness, rate=-1):
        """(Helper) Start fading a device."""
        self._level(brightness, rate, self._pim.encoder.fade_start)

    def fade_stop(self):
        """(Helper) Stop fading a device."""
        self._pim.send(self._pim.encoder.fade_stop(self._addr))
        self._pim.send(self._pim.encoder.report_state(self._addr), self.response_addr)

    def blink(self, rate=-1):
        """(Helper) Blink a device."""
        if rate < MINIMUM_BLINK_RATE and not self._pim.flags.get(
            "unlimited_blink_rate"
        ):
            rate = MINIMUM_BLINK_RATE  # Force 1/3 of second blink rate
        self._pim.send(self._pim.encoder.blink(self._addr, rate))
        if self._pim.flags.get("report_state"):
            self.update_status()
        self.setattr("status", 100)

    def update_status(self):
        """(Helper) Get status of a device."""
        self._pim.send(self._pim.encoder.report_state(self._addr), self.response_addr)


class UpbDevices(Elements[UpbDevice]):
    """Handling for multiple devices."""

    def __init__(self, pim):
        super().__init__(pim)
        pim.add_handler(
            UpbCommand.DEVICE_STATE_REPORT.value, self._device_state_report_handler
        )
        pim.add_handler(
            UpbCommand.REGISTER_VALUES_REPORT.value,
            self._register_values_report_handler,
        )
        pim.add_handler(UpbCommand.GOTO.value, self._goto_handler)

    def sync(self):
        """Sync handler for devices."""
        for device_id in self.elements:  # pylint: disable=consider-using-dict-items
            device = self.elements[device_id]
            if device.addr.channel > 0:
                continue
            device.update_status()

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
            LOG.debug("Device status report: '%s' level %d", device.name, device.status)

    def _goto_handler(self, msg):
        if msg.link:
            return
        channel = msg.data[2] - 1 if len(msg.data) > 2 else 0
        index = UpbAddr(msg.network_id, msg.dest_id, channel).index
        device = self.pim.devices.elements.get(index)
        if device:
            level = msg.data[0] if len(msg.data) > 0 else -1
            device.setattr("status", level)
            LOG.debug("Goto level report: '%s' level %d", device.name, device.status)

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
            LOG.debug("Network name '%s'", network_name)
        elif start_register == 32:
            room_name = data[1:].decode("UTF-8").strip()
            LOG.debug("Room name '%s'", room_name)
        elif start_register == 48:
            device_name = data[1:].decode("UTF-8").strip()
            LOG.debug("Device name '%s'", device_name)
