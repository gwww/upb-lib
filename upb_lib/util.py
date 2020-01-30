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


def light_index(network, light_id, channel):
    """Format a light ID"""
    return f"{network}_{light_id}_{channel}"


def link_index(network, link_id):
    """Format a link ID"""
    return f"{network}_{link_id}"
