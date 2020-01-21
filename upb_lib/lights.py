"""Definition of an UPB Light"""

import logging

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
