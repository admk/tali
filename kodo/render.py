from datetime import datetime
from os import stat
from re import T
from typing import Optional, List, Dict, Tuple, Callable, Literal, Any

from . import constants
from .item import TodoItem, Status, Priority
from .utils import colored, timedelta_format


GroupBy = Literal[
    "all", "project", "tag", "status", "priority", "deadline", "created_at"]
SortBy = Literal[
    "id", "status", "title", "project", "tags", "priority",
    "deadline", "created_at"]
GroupFunc = Callable[[TodoItem], Optional[str | List[str]]]
SortFunc = Callable[[TodoItem], Any]


def _shorten(text: str, max_len: int) -> str:
    if len(text) > max_len:
        return f"{text[:max_len]}…"
    return text


def _format_date(
    date: Optional[datetime], status: Optional[Status] = None,
    mode: Literal["deadline", "created_at"] = "deadline",
    use_color: bool = True,
) -> str:
    if date is None:
        return "^never"
    remaining_time = date - datetime.now()
    if mode == "created_at":
        remaining_time = -remaining_time
    seconds = remaining_time.total_seconds()
    if abs(seconds) < 365 * 24 * 60 * 60:  # one year
        time = timedelta_format(remaining_time, num_components=1)
    else:
        time = f"{date:{constants.DATE_FORMAT}}"
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


class FilterMixin:
    @classmethod
    def _filter(
        cls, func: Callable[[TodoItem], bool], todos: List[TodoItem]
    ) -> List[TodoItem]:
        return [todo for todo in todos if func(todo)]

    @classmethod
    def filter_by_project(
        cls, todos: List[TodoItem], project: str = "Uncategorized"
    ) -> List[TodoItem]:
        return cls._filter(lambda todo: todo.project == project, todos)

    @classmethod
    def filter_by_tag(
        cls, todos: List[TodoItem], tag: Optional[str] = None
    ) -> List[TodoItem]:
        if tag is None:
            return cls._filter(lambda todo: not todo.tags, todos)
        return cls._filter(lambda todo: tag in todo.tags, todos)

    @classmethod
    def filter_by_status(
        cls, todos: List[TodoItem], status: Status = "pending"
    ) -> List[TodoItem]:
        return cls._filter(lambda todo: todo.status == status, todos)

    @classmethod
    def filter_by_priority(
        cls, todos: List[TodoItem], priority: Priority = "normal"
    ) -> List[TodoItem]:
        return cls._filter(lambda todo: todo.priority == priority, todos)

    @classmethod
    def _select_by_date_range(
        cls, date: datetime, date_range: Tuple[datetime, datetime]
    ) -> bool:
        from_date, to_date = date_range
        return from_date <= date <= to_date

    @classmethod
    def filter_by_deadline(
        cls, todos: List[TodoItem], date_range: Tuple[datetime, datetime]
    ) -> List[TodoItem]:
        func = lambda todo: \
            cls._select_by_date_range(todo.deadline, date_range)
        return cls._filter(func, todos)

    @classmethod
    def filter_by_created_at(
        cls, todos: List[TodoItem], date_range: Tuple[datetime, datetime]
    ) -> List[TodoItem]:
        func = lambda todo: \
            cls._select_by_date_range(todo.created_at, date_range)
        return cls._filter(func, todos)


class SortMixin:
    @staticmethod
    def sort_id(todo: TodoItem) -> int:
        return todo.id

    @staticmethod
    def sort_status(todo: TodoItem) -> int:
        return list(constants.STATUS_FORMATTED).index(todo.status)

    @staticmethod
    def sort_title(todo: TodoItem) -> str:
        return todo.title

    @staticmethod
    def sort_project(todo: TodoItem) -> str:
        return todo.project

    @staticmethod
    def sort_tags(todo: TodoItem) -> Tuple[str, ...]:
        return tuple(sorted(todo.tags))

    @staticmethod
    def sort_priority(todo: TodoItem) -> int:
        return list(constants.PRIORITY_FORMATTED).index(todo.priority)

    @staticmethod
    def sort_deadline(todo: TodoItem) -> datetime:
        return todo.deadline or datetime(9999, 12, 31)

    @staticmethod
    def sort_created_at(todo: TodoItem) -> datetime:
        return todo.created_at


