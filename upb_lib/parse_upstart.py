""" 
Parse UPStart file and create UPB light/link objects    
"""

from .const import PRODUCTS
from .lights import Light, Lights
from .links import Link, Links, Light_link


def process_upstart_file(pim, filename):
    try:
        with open(filename) as f:
            _process_file(pim, f)
            f.close()
    except EnvironmentError as e:
        print("Cannot open UPStart file '{}': {}".format(filename, e))


def _process_file(pim, file):

    pim.lights = Lights(pim)
    pim.links = Links(pim)

    for line in file:
        fields = line.strip().split(",")

        # Light record
        if fields[0] == "3":
            # network_id used in future reads, until it changes
            network_id = int(fields[2])

            light_id = "{}/{}".format(network_id, fields[1])
            light = Light(light_id, pim)
            pim.lights.add_element(light_id, light)

            light.network_id = network_id
            light.upb_id = int(fields[1])
            light.name = "{} {}".format(fields[11], fields[12])
            light.version = "{}.{}".format(fields[5], fields[6])

            product = "{}/{}".format(fields[3], fields[4])
            if product in PRODUCTS:
                light.product = PRODUCTS[product][0]
                light.kind = PRODUCTS[product][1]
            else:
                light.product = product
                light.kind = fields[7]

        # Channel info record
        elif fields[0] == "8":
            light_id = "{}/{}".format(network_id, fields[2])
            light = pim.lights.elements[light_id]
            light.dimmable = True if fields[3] == "1" else False

        elif fields[0] == "0":
            network_id = int(fields[4])

        # Link definition record
        elif fields[0] == "2":
            link_id = int(fields[1])
            link = Link(link_id, pim)
            pim.links.add_element(link_id, link)
            link.name = fields[2]
            link.network_id = network_id
            link.link_id = link_id

        # Light link definition
        elif fields[0] == "4":
            link_id = int(fields[4])
            if link_id == 255:
                continue

            light_id = "{}/{}".format(network_id, fields[3])
            dim_level = int(fields[5])
            pim.links[link_id].add_light(Light_link(light_id, dim_level))
