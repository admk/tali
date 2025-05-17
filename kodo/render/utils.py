from datetime import date, datetime, timedelta
from typing import Optional, Literal

from termcolor import colored, ATTRIBUTES

from .. import constants
from ..book.item import Status


ATTRIBUTES |= {
    "italic": 3,
    "strike": 9,
}


def shorten(text: str, max_len: int) -> str:
    if len(text) > max_len:
        return f"{text[:max_len]}…"
    return text


def _timedelta_format(
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


def format_datetime(
    dt: Optional[date | datetime], status: Optional[Status] = None,
    mode: Literal["deadline", "created_at"] = "deadline",
    use_color: bool = True,
) -> str:
    if dt is None:
        return "^never"
    if isinstance(dt, date):
        dt = datetime.combine(dt, datetime.max.time())
    remaining_time = dt - datetime.now()
    if mode == "created_at":
        remaining_time = -remaining_time
    seconds = remaining_time.total_seconds()
    if abs(seconds) < 365 * 24 * 60 * 60:  # one year
        time = _timedelta_format(remaining_time, num_components=1)
    else:
        time = f"{dt:{constants.DATE_FORMAT}}"
    time = "^" + time
    if not use_color:
        return time
    if mode != "created_at" and (
        status is None or status not in ["done", "note"]
    ):
        attrs = constants.DEADLINE_ATTRS["_default"]
        for k, v in constants.DEADLINE_ATTRS.items():
            if isinstance(k, int) and remaining_time.total_seconds() < k:
                attrs = v
    else:
        attrs = constants.DEADLINE_ATTRS["_inactive"]
    return colored(time, **attrs)
