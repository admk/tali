import re
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
from typing import (
    get_args, Optional, Sequence, List, Dict, Tuple, Callable, Literal, Any)

from box import Box

from ..common import logger, has_prefix
from ..book.item import TodoItem, Status, Priority


FilterBy = Literal[
    "title", "project", "tag", "status", "priority", "deadline", "created_at"]
ActBy = Literal["add", "delete"] | FilterBy
GroupBy = Literal[
    "id", "project", "tag", "status", "priority", "deadline", "created_at"]
SortBy = Literal[
    "id", "status", "title", "project", "tags", "priority",
    "deadline", "created_at"]
FilterValue = str | Tuple[datetime, datetime]
GroupKey = Optional[str | datetime | date]
GroupFunc = Callable[[TodoItem], GroupKey]
SortFunc = Callable[[TodoItem], Any]


class SelectError(Exception):
    pass


class FilterError(SelectError):
    """An exception raised when a filter operation fails."""


class SortError(SelectError):
    """An exception raised when a sort operation fails."""


class GroupError(SelectError):
    """An exception raised when a group operation fails."""


class SelectMixin:
    config: Box


class FilterMixin(SelectMixin):
    def _resolve_alias(self, key: str, value: str) -> str:
        for k, v in self.config.item[key].get("alias", {}).items():
            value = re.sub(k, v, value)
        return value

    def filter_by_ids(self, todos, ids: List[int]) -> bool:
        return todos.id in ids

    def filter_by_title(self, todos, title: str) -> bool:
        return title.lower() in todos.title.lower()

    def filter_by_project(self, todos, project: str) -> bool:
        separator = self.config.token.project
        splits = project.split(separator)
        todo_splits = todos.project.split(separator)
        return has_prefix(todo_splits, splits)

    def filter_by_tags(self, todo: TodoItem, tags: List[str]) -> bool:
        return all(t in todo.tags for t in tags) if tags else not todo.tags

    def filter_by_status(self, todo: TodoItem, status: Status) -> bool:
        new_status = self._resolve_alias('status', status)
        if new_status not in get_args(Status):
            raise FilterError(f"Unrecognized status {status!r}.")
        return todo.status == new_status

    def filter_by_priority(self, todo: TodoItem, priority: Priority) -> bool:
        return todo.priority == priority

    def _filter_by_date_range(
        self, date: datetime, date_range: Sequence[datetime | relativedelta]
    ) -> bool:
        from_date, to_date = date_range
        if isinstance(from_date, relativedelta):
            from_date = datetime.now() + from_date
        if isinstance(to_date, relativedelta):
            to_date = datetime.now() + to_date
        if from_date > to_date:
            from_date, to_date = to_date, from_date
        return from_date <= date <= to_date

    def filter_by_deadline(
        self, todo: TodoItem, date_range: Sequence[datetime]
    ) -> bool:
        if todo.deadline is None:
            return False
        if len(date_range) == 1:
            date_range = (datetime.min, date_range[0])
        if len(date_range) != 2:
            raise FilterError(f'Invalid date range: {date_range!r}.')
        return self._filter_by_date_range(todo.deadline, date_range)

    def filter_by_created_at(
        self, todo: TodoItem, date_range: Sequence[datetime]
    ) -> bool:
        return self._filter_by_date_range(todo.created_at, date_range)

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
    def sort_by_id(self, todo: TodoItem) -> int:
        return todo.id

    def sort_by_status(self, todo: TodoItem) -> int:
        return list(self.config.group.header.status).index(todo.status)

    def sort_by_title(self, todo: TodoItem) -> str:
        return todo.title

    def sort_by_project(self, todo: TodoItem) -> str:
        return todo.project

    def sort_by_tags(self, todo: TodoItem) -> Tuple[str, ...]:
        return tuple(sorted(todo.tags))

    def sort_by_priority(self, todo: TodoItem) -> int:
        return list(self.config.group.header.priority).index(todo.priority)

    def sort_by_deadline(self, todo: TodoItem) -> datetime:
        return todo.deadline or datetime(9999, 12, 31)

    def sort_by_created_at(self, todo: TodoItem) -> datetime:
        return todo.created_at

    def sort_by(
        self, todos: List[TodoItem], mode: SortBy,
    ) -> List[TodoItem]:
        return sorted(todos, key=getattr(self, f"sort_by_{mode}"))


class GroupMixin(SortMixin):
    def _group_by_value(
        self, name: str
    ) -> Tuple[GroupFunc, Optional[SortFunc]]:
        gfunc = lambda todo: getattr(todo, name)
        sfunc = getattr(self, f"sort_by_{name}")
        return gfunc, sfunc

    def group_by_all(self) -> Tuple[GroupFunc, Optional[SortFunc]]:
        return lambda _: None, None

    group_by_id = group_by_all

    def group_by_project(self) -> Tuple[GroupFunc, Optional[SortFunc]]:
        return self._group_by_value("project")

    def group_by_tag(self) -> Tuple[GroupFunc, Optional[SortFunc]]:
        gfunc = lambda todo: todo.tags if todo.tags else "_untagged"
        return gfunc, self.sort_by_tags

    def group_by_status(self) -> Tuple[GroupFunc, Optional[SortFunc]]:
        return self._group_by_value("status")

    def group_by_priority(self) -> Tuple[GroupFunc, Optional[SortFunc]]:
        return self._group_by_value("priority")

    def group_by_deadline(self) -> Tuple[GroupFunc, Optional[SortFunc]]:
        def gfunc(todo: TodoItem) -> GroupKey:
            dt = todo.deadline
            if dt is None or todo.status != "pending":
                return None
            delta = (dt - datetime.now()).total_seconds()
            if delta < 0:
                return "overdue"
            if delta < 86400:  # 1 day in seconds
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

    def group_by_description(self):
        raise GroupError("Grouping by description is not supported.")

    def group_by(
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
