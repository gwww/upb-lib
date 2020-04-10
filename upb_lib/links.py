"""Definition of an link (scene)"""
import logging
from collections import namedtuple
from time import time

from .const import UpbCommand
from .elements import Addr, Element, Elements
from .message import (
    encode_activate_link,
    encode_blink,
    encode_deactivate_link,
    encode_fade_start,
    encode_fade_stop,
    encode_goto,
)
from .util import check_dim_params, rate_to_seconds

LOG = logging.getLogger(__name__)


DeviceLink = namedtuple("DeviceLink", "device_id, device_level")


class LinkAddr(Addr):
    def __init__(self, network_id, upb_id):
        super().__init__(network_id, upb_id, True)
        self._index = f"{self.network_id}_{self.upb_id}"


class Link(Element):
    """Class representing a UPB Link."""

    def __init__(self, addr, pim):
        super().__init__(addr.index, pim)
        self.devices = []
        self._addr = addr
        self.network_id = addr.network_id
        self.link_id = addr.upb_id
        self.last_change = None

    def add_device(self, device_link):
        self.devices.append(device_link)

    def activate(self):
        """(Helper) Activate link"""
        self._pim.send(encode_activate_link(self._addr), False)
        self.update_device_levels(UpbCommand.ACTIVATE)

    def deactivate(self):
        """(Helper) Deactivate link"""
        self._pim.send(encode_deactivate_link(self._addr), False)
        self.update_device_levels(UpbCommand.DEACTIVATE)

    def goto(self, brightness, rate=-1):
        """(Helper) Goto level"""
        saved_rate = rate
        brightness, rate = check_dim_params(
            brightness, rate, self._pim.flags.get("use_raw_rate")
        )
        self._pim.send(encode_goto(self._addr, brightness, rate), False)
        self.update_device_levels(UpbCommand.GOTO, brightness, saved_rate)

    def fade_start(self, brightness, rate=-1):
        """(Helper) Start fading a link."""
        saved_rate = rate
        brightness, rate = check_dim_params(
            brightness, rate, self._pim.flags.get("use_raw_rate")
        )
        self._pim.send(encode_fade_start(self._addr, brightness, rate), False)
        self.update_device_levels(UpbCommand.FADE_START, brightness, saved_rate)

    def fade_stop(self):
        """(Helper) Stop fading a link."""
        self._pim.send(encode_fade_stop(self._addr), False)
        for device_link in self.devices:
            device = self._pim.devices.elements.get(device_link.device_id)
            if device:
                device.update_status()

    def blink(self, rate=-1):
        """(Helper) Blink a link."""
        self._pim.send(encode_blink(self._addr, rate), False)
        self.update_device_levels(UpbCommand.BLINK, 100)

    def update_device_levels(self, upb_cmd, level=-1, rate=-1):
        LOG.debug(f"{upb_cmd.name.capitalize()} {self.name} {self.index}")
        for device_link in self.devices:
            device = self._pim.devices.elements.get(device_link.device_id)
            if not device:
                continue

            if upb_cmd == UpbCommand.GOTO or upb_cmd == UpbCommand.FADE_START:
                set_level = level
            elif upb_cmd == UpbCommand.ACTIVATE:
                set_level = device_link.device_level
            else:
                set_level = 0

            device.setattr("status", set_level)
            LOG.debug(f"  Updating '{device.name}' to level {set_level}")

        changes = {"timestamp": time()}
        if level >= 0:
            changes["level"] = level
        if rate >= 0:
            changes["rate"] = rate
        changes["command"] = upb_cmd.name.lower()
        self.setattr("last_change", changes)


class Links(Elements):
    """Handling for multiple links."""

    def __init__(self, pim):
        super().__init__(pim)
        pim.add_handler(UpbCommand.ACTIVATE, self._activate_handler)
        pim.add_handler(UpbCommand.DEACTIVATE, self._deactivate_handler)
        pim.add_handler(UpbCommand.GOTO, self._goto_handler)

    def sync(self):
        pass

    def _levels(self, msg, upb_cmd, level=-1, rate=-1):
        if not msg.link:
            return
        breakpoint()
        index = LinkAddr(msg.network_id, msg.dest_id).index
        link = self.elements.get(index)
        if not link:
            return

        if rate >= 0:
            rate = rate_to_seconds(rate)

        link.update_device_levels(upb_cmd, level, rate)

    def _activate_handler(self, msg):
        self._levels(msg, UpbCommand.ACTIVATE)

    def _deactivate_handler(self, msg):
        self._levels(msg, UpbCommand.DEACTIVATE)

    def _goto_handler(self, msg):
        level = msg.data[0] if len(msg.data) else -1
        rate = msg.data[1] if len(msg.data) > 1 else -1
        self._levels(msg, UpbCommand.GOTO, level, rate)
