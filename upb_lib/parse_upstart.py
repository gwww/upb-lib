"""
Parse UPStart file and create UPB device/link objects
"""

import logging

from .const import MANUFACTURERS, PRODUCTS
from .devices import UpbAddr, UpbDevice
from .links import DeviceLink, Link, LinkAddr
from .util import parse_flags

LOG = logging.getLogger(__name__)


def process_upstart_file(pim, filename):
    """Process the UPStart UPE file."""
    try:
        with open(filename) as file_handle:
            _process_file(pim, file_handle)
            file_handle.close()
        return True
    except EnvironmentError as exc:
        LOG.error("Cannot open UPStart file: %s", exc)
        return False


def _process_file(pim, file):
    for line in file:
        fields = line.strip().split(",")
        if fields[0] == "0":
            # File overview record
            network_id = int(fields[4])
            pim.network_id = network_id
        elif fields[0] == "2":
            _link_definition_record(pim, network_id, fields)
        elif fields[0] == "3":
            _device_definition_record(pim, network_id, fields)
        elif fields[0] == "8":
            _channel_definition_record(pim, network_id, fields)
        elif fields[0] == "4":
            _link_device_definition_record(pim, network_id, fields)
        elif fields[0] == "98":
            _custom_flags_record(pim, ",".join(fields[1:]))
        elif fields[0] == "99":
            _rename_device_record(pim, fields)


def _link_definition_record(pim, network_id, fields):
    link_id = int(fields[1])
    link = Link(LinkAddr(network_id, link_id), pim)
    link.name = fields[2]
    pim.links.add_element(link)


def _device_definition_record(pim, network_id, fields):
    upb_id = int(fields[1])
    number_of_channels = int(fields[8])
    multi_channel = number_of_channels > 1
    for channel in range(0, number_of_channels):
        device = UpbDevice(UpbAddr(network_id, upb_id, channel, multi_channel), pim)
        if multi_channel:
            device.name = f"{fields[11]} {fields[12]} {channel}"
        else:
            device.name = f"{fields[11]} {fields[12]}"
        device.version = f"{fields[5]}.{fields[6]}"

        device.manufacturer = MANUFACTURERS.get(fields[3], fields[3])
        product = f"{fields[3]}/{fields[4]}"
        if product in PRODUCTS:
            device.product = PRODUCTS[product][0]
            device.kind = PRODUCTS[product][1]
        else:
            device.product = product
            device.kind = fields[7]

        pim.devices.add_element(device)


def _channel_definition_record(pim, network_id, fields):
    device_id = UpbAddr(network_id, fields[2], fields[1]).index
    device = pim.devices.elements.get(device_id)
    if device:
        device.dimmable = fields[3] == "1"


def _link_device_definition_record(pim, network_id, fields):
    link_id = int(fields[4])
    if link_id == 255:
        return

    link_idx = LinkAddr(network_id, link_id).index
    device_idx = UpbAddr(network_id, fields[3], fields[1]).index
    dim_level = int(fields[5])
    pim.links[link_idx].add_device(DeviceLink(device_idx, dim_level))


def _rename_device_record(pim, fields):
    device = pim.devices.elements.get(fields[1])
    if device:
        device.name = fields[2]


def _custom_flags_record(pim, flags):
    pim.flags = parse_flags(flags)
