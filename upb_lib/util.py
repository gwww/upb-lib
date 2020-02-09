"""Utility functions"""

import re


# Array for converting seconds to a rate (aka transition) length
SECS_TO_RATE = [
    0, 0.8, 1.6, 3.3, 5, 6.6, 10, 20, 30, 60, 120, 600, 1800, 3600,
]

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


def parse_flags(flags):
    """Parse flags that change behavior of library."""
    flags = re.split(r"\s*,\s*", flags)
    return_value = {}
    for flag in flags:
        flag = re.split(r"\s*=\s*", flag)
        if len(flag) == 1:
            return_value[flag[0]] = True
        elif len(flag) == 2:
            try:
                flag[1] = int(flag[1])
            except:
                pass
            return_value[flag[0]] = flag[1]
    return return_value


def light_index(network, light_id, channel):
    """Format a light ID"""
    return f"{network}_{light_id}_{channel}"


def link_index(network, link_id):
    """Format a link ID"""
    return f"{network}_{link_id}"


def seconds_to_rate(seconds):
    return min(range(len(SECS_TO_RATE)), key=lambda i: abs(SECS_TO_RATE[i]-seconds))
