""" 
Parse UPStart file and create UPB light/link objects    
"""

import logging

from .const import PRODUCTS
from .lights import Light
from .links import Link, LightLink

LOG = logging.getLogger(__name__)


def process_upstart_file(pim, filename):
    try:
        with open(filename) as f:
            _process_file(pim, f)
            f.close()
    except EnvironmentError as e:
        LOG.error(f"Cannot open UPStart file '{filename}': {e}")


def _process_file(pim, file):
    for line in file:
        fields = line.strip().split(",")

        # File overview record
        if fields[0] == "0":
            network_id = int(fields[4])

        # Link definition record
        elif fields[0] == "2":
            link_id = int(fields[1])
            index = "{}_{}".format(network_id, link_id)
            link = Link(index, pim)

            link.name = fields[2]
            link.network_id = network_id
            link.link_id = link_id
            pim.links.add_element(link)

        # Light record
        elif fields[0] == "3":
            # network_id used in future reads, until it changes
            upb_id = int(fields[1])
            network_id = int(fields[2])
            index = "{}_{}".format(network_id, upb_id)
            light = Light(index, pim)

            light.network_id = network_id
            light.upb_id = upb_id
            light.name = "{} {}".format(fields[11], fields[12])
            light.version = "{}.{}".format(fields[5], fields[6])

            product = "{}/{}".format(fields[3], fields[4])
            if product in PRODUCTS:
                light.product = PRODUCTS[product][0]
                light.kind = PRODUCTS[product][1]
            else:
                light.product = product
                light.kind = fields[7]

            pim.lights.add_element(light)

        # Channel info record, only care about dimmable flag
        elif fields[0] == "8":
            light_id = "{}_{}".format(network_id, fields[2])
            light = pim.lights.elements[light_id]
            light.dimmable = True if fields[3] == "1" else False

        # Light link definition
        elif fields[0] == "4":
            link_id = int(fields[4])
            if link_id == 255:
                continue

            link_index = "{}_{}".format(network_id, link_id)
            light_index = "{}_{}".format(network_id, int(fields[3]))
            dim_level = int(fields[5])
            pim.links[link_index].add_light(LightLink(light_index, dim_level))
