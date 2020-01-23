"""Definition of an UPB Light"""

import logging

from .const import UpbCommand
from .elements import Element, Elements
from .message import encode_report_state

LOG = logging.getLogger(__name__)


class Light(Element):
    """Class representing a Light"""

    def __init__(self, index, pim):
        super().__init__(index, pim)
        self.status = None
        self.version = None
        self.product = None
        self.kind = None
        self.network_id = None
        self.upb_id = None

    def level(self, level, time=0):
        """(Helper) Set light to specified level"""
        if level <= 0:
            self._elk.send(pf_encode(self._index))
        elif level >= 98:
            self._elk.send(pn_encode(self._index))
        else:
            self._elk.send(pc_encode(self._index, 9, level, time))

    def toggle(self):
        """(Helper) Toggle light"""
        self._elk.send(pt_encode(self._index))

class Lights(Elements):
    """Handling for multiple lights"""

    def __init__(self, pim):
        super().__init__(pim)
        pim.add_handler(UpbCommand.DEVICE_STATE_REPORT,
                        self._device_state_report_handler)
        pim.add_handler(UpbCommand.REGISTER_VALUES_REPORT,
                        self._register_values_report_handler)

    def sync(self):
        for light_id in self.elements:
            light = self.elements[light_id]
            self.pim.send(encode_report_state(light.network_id, light.upb_id))

    def _device_state_report_handler(self, light_id, dim_level):
        light = self.pim.lights.elements.get(light_id)
        if light:
            light.setattr("status", dim_level)
            LOG.debug("Light %s dim level is %d", light.name, light.status)

    def _register_values_report_handler(self, data):
        if len(data) != 17:
            LOG.debug("Parse register values only accepts 16 registers")
            return
        start_register = data[0]
        if start_register == 0:
            pass
        elif start_register == 16:
            network_name = data[1:].decode('UTF-8').strip()
            LOG.debug("Network name '{}'".format(network_name))
        elif start_register == 32:
            room_name = data[1:].decode('UTF-8').strip()
            LOG.debug("Room name '{}'".format(room_name))
        elif start_register == 48:
            device_name = data[1:].decode('UTF-8').strip()
            LOG.debug("Device name '{}'".format(device_name))
