import re
from datetime import timedelta
from typing import Optional, Dict


def shorten(text: str, max_len: int, ellipsis: str = '…') -> str:
    if max_len <= 0:
        return text
    if len(text) > max_len:
        return f"{text[:max_len - len(ellipsis)]}{ellipsis}"
    return text


def pluralize(text: str, count: int, plural: Optional[str] = None) -> str:
    plural = plural or f"{text}s"
    return plural if count != 1 else text


def strip_rich(text: str) -> str:
    text = re.sub(r"\[.*?\]", "", text)
    text = re.sub(r"\[/.*?\]", "", text)
    return text


SECONDS = {
    "y": 31536000,
    "M": 2592000,
    "w": 604800,
    "d": 86400,
    "h": 3600,
    "m": 60,
    "s": 1,
}
_DEFAULT_FORMAT = {
    "y": "[green]y[/]",
    "M": "[cyan]M[/]",
    "w": "[blue]w[/]",
    "d": "[yellow]d[/]",
    "h": "[magenta]h[/]",
    "m": "[red]m[/]",
    "s": "s",
}


def timedelta_format(
    delta: timedelta,
    fmt: Optional[str | Dict[str, str]] = None,
    num_components: int = 2,
    skip_zeros: bool = True
):
    total_seconds = delta.total_seconds()
    negative = total_seconds < 0
    if negative:
        total_seconds = -total_seconds
    fmt = fmt or _DEFAULT_FORMAT
    if isinstance(fmt, str):
        fmt = {c: _DEFAULT_FORMAT[c] for c in fmt}
    if not all(c in SECONDS for c in fmt):
        raise ValueError(f'Invalid format: {fmt}')
    text = []
    leading_zeros = True
    for k, v in SECONDS.items():
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
        if skip_zeros:
            text.append(f'{count}{fmt[k]}')
        elif count > 0:
            text.append(f'{count}{fmt[k]}')
    sign = "-" if negative else ""
    return f"{sign}{''.join(text) or '0s'}"
