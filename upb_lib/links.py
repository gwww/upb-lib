"""Definition of an link (scene)"""
from collections import namedtuple
from enum import Enum
import logging
from time import time

from .const import UpbCommand
from .elements import Element, Elements
from .message import encode_goto, encode_activate_link, encode_deactivate_link
from .util import link_index

LOG = logging.getLogger(__name__)


LightLink = namedtuple("LightLink", "light_id, dim_level")


class Link(Element):
    """Class representing a Light"""

    def __init__(self, index, pim):
        super().__init__(index, pim)
        self.lights = []
        self.network_id = None
        self.link_id = None
        self.last_change = None

    def add_light(self, light_link):
        self.lights.append(light_link)

    def activate(self):
        """(Helper) Activate link"""
        self._pim.send(encode_activate_link(self.network_id, self.link_id))
        self.update_light_levels(UpbCommand.ACTIVATE)

    def deactivate(self):
        """(Helper) Deactivate link"""
        self._pim.send(encode_deactivate_link(self.network_id, self.link_id))
        self.update_light_levels(UpbCommand.DEACTIVATE)

    def goto(self, brightness, rate=-1):
        """(Helper) Goto level"""
        if brightness > 100:
            brightness = 100

        self._pim.send(
            encode_goto(True, self.network_id, self.link_id, 0, brightness, rate)
        )
        self.update_light_levels(UpbCommand.GOTO, brightness)

    def update_light_levels(self, upb_cmd, level=0):
        LOG.debug(f"{upb_cmd.name.capitalize()} {self.name} {self.index}")
        for light_link in self.lights:
            light = self._pim.lights.elements.get(light_link.light_id)
            if not light:
                continue

            if upb_cmd == UpbCommand.GOTO:
                set_level = level
            elif upb_cmd == UpbCommand.ACTIVATE:
                set_level = light_link.dim_level
            else:
                set_level = 0

            light.setattr("status", set_level)
            LOG.debug(f"  Updating '{light.name}' to dim level {set_level}")

        if upb_cmd == UpbCommand.GOTO:
            self.setattr("last_change", {"command": "goto", "level": level})
        else:
            self.setattr("last_change", {"command": upb_cmd.name.lower()})


class Links(Elements):
    """Handling for multiple lights"""

    def __init__(self, pim):
        super().__init__(pim)
        pim.add_handler(UpbCommand.ACTIVATE, self._activate_handler)
        pim.add_handler(UpbCommand.DEACTIVATE, self._deactivate_handler)
        pim.add_handler(UpbCommand.GOTO, self._goto_handler)

    def sync(self):
        pass

    def _activate_deactivate(self, msg, upb_cmd, level=0):
        if not msg.link:
            return
        index = link_index(msg.network_id, msg.dest_id)
        link = self.elements.get(index)
        if not link:
            LOG.warning(f"UPB command received for unknown link: {index}")
            return

        link.update_light_levels(upb_cmd, level)

    def _activate_handler(self, msg):
        self._activate_deactivate(msg, UpbCommand.ACTIVATE)

    def _deactivate_handler(self, msg):
        self._activate_deactivate(msg, UpbCommand.DEACTIVATE)

    def _goto_handler(self, msg):
        self._activate_deactivate(msg, UpbCommand.GOTO, msg.data[0])
