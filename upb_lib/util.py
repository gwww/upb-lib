"""Utility functions"""

import contextlib
import re
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from .const import TCP_DEFAULT_PORT

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


def parse_url(url: str) -> str:
    """Parse a PIM connection string for backward compatibility."""
    if url.startswith("tcp://"):
        # Backward compatibility for tcp://host (without port) where default port
        # is TCP_DEFAULT_PORT.
        # New installations should use socket://host:port
        parts = urlsplit(url)
        if parts.netloc and ":" not in parts.netloc:
            parts = parts._replace(netloc=f"{parts.netloc}:{TCP_DEFAULT_PORT}")
            return urlunsplit(parts)
        return url
    if url.startswith("serial://"):
        # Backwards compatibility for serial:// and baudrate at end of URL
        # New installations should use device:// and no longer include baudrate in URL
        new_url = url.replace("serial://", "device://", 1)
        new_url = re.sub(r":([0-9]+)$", r"", new_url)
        return new_url
    return url


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
