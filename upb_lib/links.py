"""Definition of an link (scene)"""

from collections import namedtuple
import logging

from .const import UpbCommand
from .elements import Element, Elements
from .message import encode_goto, encode_activate_link, encode_deactivate_link

LOG = logging.getLogger(__name__)


Light_link = namedtuple("Light_link", "light_id, dim_level")


class Link(Element):
    """Class representing a Light"""

    def __init__(self, index, pim):
        super().__init__(index, pim)
        self.lights = []
        self.network_id = None
        self.link_id = None

    def add_light(self, light_link):
        self.lights.append(light_link)

    def activate(self):
        """(Helper) Activate link"""
        self._pim.send(encode_activate_link(self.network_id, self.link_id))

    def deactivate(self):
        """(Helper) Deactivate link"""
        self._pim.send(encode_deactivate_link(self.network_id, self.link_id))

    def level(self, level, rate=-1):
        """(Helper) Set lights in link to specified level"""
        if level < 0:
            level = 0
        elif level > 99:
            level = 100
        self._pim.send(encode_goto(True, self.network_id, self.link_id, level, rate))

class Links(Elements):
    """Handling for multiple lights"""

    def __init__(self, pim):
        super().__init__(pim)
        pim.add_handler(UpbCommand.ACTIVATE, self._activate_handler)
        pim.add_handler(UpbCommand.DEACTIVATE, self._deactivate_handler)

    def sync(self):
        pass

    def _activate_deactivate(self, link_id, link_levels):
        act = "Activate" if link_levels else "Deactivate"
        if link_id not in self.elements:
            LOG.warning(
                "UPB {} command received for unknown link: {}".format(act, link_id)
            )
            return

        LOG.debug("{} '{}' ({})".format(act, self.elements[link_id].name, link_id))
        lights = self.elements[link_id].lights
        for light_link in lights:
            if light_link.light_id not in self.pim.lights.elements:
                continue

            light = self.pim.lights.elements[light_link.light_id]
            light.setattr("status", light_link.dim_level if link_levels else 0)
            LOG.debug(
                "  Updating '{}' to dim level {}".format(
                    light.name, light_link.dim_level if link_levels else 0
                )
            )

    def _activate_handler(self, link_id):
        self._activate_deactivate(link_id, True)

    def _deactivate_handler(self, link_id):
        self._activate_deactivate(link_id, False)