class GroupMixin(SortMixin):
    @classmethod
    def _group(
        cls, todos: List[TodoItem],
        group_func: GroupFunc,
        group_sort_func: Optional[SortFunc] = None,
    ) -> Dict[str | datetime, List[TodoItem]]:
        groups = {}
        orders: Dict[str, Any] = {}
        for todo in todos:
            key_or_keys = group_func(todo)
            if group_sort_func:
                order = group_sort_func(todo)
            else:
                order = repr(key_or_keys)
            if not key_or_keys:
                continue
            if isinstance(key_or_keys, list):
                keys = key_or_keys
            else:
                keys = [key_or_keys]
            for key in keys:
                if key not in groups:
                    groups[key] = []
                groups[key].append(todo)
                if order is not None:
                    orders[key] = order
        ordered_groups = {}
        for key in sorted(orders.keys(), key=orders.get):  # type: ignore
            ordered_groups[key] = groups[key]
        return ordered_groups

    @classmethod
    def group_by_all(
        cls, todos: List[TodoItem]
    ) -> Dict[str | datetime, List[TodoItem]]:
        gfunc = lambda todo: "_all"
        return cls._group(todos, gfunc)

    @classmethod
    def group_by_project(
        cls, todos: List[TodoItem]
    ) -> Dict[str | datetime, List[TodoItem]]:
        gfunc = lambda todo: f"{constants.PREFIXES['project']}{todo.project}"
        return cls._group(todos, gfunc)

    @classmethod
    def group_by_tag(
        cls, todos: List[TodoItem]
    ) -> Dict[str | datetime, List[TodoItem]]:
        gfunc = lambda todo: [
            f"{constants.PREFIXES['tag']}{t}" for t in todo.tags
        ] if todo.tags else "untagged"
        return cls._group(todos, gfunc)

    @classmethod
    def group_by_status(
        cls, todos: List[TodoItem]
    ) -> Dict[str | datetime, List[TodoItem]]:
        gfunc = lambda todo: colored(
            constants.STATUS_FORMATTED[todo.status],
            **constants.STATUS_ATTRS[todo.status])
        return cls._group(todos, gfunc, cls.sort_status)

    @classmethod
    def group_by_priority(
        cls, todos: List[TodoItem]
    ) -> Dict[str | datetime, List[TodoItem]]:
        gfunc = lambda todo: colored(
            constants.PRIORITY_FORMATTED[todo.priority],
            **constants.PRIORITY_ATTRS[todo.priority])
        return cls._group(todos, gfunc, cls.sort_priority)

    @classmethod
    def group_by_deadline(
        cls, todos: List[TodoItem]
    ) -> Dict[str | datetime, List[TodoItem]]:
        def gfunc(todo: TodoItem) -> str:
            return _format_date(
                todo.deadline, todo.status, use_color=False)  # type: ignore
        return cls._group(todos, gfunc, cls.sort_deadline)

    @classmethod
    def group_by_created_at(
        cls, todos: List[TodoItem]
    ) -> Dict[str | datetime, List[TodoItem]]:
        def gfunc(todo: TodoItem) -> str:
            return _format_date(
                todo.created_at, todo.status,  # type: ignore
                "created_at", use_color=False)
        return cls._group(todos, gfunc, cls.sort_created_at)


