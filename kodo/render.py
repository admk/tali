from datetime import datetime
from os import stat
from typing import Optional, List, Dict, Tuple, Callable, Literal, Any

from . import constants
from .item import TodoItem, Status, Priority
from .utils import colored, timedelta_format


GroupBy = Literal[
    "all", "project", "tag", "status", "priority", "deadline", "created_at"]
GroupFunc = Callable[[TodoItem], Optional[str | List[str]]]
OrderFunc = Callable[[TodoItem], Any]


class Renderer:
    def __init__(self) -> None:
        super().__init__()
        self._priority_formatted = {
            k: f"{v} {k}" if v is not None else k
            for k, v in constants.PRIORITY_SYMBOLS.items()}
        self._status_formatted = {
            k: f"{v} {k}" for k, v in constants.STATUS_SYMBOLS.items()}

    @staticmethod
    def _shorten(text: str, max_len: int) -> str:
        if len(text) > max_len:
            return f"{text[:max_len]}…"
        return text

    def _format_date(
        self, date: Optional[datetime], status: Optional[Status] = None,
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

    @staticmethod
    def _sort_id(todo: TodoItem) -> int:
        return todo.id

    @staticmethod
    def _sort_deadline(todo: TodoItem) -> datetime:
        return todo.deadline or datetime(9999, 12, 31)

    def _filter(
        self, func: Callable[[TodoItem], bool], todos: List[TodoItem]
    ) -> List[TodoItem]:
        return [todo for todo in todos if func(todo)]

    def filter_by_project(
        self, todos: List[TodoItem], project: str = "Uncategorized"
    ) -> List[TodoItem]:
        return self._filter(lambda todo: todo.project == project, todos)

    def filter_by_tag(
        self, todos: List[TodoItem], tag: Optional[str] = None
    ) -> List[TodoItem]:
        if tag is None:
            return self._filter(lambda todo: not todo.tags, todos)
        return self._filter(lambda todo: tag in todo.tags, todos)

    def filter_by_status(
        self, todos: List[TodoItem], status: Status = "pending"
    ) -> List[TodoItem]:
        return self._filter(lambda todo: todo.status == status, todos)

    def filter_by_priority(
        self, todos: List[TodoItem], priority: Priority = "normal"
    ) -> List[TodoItem]:
        return self._filter(lambda todo: todo.priority == priority, todos)

    @staticmethod
    def _select_by_date_range(
        date: datetime, date_range: Tuple[datetime, datetime]
    ) -> bool:
        from_date, to_date = date_range
        return from_date <= date <= to_date

    def filter_by_deadline(
        self, todos: List[TodoItem], date_range: Tuple[datetime, datetime]
    ) -> List[TodoItem]:
        func = lambda todo: \
            self._select_by_date_range(todo.deadline, date_range)
        return self._filter(func, todos)

    def filter_by_created_at(
        self, todos: List[TodoItem], date_range: Tuple[datetime, datetime]
    ) -> List[TodoItem]:
        func = lambda todo: \
            self._select_by_date_range(todo.created_at, date_range)
        return self._filter(func, todos)

    def _group(
        self, todos: List[TodoItem],
        group_func: GroupFunc, order_func: Optional[OrderFunc] = None,
    ) -> Dict[str | datetime, List[TodoItem]]:
        groups = {}
        orders: Dict[str, Any] = {}
        for todo in todos:
            key_or_keys = group_func(todo)
            if order_func:
                order = order_func(todo)
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

    def group_by_all(
        self, todos: List[TodoItem]
    ) -> Dict[str | datetime, List[TodoItem]]:
        gfunc = lambda todo: "_all"
        return self._group(todos, gfunc)

    def group_by_project(
        self, todos: List[TodoItem]
    ) -> Dict[str | datetime, List[TodoItem]]:
        gfunc = lambda todo: f"{constants.PREFIXES['project']}{todo.project}"
        return self._group(todos, gfunc)

    def group_by_tag(
        self, todos: List[TodoItem]
    ) -> Dict[str | datetime, List[TodoItem]]:
        gfunc = lambda todo: [
            f"{constants.PREFIXES['tag']}{t}" for t in todo.tags
        ] if todo.tags else "untagged"
        return self._group(todos, gfunc)

    def group_by_status(
        self, todos: List[TodoItem]
    ) -> Dict[str | datetime, List[TodoItem]]:
        gfunc = lambda todo: colored(
            self._status_formatted[todo.status],
            **constants.STATUS_ATTRS[todo.status])
        ofunc = lambda todo: list(self._status_formatted).index(todo.status)
        return self._group(todos, gfunc, ofunc)

    def group_by_priority(
        self, todos: List[TodoItem]
    ) -> Dict[str | datetime, List[TodoItem]]:
        gfunc = lambda todo: colored(
            self._priority_formatted[todo.priority],
            **constants.PRIORITY_ATTRS[todo.priority])
        ofunc = lambda todo: \
            list(self._priority_formatted).index(todo.priority)
        return self._group(todos, gfunc, ofunc)

    def group_by_deadline(
        self, todos: List[TodoItem]
    ) -> Dict[str | datetime, List[TodoItem]]:
        def gfunc(todo: TodoItem) -> str:
            return self._format_date(
                todo.deadline, todo.status, use_color=False)  # type: ignore
        ofunc = lambda todo: todo.deadline or datetime(9999, 12, 31)
        return self._group(todos, gfunc, ofunc)

    def group_by_created_at(
        self, todos: List[TodoItem]
    ) -> Dict[str | datetime, List[TodoItem]]:
        def gfunc(todo: TodoItem) -> str:
            return self._format_date(
                todo.created_at, todo.status,  # type: ignore
                "created_at", use_color=False)
        ofunc = lambda todo: todo.deadline
        return self._group(todos, gfunc, ofunc)

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
        title = self._shorten(todo.title, constants.MAX_TITLE_LENGTH)
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
        return self._format_date(todo.deadline, todo.status)  # type: ignore

    def _render_description(self, todo: TodoItem) -> Optional[str]:
        if todo.description is None:
            return None
        desc = self._shorten(
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
        self, todos: List[TodoItem], group_by: GroupBy = "all",
    ) -> str:
        text = []
        grouped = getattr(self, f"group_by_{group_by}")(todos)
        for group, gtodos in grouped.items():
            if not gtodos:
                continue
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
    book = TaskBook()
    book.add("Task", "This is a task", "project", ["wip"], priority="low", deadline=datetime(2025, 7, 15))
    book.add("Complete task", "This is a complete task", "project", ["test"], "done")
    book.add("A note", None, "another", ["star"], "note", "high")
    print(Renderer().render(book.todos))
