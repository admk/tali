from typing import Optional
from datetime import timedelta

from termcolor import colored, ATTRIBUTES


ATTRIBUTES |= {
    "italic": 3,
    "strike": 9,
}


def bold(text: str) -> str:
    return colored(text, attrs=["bold"])


def underline(text: str) -> str:
    return colored(text, attrs=["underline"])


def strike(text: str) -> str:
    return colored(text, attrs=["strike"])


def italic(text: str) -> str:
    return colored(text, attrs=["italic"])


def timedelta_format(
    delta: timedelta,
    fmt: Optional[str] = None,
    num_components: int = 2
):
    total_seconds = delta.total_seconds()
    negative = total_seconds < 0
    if negative:
        total_seconds = -total_seconds
    components = {
        'y': 31536000,
        'M': 2592000,
        'w': 604800,
        'd': 86400,
        'h': 3600,
        'm': 60,
        's': 1,
    }
    fmt = fmt or "".join(components.keys())
    if not all(c in components for c in fmt):
        raise ValueError(f'Invalid format: {fmt}')
    text = []
    leading_zeros = True
    for k, v in components.items():
        if k not in fmt:
            continue
        count = int(total_seconds // v)
        total_seconds -= count * v
        if leading_zeros and not count:
            continue
        leading_zeros = False
        if num_components is not None:
            if len(text) >= num_components:
                continue
        if count > 0:
            text.append(f'{count}{k}')
    sign = "-" if negative else ""
    return f"{sign}{''.join(text) or '0s'}"
