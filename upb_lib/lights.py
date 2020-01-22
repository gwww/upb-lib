"""Definition of an UPB Light"""

import logging

from .const import UpbCommand
from .elements import Element, Elements

LOG = logging.getLogger(__name__)


class Light(Element):
    """Class representing a Light"""

    def __init__(self, index, pim):
        super().__init__(index, pim)
        self.status = None
        self.version = None
        self.product = None
        self.kind = None
        self.upb_id = None
        self.network_id = None


class Lights(Elements):
    """Handling for multiple lights"""

    def __init__(self, pim):
        super().__init__(pim)
        pim.add_handler(UpbCommand.DEVICE_STATE_REPORT,
                        self._device_state_report_handler)

    def _device_state_report_handler(self, light_id, dim_level):
        light = self.pim.lights.elements.get(light_id)
        if light:
            light.setattr("status", dim_level)
            LOG.debug("Light %s new dim level is %d", light.name, light.status)
