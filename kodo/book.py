import os
import json
from datetime import datetime, timedelta
from typing import List, Optional

from .item import TodoItem, Status, Priority


class TaskBook:
    modified: bool = False
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
        if not self.modified:
            return
        if path is None and self.path is None:
            raise ValueError("No path specified for saving.")
        real_path: str = path or self.path  # type: ignore
        os.makedirs(os.path.dirname(real_path), exist_ok=True)
        with open(real_path, "w") as f:
            data = [todo.to_dict() for todo in self.todos]
            json.dump(data, f, indent=4)

    def add(
        self, title: str, description: Optional[str] = None,
        project: str = "Inbox", tags: Optional[List[str]] = None,
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
        self.modified = True
        return todo

    def delete(self, todo: int | TodoItem) -> TodoItem:
        todo_id = todo if isinstance(todo, int) else todo.id
        # find the todo item, and pop it from the list
        for i, t in enumerate(self.todos):
            if t.id == todo_id:
                item = self.todos.pop(i)
                self.modified = True
                return item
        raise ValueError("Todo item not found.")

    def defer(self, todo: int | TodoItem, days: Optional[int] = 1):
        todo_id = todo if isinstance(todo, int) else todo.id
        for todo in self.todos:
            if todo.id != todo_id:
                continue
            if days is None:
                todo.deadline = None
            else:
                deadline = todo.deadline or datetime.now()
                todo.deadline = deadline + timedelta(days=days)
            self.modified = True
            return todo
        raise ValueError("Todo item not found.")

    def mark(self, todo: int | TodoItem, status: Status = "done") -> TodoItem:
        todo_id = todo if isinstance(todo, int) else todo.id
        for todo in self.todos:
            if todo.id != todo_id:
                continue
            todo.status = status
            self.modified = True
            return todo
        raise ValueError("Todo item not found.")

    def note(self, todo: int | TodoItem) -> TodoItem:
        return self.mark(todo, "note")

    def pending(self, todo: int | TodoItem) -> TodoItem:
        return self.mark(todo, "pending")

    def done(self, todo: int | TodoItem) -> TodoItem:
        return self.mark(todo, "done")

    def star(self, todo: int | TodoItem) -> TodoItem:
        todo_id = todo if isinstance(todo, int) else todo.id
        for todo in self.todos:
            if todo.id != todo_id:
                continue
            if "star" in todo.tags:
                raise ValueError("Todo item already starred.")
            todo.tags.append("star")
            self.modified = True
            return todo
        raise ValueError("Todo item not found.")

    def unstar(self, todo: int | TodoItem) -> TodoItem:
        todo_id = todo if isinstance(todo, int) else todo.id
        for todo in self.todos:
            if todo.id != todo_id:
                continue
            if "star" not in todo.tags:
                raise ValueError("Todo item not starred.")
            todo.tags.remove("star")
            self.modified = True
            return todo
        raise ValueError("Todo item not found.")