class Renderer(FilterMixin, GroupMixin):
    def __init__(self) -> None:
        super().__init__()

    def get_stats(self, todos: List[TodoItem]):
        total = len(todos)
        done = len([t for t in todos if t.status == "done"])
        pending = len([t for t in todos if t.status == "pending"])
        notes = len([t for t in todos if t.status == "note"])
        progress = (done / total) if total > 0 else None
        return {
            "progress": progress,
            "done": done,
            "pending": pending,
            "note": notes
        }

    def render_stats(self, todos: List[TodoItem]) -> str:
        stats = self.get_stats(todos)
        text = []
        progress = stats["progress"]
        if progress is not None:
            progress_str = f"{stats['progress']:.0%}"
            attrs = constants.PROGRESS_ATTRS["_default"]
            for k, v in constants.PROGRESS_ATTRS.items():
                if isinstance(k, float) and progress <= k:
                    attrs = v
            progress_str = colored(progress_str, **attrs)
            text.append(f"\n  {progress_str} of all tasks complete.")
        stats_text = []
        for key in ["done", "pending", "note"]:
            key_formatted = colored(stats[key], **constants.STATUS_ATTRS[key])
            stats_text.append(f"{key_formatted} {key}")
        text.append("  " + " · ".join(stats_text))
        return "\n".join(text)

    def _render_id(self, todo: TodoItem) -> Optional[str]:
        return colored(str(todo.id), **constants.ID_ATTRS)

    def _render_status(self, todo: TodoItem) -> Optional[str]:
        status = todo.status
        symbol = colored(
            constants.STATUS_SYMBOLS[status], **constants.STATUS_ATTRS[status])
        return f"{symbol}"

    def _render_title(self, todo: TodoItem) -> Optional[str]:
        title = _shorten(todo.title, constants.MAX_TITLE_LENGTH)
        attrs = {}
        for k, v in constants.TITLE_ATTRS.items():
            p, q = k.split(".")
            if getattr(todo, p) == q:
                attrs |= v
        return colored(title, **attrs)

    def _render_tags(self, todo: TodoItem) -> Optional[str]:
        tags = []
        for tag in todo.tags:
            key = tag if tag in constants.TAG_SYMBOLS else "_default"
            default_tag = f"{constants.PREFIXES['tag']}{tag}"
            tags.append(colored(
                constants.TAG_SYMBOLS.get(key, default_tag),
                **constants.TAG_ATTRS[key]))
        return ",".join([tag for tag in tags])

    def _render_project(self, todo: TodoItem) -> Optional[str]:
        return colored(
            f"{constants.PREFIXES['project']}{todo.project}",
            **constants.PROJECT_ATTRS)  # type: ignore

    def _render_priority(self, todo: TodoItem) -> Optional[str]:
        priority = todo.priority
        symbol = constants.PRIORITY_SYMBOLS[priority] or ""
        if not symbol:
            return None
        return colored(symbol, **constants.PRIORITY_ATTRS[priority])

    def _render_deadline(self, todo: TodoItem) -> Optional[str]:
        if todo.deadline is None:
            return None
        return _format_date(todo.deadline, todo.status)  # type: ignore

    def _render_description(self, todo: TodoItem) -> Optional[str]:
        if todo.description is None:
            return None
        desc = _shorten(
            todo.description, constants.MAX_DESCRIPTION_LENGTH)
        return colored(desc, **constants.DESCRIPTION_ATTRS)

    def _render_item(self, todo: TodoItem, group_by: GroupBy) -> str:
        fields = {
            "id": self._render_id(todo),
            "status": self._render_status(todo),
            "title": self._render_title(todo),
            "tags": self._render_tags(todo),
            "priority": self._render_priority(todo),
            "project": self._render_project(todo),
            "deadline": self._render_deadline(todo),
            "description": self._render_description(todo),
        }
        fields = {k: " " + v if v else "" for k, v in fields.items()}
        return constants.FORMAT[group_by].format(**fields)

    def render(
        self, todos: List[TodoItem],
        group_by: GroupBy = "all",
        sort_by: SortBy = "id",
    ) -> str:
        text = []
        grouped = getattr(self, f"group_by_{group_by}")(todos)
        for group, gtodos in grouped.items():
            if not gtodos:
                continue
            gtodos = sorted(gtodos, key=getattr(self, f"sort_{sort_by}"))
            if group_by == "all":
                text.append("")
            else:
                stats = self.get_stats(gtodos)
                text.append("")
                progress = colored(
                    f"[{stats['done']}/{len(gtodos)}]",
                    **constants.GROUP_PROGRESS_ATTRS)
                group = colored(group, **constants.GROUP_ATTRS)  # type: ignore
                text.append(f"  {group} {progress}")
            for todo in gtodos:
                item = f"  {self._render_item(todo, group_by)}"
                text.append(item)
        text.append(self.render_stats(todos))
        return "\n".join(text)


if __name__ == "__main__":
    from .book import TaskBook
    book = TaskBook(path="book.json")
    print(Renderer().render(book.todos, sort_by="deadline"))
