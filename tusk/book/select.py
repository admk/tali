from datetime import datetime, date
from typing import (
    get_args, Optional, List, Dict, Tuple, Callable, Literal, Any)

from box import Box

from ..book.item import TodoItem, Status, Priority


FilterBy = Literal[
    "title", "project", "tag", "status", "priority", "deadline", "created_at"]
ActBy = Literal["add", "delete"] | FilterBy
GroupBy = Literal[
    "id_range", "project", "tag", "status", "priority", "deadline", "created_at"]
SortBy = Literal[
    "id_range", "status", "title", "project", "tags", "priority",
    "deadline", "created_at"]
FilterValue = str | Tuple[datetime, datetime]
GroupKey = Optional[str | datetime | date]
GroupFunc = Callable[[TodoItem], GroupKey]
SortFunc = Callable[[TodoItem], Any]


class SelectMixin:
    config: Box


class FilterMixin(SelectMixin):
    def filter_by_ids(self, todos, ids: List[int]) -> bool:
        return todos.id in ids

    def filter_by_title(self, todos, title: str) -> bool:
        return title.lower() in todos.title.lower()

    def filter_by_project(self, todos, project: str) -> bool:
        separator = self.config.token.project
        splits = project.split(separator)
        todo_splits = todos.project.split(separator)
        suffix_len = max(len(splits) - len(todo_splits), 0)
        todo_splits += [None] * suffix_len
        return all(p == q for p, q in zip(splits, todo_splits))

    def filter_by_tags(self, todo: TodoItem, tags: List[str]) -> bool:
        return all(t in todo.tags for t in tags) if tags else not todo.tags

    def filter_by_status(self, todo: TodoItem, status: Status) -> bool:
        status = self.config.alias.status.get(status, status)
        if status not in get_args(Status):
            raise ValueError(f"Unrecognized status {status!r}.")
        return todo.status == status

    def filter_by_priority(self, todo: TodoItem, priority: Priority) -> bool:
        return todo.priority == priority

    def _select_by_date_range(
        self, date: datetime, date_range: Tuple[datetime, datetime]
    ) -> bool:
        from_date, to_date = date_range
        return from_date <= date <= to_date

    def filter_by_deadline(
        self, todo: TodoItem, date_range: Tuple[datetime, datetime]
    ) -> bool:
        if todo.deadline is None:
            return False
        return self._select_by_date_range(todo.deadline, date_range)

    def filter_by_created_at(
        self, todo: TodoItem, date_range: Tuple[datetime, datetime]
    ) -> bool:
        return self._select_by_date_range(todo.created_at, date_range)

    def filter(
        self, todos, filters: Dict[FilterBy, FilterValue]
    ) -> List[TodoItem]:
        filtered_todos = []
        for todo in todos:
            for key, value in filters.items():
                func = getattr(self, f"filter_by_{key}")
                if not func(todo, value):
                    break
            else:
                filtered_todos.append(todo)
        return filtered_todos


class SortMixin(SelectMixin):
    def sort_id_range(self, todo: TodoItem) -> int:
        return todo.id

    def sort_status(self, todo: TodoItem) -> int:
        return list(self.config.group.header.status).index(todo.status)

    def sort_title(self, todo: TodoItem) -> str:
        return todo.title

    def sort_project(self, todo: TodoItem) -> str:
        return todo.project

    def sort_tags(self, todo: TodoItem) -> Tuple[str, ...]:
        return tuple(sorted(todo.tags))

    def sort_priority(self, todo: TodoItem) -> int:
        return list(self.config.group.header.priority).index(todo.priority)

    def sort_deadline(self, todo: TodoItem) -> datetime:
        return todo.deadline or datetime(9999, 12, 31)

    def sort_created_at(self, todo: TodoItem) -> datetime:
        return todo.created_at

    def sort(
        self, todos: List[TodoItem], mode: SortBy,
    ) -> List[TodoItem]:
        return sorted(todos, key=getattr(self, f"sort_{mode}"))


class GroupMixin(SortMixin):
    def _group_by_value(
        self, name: str
    ) -> Tuple[GroupFunc, Optional[SortFunc]]:
        gfunc = lambda todo: getattr(todo, name)
        sfunc = getattr(self, f"sort_{name}")
        return gfunc, sfunc

    def group_by_all(self) -> Tuple[GroupFunc, Optional[SortFunc]]:
        return lambda _: None, None

    group_by_id_range = group_by_all

    def group_by_project(self) -> Tuple[GroupFunc, Optional[SortFunc]]:
        return self._group_by_value("project")

    def group_by_tag(self) -> Tuple[GroupFunc, Optional[SortFunc]]:
        gfunc = lambda todo: todo.tags if todo.tags else "_untagged"
        return gfunc, self.sort_tags

    def group_by_status(self) -> Tuple[GroupFunc, Optional[SortFunc]]:
        return self._group_by_value("status")

    def group_by_priority(self) -> Tuple[GroupFunc, Optional[SortFunc]]:
        return self._group_by_value("priority")

    def group_by_deadline(self) -> Tuple[GroupFunc, Optional[SortFunc]]:
        def gfunc(todo: TodoItem) -> GroupKey:
            dt = todo.deadline
            if dt is None or todo.status != "pending":
                return None
            delta = dt - datetime.now()
            if delta.seconds < 0:
                return "overdue"
            if delta.days < 1:
                return "today"
            return dt.date()
        sfunc = lambda todo: todo.deadline or datetime(9999, 12, 31)
        return gfunc, sfunc

    def group_by_created_at(self) -> Tuple[GroupFunc, Optional[SortFunc]]:
        def gfunc(todo: TodoItem) -> GroupKey:
            dt = todo.created_at
            delta = datetime.now() - dt
            if delta.days > 1:
                return dt.date()
            return "_today"
        sfunc = lambda todo: todo.created_at
        return gfunc, sfunc

    def group(
        self, todos: List[TodoItem], group_by: GroupBy,
    ) -> Dict[GroupKey, List[TodoItem]]:
        group_func, group_sort_func = getattr(self, f"group_by_{group_by}")()
        groups = {}
        orders: Dict[Any, Any] = {}
        for todo in todos:
            key_or_keys = group_func(todo)
            if group_sort_func:
                order = group_sort_func(todo)
            else:
                order = repr(key_or_keys)
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
