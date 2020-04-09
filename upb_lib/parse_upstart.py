"""
Parse UPStart file and create UPB light/link objects
"""

import logging

from .const import PRODUCTS
from .lights import Light, UPBAddr
from .links import LightLink, Link, LinkAddr

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
            link = Link(LinkAddr(network_id, link_id), pim)
            link.name = fields[2]
            pim.links.add_element(link)

        # Light record
        elif fields[0] == "3":
            # network_id used in future reads, until it changes
            upb_id = int(fields[1])
            network_id = int(fields[2])
            number_of_channels = int(fields[8])
            multi_channel = number_of_channels > 1
            for channel in range(0, number_of_channels):
                light = Light(UPBAddr(network_id, upb_id, channel, multi_channel), pim)
                if multi_channel:
                    light.name = f"{fields[11]} {fields[12]} {channel}"
                else:
                    light.name = f"{fields[11]} {fields[12]}"
                light.version = f"{fields[5]}.{fields[6]}"

                product = f"{fields[3]}/{fields[4]}"
                if product in PRODUCTS:
                    light.product = PRODUCTS[product][0]
                    light.kind = PRODUCTS[product][1]
                else:
                    light.product = product
                    light.kind = fields[7]

                pim.lights.add_element(light)

        # Channel info record, only care about dimmable flag
        elif fields[0] == "8":
            light_id = UPBAddr(network_id, fields[2], fields[1]).index
            light = pim.lights.elements[light_id]
            light.dimmable = True if fields[3] == "1" else False

        # Light link definition
        elif fields[0] == "4":
            link_id = int(fields[4])
            if link_id == 255:
                continue

            link_idx = LinkAddr(network_id, link_id).index
            light_idx = UPBAddr(network_id, fields[3], fields[1]).index
            dim_level = int(fields[5])
            pim.links[link_idx].add_light(LightLink(light_idx, dim_level))

        # Rename definition - not part of UPE file spec
        elif fields[0] == "99":
            light = pim.lights.elements.get(fields[1])
            if light:
                light.name = fields[2]
