import os
import copy
import json
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple

from .item import TodoItem, Status, Priority
from .select import (
    FilterMixin, GroupMixin, SortMixin, FilterBy, FilterValue, GroupBy, SortBy)


class TaskBook(FilterMixin, GroupMixin, SortMixin):
    todos: List[TodoItem]
    path: Optional[str]

    def __init__(
        self, todos: Optional[List[TodoItem]] = None,
        path: Optional[str] = None
    ):
        super().__init__()
        self.path = path
        if todos is None and path is not None:
            if os.path.exists(path):
                with open(path, "r") as f:
                    todos = [TodoItem.from_dict(todo) for todo in json.load(f)]
        self.todos = todos or []
        self.next_id = max([todo.id for todo in self.todos], default=0) + 1

    def save(self, path: str | None = None):
        if path is None and self.path is None:
            raise ValueError("No path specified for saving.")
        real_path: str = path or self.path  # type: ignore
        folder = os.path.dirname(real_path)
        if folder:
            os.makedirs(folder, exist_ok=True)
        with open(real_path, "w") as f:
            data = [todo.to_dict() for todo in self.todos]
            json.dump(data, f, indent=4)

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

    def delete(self, todo: int | TodoItem) -> TodoItem:
        todo_id = todo if isinstance(todo, int) else todo.id
        # find the todo item, and pop it from the list
        for i, t in enumerate(self.todos):
            if t.id == todo_id:
                item = self.todos.pop(i)
                return item
        raise ValueError("Todo item not found.")

    def title(self, todo: TodoItem, title: str) -> str:
        return title

    def status(self, todo: TodoItem, status: str) -> Status:
        new_status: Optional[Status] = None
        if status:
            status_map: Dict[str, Status] = {
                "p": "pending", "pending": "pending",
                "n": "note", "note": "note",
                "d": "done", "done": "done",
            }
            new_status = status_map[status]
        elif todo.status == "done":
            new_status = "pending"
        elif todo.status == "pending":
            new_status = "done"
        elif todo.status == "note":
            raise ValueError("Cannot toggle status of a note.")
        if new_status is None:
            raise ValueError(f"Unrecognized status {status!r}.")
        return new_status

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
            raise ValueError(f"Unrecognized priority {priority!r}.")
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
        group_by: GroupBy = "all", sort_by: SortBy = "id",
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
        todos = copy.deepcopy(todos)
        for todo in todos:
            for action, value in actions.items():
                value = getattr(self, action)(todo, value)
                setattr(todo, action, value)
        return todos
