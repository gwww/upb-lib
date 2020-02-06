"""Definition of an UPB Light"""

import logging

from .const import UpbCommand
from .elements import Element, Elements
from .message import (
    encode_blink,
    encode_fade_start,
    encode_fade_stop,
    encode_goto,
    encode_report_state,
)
from .util import light_index

LOG = logging.getLogger(__name__)


class Light(Element):
    """Class representing a Light"""

    def __init__(self, index, pim):
        super().__init__(index, pim)
        self.status = 0
        self.version = None
        self.product = None
        self.kind = None
        self.network_id = None
        self.upb_id = None
        self.channel = None
        self.dimmable = None

    def _level(self, brightness, rate):
        if rate > 255:
            rate = 255

        self._pim.send(
            encode_goto(
                False, self.network_id, self.upb_id, self.channel, brightness, rate
            )
        )
        self.setattr("status", brightness)

    def turn_on(self, brightness=100, rate=-1):
        """(Helper) Set light to specified level"""
        if not self.dimmable or brightness > 100:
            brightness = 100
        self._level(brightness, rate)

    def turn_off(self, rate=-1):
        """(Helper) Turn light off."""
        self._level(0, rate)

    def fade_start(self, brightness, rate=-1):
        """(Helper) Start fading a light."""
        self._pim.send(
            encode_fade_start(
                False, self.network_id, self.upb_id, self.channel, brightness, rate
            )
        )
        self.setattr("status", brightness)

    def fade_stop(self):
        """(Helper) Stop fading a light."""
        self._pim.send(
            encode_fade_stop(False, self.network_id, self.upb_id, self.channel)
        )
        self._pim.send(encode_report_state(self.network_id, self.upb_id))

    def blink(self, rate=-1):
        """(Helper) Blink a light."""
        self._pim.send(
            encode_blink(False, self.network_id, self.upb_id, self.channel, rate)
        )
        self.setattr("status", 100)

    def update_status(self):
        """(Helper) Get status of a light."""
        self._pim.send(encode_report_state(self.network_id, self.upb_id))

class Lights(Elements):
    """Handling for multiple lights"""

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
        for light_id in self.elements:
            light = self.elements[light_id]
            self.pim.send(encode_report_state(light.network_id, light.upb_id))

    def _device_state_report_handler(self, msg):
        status_length = len(msg.data)
        for i in range(0, 100):
            if i >= status_length:
                break

            index = light_index(msg.network_id, msg.src_id, i)
            light = self.pim.lights.elements.get(index)
            if not light:
                break

            level = msg.data[i]
            light.setattr("status", level)
            LOG.debug("(DSR) Light %s level is %d", light.name, light.status)

    def _goto_handler(self, msg):
        if msg.link:
            return
        channel = msg.data[2] if len(msg.data) > 2 else 0
        index = light_index(msg.network_id, msg.dest_id, channel)
        light = self.pim.lights.elements.get(index)
        if light:
            level = msg.data[0]
            light.setattr("status", level)
            LOG.debug(
                f"(GOTO) Light {light.name}/{light.index} level is {light.status}"
            )

    def _register_values_report_handler(self, msg):
        index = light_index(msg.network_id, msg.src_id, 0)
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
