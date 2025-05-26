from datetime import timedelta, datetime
from dataclasses import dataclass
from typing import Optional, Dict, List

from ..book.select import GroupBy
from ..book.item import TodoItem


@dataclass
class ActionResult:
    def _todos_to_list(self, todos: List[TodoItem]) -> List[dict]:
        return [todo.to_dict() for todo in todos]

    def to_dict(self) -> dict:
        raise NotImplementedError


@dataclass
class ViewResult(ActionResult):
    grouped_todos: Dict[str, List[TodoItem]]
    group: GroupBy
    show_all: bool

    def to_dict(self) -> dict:
        return {
            "grouped_todos": {
                group: self._todos_to_list(todos)
                for group, todos in self.grouped_todos.items()
            },
            "group": self.group,
        }


@dataclass
class HistoryResult(ActionResult):
    history: List[Dict[str, str | datetime]]

    def to_dict(self) -> dict:
        return {
            "history": [
                {
                    "hash": item["hash"],
                    "message": item["message"],
                    "timestamp": item["timestamp"].isoformat(),  # type: ignore
                } for item in self.history
            ]
        }


@dataclass
class CommitResult(ActionResult):
    action: str
    message: str
    hexsha: str
    timestamp: datetime

    def to_dict(self) -> dict:
        return {
            "action": self.action,
            "message": self.message,
            "hexsha": self.hexsha,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class AddResult(ActionResult):
    item: TodoItem

    def to_dict(self) -> dict:
        return self.item.to_dict()


@dataclass
class EditResult(ActionResult):
    before: List[TodoItem]
    after: List[TodoItem]

    def to_dict(self) -> dict:
        return {
            "before": self._todos_to_list(self.before),
            "after": self._todos_to_list(self.after),
        }


def shorten(text: str, max_len: int) -> str:
    if max_len <= 0:
        return text
    if len(text) > max_len:
        return f"{text[:max_len]}…"
    return text


def pluralize(text: str, count: int) -> str:
    return f"{text}s" if count != 1 else text


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
    num_components: int = 2
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
        if count > 0:
            text.append(f'{count}{fmt[k]}')
    sign = "-" if negative else ""
    return f"{sign}{''.join(text) or '0s'}"
