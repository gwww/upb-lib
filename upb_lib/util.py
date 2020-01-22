"""Utility functions"""


def parse_url(url):
    """Parse a PIM connection string """
    scheme, dest = url.split("://")
    host = None
    if scheme == "tcp":
        host, port = dest.split(":") if ":" in dest else (dest, 2101)
    elif scheme == "serial":
        host, port = dest.split(":") if ":" in dest else (dest, 4800)
    else:
        raise ValueError("Invalid scheme '%s'" % scheme)
    return (scheme, host, int(port))


def light_id(network, light_id, channel):
    """Format a light ID"""
    return "{}/{}".format(network, light_id)
