"""Utility functions"""

import contextlib
import re
from typing import Any

# Array for converting seconds to a rate (aka transition) length
SECONDS_TO_RATE = [
    0,
    0.8,
    1.6,
    3.3,
    5,
    6.6,
    10,
    20,
    30,
    60,
    120,
    300,
    600,
    900,
    1800,
    3600,
]


def seconds_to_rate(seconds: float) -> int:
    """Convert seconds to a UPB rate value."""
    return min(
        range(len(SECONDS_TO_RATE)), key=lambda i: abs(SECONDS_TO_RATE[i] - seconds)
    )


def rate_to_seconds(rate: int) -> float:
    """Convert a UPB rate value to seconds."""
    if rate < len(SECONDS_TO_RATE):
        return SECONDS_TO_RATE[rate]
    return -1


def check_dim_params(brightness: int, rate: int, use_raw_rate: bool) -> tuple[int, int]:
    """Check that device params are in range."""
    brightness = round(brightness)
    if brightness < 0:
        brightness = 0
    elif brightness > 100:
        brightness = 100

    if rate != -1:
        if use_raw_rate:
            rate = round(rate)
            if rate < 0:
                rate = 0
            elif rate > 255:
                rate = 255
        else:
            rate = seconds_to_rate(rate)

    return (brightness, rate)


def parse_url(url: str) -> tuple[str, str, int]:
    """Parse a PIM connection string"""
    scheme, dest = url.split("://")
    host = None
    if scheme == "tcp":
        host, port = dest.split(":") if ":" in dest else (dest, 2101)
    elif scheme == "serial":
        host, port = dest.split(":") if ":" in dest else (dest, 4800)
    else:
        raise ValueError(f"Invalid scheme '{scheme}'")
    return (scheme, host, int(port))


def parse_flags(flags_in: str) -> dict[str, Any]:
    """Parse flags that change behavior of library."""
    flags = re.split(r"\s*,\s*", flags_in)
    return_value = {}
    for flag in flags:
        flag = re.split(r"\s*=\s*", flag)
        if len(flag) == 1:
            return_value[flag[0]] = True
        elif len(flag) == 2:
            with contextlib.suppress(ValueError):
                flag[1] = int(flag[1])
            return_value[flag[0]] = flag[1]
    return return_value
