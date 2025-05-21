from datetime import timedelta
from dataclasses import dataclass
from typing import Optional, Union, Dict, List

from ..book.select import GroupBy
from ..book.item import TodoItem


@dataclass
class ViewResult:
    grouped_todos: Dict[GroupBy, List[TodoItem]]
    group: GroupBy
    show_all: bool


@dataclass
class AddResult:
    item: TodoItem


@dataclass
class EditResult:
    before: List[TodoItem]
    after: List[TodoItem]


ActionResult = Union[ViewResult, AddResult, EditResult]


SECONDS = {
    "y": 31536000,
    'M': 2592000,
    'w': 604800,
    'd': 86400,
    'h': 3600,
    'm': 60,
    's': 1,
}


def shorten(text: str, max_len: int) -> str:
    if max_len <= 0:
        return text
    if len(text) > max_len:
        return f"{text[:max_len]}…"
    return text


def pluralize(text: str, count: int) -> str:
    return f"{text}s" if count != 1 else text


def timedelta_format(
    delta: timedelta,
    fmt: Optional[str] = None,
    num_components: int = 2
):
    total_seconds = delta.total_seconds()
    negative = total_seconds < 0
    if negative:
        total_seconds = -total_seconds
    fmt = fmt or "".join(SECONDS.keys())
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
        if count > 0:
            text.append(f'{count}{k}')
    sign = "-" if negative else ""
    return f"{sign}{''.join(text) or '0s'}"
