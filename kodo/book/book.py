import copy
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple

from box import Box

from ..common import warn
from .item import TodoItem, Status, Priority
from .select import (
    FilterMixin, GroupMixin, SortMixin, FilterBy, FilterValue, GroupBy, SortBy)


class TaskBook(FilterMixin, GroupMixin, SortMixin):
    todos: List[TodoItem]
    path: Optional[str]

    def __init__(
        self, config: Box, todos: Optional[List[TodoItem]] = None,
    ):
        super().__init__()
        self.config = config
        self.todos = todos or []
        self.next_id = max([todo.id for todo in self.todos], default=0) + 1

    def add(
        self, title: str, description: Optional[str] = None,
        project: str = "inbox", tags: Optional[List[str]] = None,
        status: Status = "pending", priority: Priority = "normal",
        deadline: Optional[datetime] = None,
        created_at: Optional[datetime] = None,
    ) -> TodoItem:
        if tags is None:
            tags = []
        todo = TodoItem(
            self.next_id, title, description, project, tags,
            status, priority, deadline, created_at)
        self.todos.append(todo)
        self.next_id += 1
        return todo

    def title(self, todo: TodoItem, title: str) -> str:
        return title

    def status(self, todo: TodoItem, status: str) -> Status:
        if status:
            status_map: Dict[str, Status] = {
                "p": "pending", "pending": "pending",
                "n": "note", "note": "note",
                "d": "done", "done": "done",
                "x": "delete", "delete": "delete",
            }
            try:
                return status_map[status]
            except KeyError:
                raise ValueError(f"Unrecognized status {status!r}.")
        if todo.status == "note":
            raise ValueError("Cannot toggle status of a note.")
        status_changes: Dict[Status, Status] = {
            "done": "pending",
            "pending": "done",
        }
        try:
            return status_changes[todo.status]
        except KeyError:
            raise ValueError(f"Unrecognized status {status!r}.")

    def priority(self, todo: TodoItem, priority: Priority):
        new_priority: Optional[Priority] = None
        priority_map: Dict[str, Priority] = {
            "h": "high", "high": "high",
            "n": "normal", "normal": "normal",
            "l": "low", "low": "low",
        }
        try:
            new_priority = priority_map[priority]
        except KeyError:
            pass
        priority_changes: Dict[Tuple[str, Priority], Priority] = {
            ("", "high"): "normal",
            ("", "normal"): "high",
            ("", "low"): "normal",
            ("+", "high"): "high",
            ("+", "normal"): "high",
            ("+", "low"): "normal",
            ("-", "high"): "normal",
            ("-", "normal"): "low",
            ("-", "low"): "low",
        }
        try:
            new_priority = priority_changes[priority, todo.priority]
        except KeyError:
            pass
        if not new_priority:
            raise ValueError(
                "Cannot change priority from "
                f"{todo.priority!r} to {priority!r}.")
        return new_priority

    def project(self, todo: TodoItem, project: str) -> str:
        return project

    def tags(self, todo: TodoItem, tags: str) -> List[str]:
        new_tags: List[str] = list(todo.tags)
        for tag in tags:
            if tag.startswith("+"):
                if tag[1:] not in new_tags:
                    new_tags.append(tag[1:])
            elif tag.startswith("-"):
                if tag[1:] in new_tags:
                    new_tags.remove(tag[1:])
            elif tag not in new_tags:
                new_tags.append(tag)
            else:
                new_tags.remove(tag)
        return new_tags

    def deadline(
        self, todo: TodoItem, deadline: Optional[datetime]
    ) -> Optional[datetime]:
        return deadline

    def select(
        self, filters: Optional[Dict[FilterBy, FilterValue]],
        group_by: GroupBy = "range", sort_by: SortBy = "range",
    ) -> Dict[Any, List[TodoItem]]:
        todos = self.todos
        if filters is not None:
            todos = self.filter(todos, filters)
        gtodos = self.group(todos, group_by)
        for group, todos in gtodos.items():
            gtodos[group] = self.sort(todos, sort_by)
        return gtodos

    def action(
        self, todos: List[TodoItem],
        actions: Optional[Dict[str, str | List[str]]],
    ) -> List[TodoItem]:
        if actions is None:
            return todos
        id_todos = {t.id: t for t in todos}
        new_id_todos = {}
        for id, todo in copy.deepcopy(id_todos).items():
            for action, value in actions.items():
                try:
                    value = getattr(self, action)(todo, value)
                except ValueError as e:
                    warn(e)
                else:
                    setattr(todo, action, value)
            if todo != id_todos[id]:
                new_id_todos[id] = todo
        all_todos = {t.id: t for t in self.todos} | new_id_todos
        self.todos = list(sorted(all_todos.values(), key=lambda t: t.id))
        return list(sorted(new_id_todos.values(), key=lambda t: t.id))
