import copy
from datetime import datetime
from typing import Dict, List, Literal, Optional, Tuple, TypeVar, get_args

from box import Box
from dateutil.relativedelta import relativedelta

from ..common import logger
from .item import Priority, Status, TodoItem
from .result import AddResult, EditResult, QueryResult, ViewResult
from .select import (
    FilterBy,
    FilterMixin,
    FilterValue,
    GroupBy,
    GroupMixin,
    SortBy,
    SortMixin,
)

T = TypeVar("T")


class ActionError(Exception):
    pass


class ActionValueError(ActionError):
    """An exception raised when a value set operation fails."""


class TaskBook(FilterMixin, GroupMixin, SortMixin):
    todos: Dict[int, TodoItem]
    path: Optional[str]

    def __init__(
        self,
        config: Box,
        todos: Optional[List[TodoItem]] = None,
    ):
        super().__init__()
        self.config = config
        self.todos = {todo.id: todo for todo in (todos or [])}
        self._id_todo_map = None

    @property
    def next_id(self) -> int:
        return max(self.todos.keys(), default=0) + 1

    def append(self, todo: TodoItem) -> None:
        self.todos[todo.id] = todo

    def children_of(self, todo_id: int) -> List[TodoItem]:
        return [todo for todo in self.todos.values() if todo.parent == todo_id]

    def descendants_of(self, todo_id: int) -> List[TodoItem]:
        descendants = []
        seen = {todo_id}
        stack = self.children_of(todo_id)
        while stack:
            todo = stack.pop(0)
            if todo.id in seen:
                continue
            seen.add(todo.id)
            descendants.append(todo)
            stack[0:0] = self.children_of(todo.id)
        return descendants

    def _descendant_ids(self, todo_id: int) -> set[int]:
        return {todo.id for todo in self.descendants_of(todo_id)}

    def _normalize_parent_id(self, parent: Optional[int]) -> Optional[int]:
        return None if parent == 0 else parent

    def _validate_parent(
        self,
        todo: TodoItem,
        parent: Optional[int],
    ) -> Optional[int]:
        parent = self._normalize_parent_id(parent)
        if parent is None:
            return None
        if parent not in self.todos:
            raise ActionValueError(
                f"Cannot set parent to a non-existing todo with id {parent}."
            )
        if parent == todo.id:
            raise ActionValueError("Cannot set an item as its own parent.")
        if parent in self._descendant_ids(todo.id):
            raise ActionValueError("Cannot create a parent cycle.")
        return parent

    def _subtree(self, todos: List[TodoItem]) -> List[TodoItem]:
        selected: set[int] = set()
        for todo in todos:
            selected.add(todo.id)
            for descendant in self.descendants_of(todo.id):
                selected.add(descendant.id)
        return [todo for todo in self.todos.values() if todo.id in selected]

    def _resolve_parent_project(
        self,
        parent: Optional[int],
        project: Optional[str],
    ) -> str:
        parent = self._normalize_parent_id(parent)
        if parent is None:
            return project or self.config.item.project.default
        parent_project = self.todos[parent].project
        if project is not None and project != parent_project:
            raise ActionValueError(
                "Child project must match the parent project."
            )
        return parent_project

    def _extend_filtered_with_descendants(
        self, todos: List[TodoItem]
    ) -> List[TodoItem]:
        ids = {todo.id for todo in todos}
        expanded = list(todos)
        for todo in todos:
            for descendant in self.descendants_of(todo.id):
                if descendant.id not in ids:
                    ids.add(descendant.id)
                    expanded.append(descendant)
        return expanded

    def add(
        self,
        title: str,
        description: Optional[str] = None,
        project: Optional[str] = None,
        tags: Optional[List[str]] = None,
        status: Status = "pending",
        priority: Priority = "normal",
        parent: Optional[int] = None,
        deadline: Optional[datetime] = None,
    ) -> AddResult:
        if tags is None:
            tags = []
        todo = TodoItem(self.next_id, title)
        parent = self._validate_parent(todo, parent)
        todo.description = self.description(todo, description)
        project = self._resolve_parent_project(parent, project)
        todo.project = self.project(todo, project)
        if tags:
            todo.tags = self.tags(todo, tags)
        todo.status = self.status(todo, status)
        todo.priority = self.priority(todo, priority)
        todo.deadline = self.deadline(todo, deadline)
        todo.parent = parent
        self.append(todo)
        return AddResult([todo])

    def id(self, todo: TodoItem, id: int) -> int:
        return id

    def title(self, todo: TodoItem, title: str) -> str:
        return self._resolve_alias("title", title.strip())

    def description(
        self, todo: TodoItem, description: Optional[str]
    ) -> Optional[str]:
        if description:
            description = description.strip()
            if description:
                return self._resolve_alias("description", description)
        return None

    def status(self, todo: TodoItem, status: str) -> Status:
        if status:
            status = self._resolve_alias("status", status)
            if status not in get_args(Status):
                raise ActionValueError(f"Unrecognized status {status!r}.")
            return status
        status_changes: Dict[Status, Status] = {
            "done": "pending",
            "pending": "done",
        }
        try:
            return status_changes[todo.status]
        except KeyError as e:
            raise ActionValueError(
                f"Cannot toggle status of an item with status {todo.status!r}."
            ) from e

    def priority(self, todo: TodoItem, priority: Priority) -> Priority:
        new_priority = self._resolve_alias("priority", priority)
        if new_priority in get_args(Priority):
            return new_priority
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
            new_priority = None
        if not new_priority:
            raise ActionValueError(
                f"Cannot change priority from {todo.priority!r} to {priority!r}."
            )
        return new_priority

    def project(self, todo: TodoItem, project: str) -> str:
        return self._resolve_alias("project", project)

    def _update_list(
        self,
        alias_key: str,
        old_values: List[str],
        values: List[str],
    ) -> List[str]:
        new_values: List[str] = list(old_values)
        for value in values:
            value = self._resolve_alias(alias_key, value.strip())
            if value.startswith("+"):
                if value[1:] not in new_values:
                    new_values.append(value[1:])
            elif value.startswith("-"):
                if value[1:] in new_values:
                    new_values.remove(value[1:])
            elif value not in new_values:
                new_values.append(value)
            else:
                new_values.remove(value)
        return new_values

    def tags(self, todo: TodoItem, tags: List[str]) -> List[str]:
        return self._update_list("tag", todo.tags, tags)

    def parent(self, todo: TodoItem, id: Optional[int]) -> Optional[int]:
        return self._validate_parent(todo, id)

    def deadline(
        self, todo: TodoItem, deadline: Optional[datetime | relativedelta]
    ) -> Optional[datetime]:
        if not isinstance(deadline, relativedelta):
            return deadline
        base = todo.deadline or datetime.now()
        return base + deadline

    def select(
        self,
        filters: Optional[Dict[FilterBy, FilterValue]],
        group_by: GroupBy = "id",
        sort_by: SortBy = "id",
        include_descendants: bool = True,
    ) -> ViewResult:
        filtered_todos = list(self.todos.values())
        if filters is not None:
            filtered_todos = self.filter(filtered_todos, filters)
            if include_descendants and "parent" not in filters:
                filtered_todos = self._extend_filtered_with_descendants(
                    filtered_todos
                )
        gtodos = self.group_by(filtered_todos, group_by)
        for group, todos in gtodos.items():
            gtodos[group] = self.sort_by(todos, sort_by)
        is_all = len(filtered_todos) == len(self.todos)
        return ViewResult(gtodos, group_by, sort_by, is_all)

    def query(self, todos: List[TodoItem], query: List[str]) -> QueryResult:
        values = []
        for todo in todos:
            values.append([getattr(todo, key) for key in query])
        return QueryResult(query, values)

    def _update_and_return(
        self, before: List[TodoItem], after: List[TodoItem]
    ) -> EditResult:
        before_id_todos = {t.id: t for t in before}
        after_id_todos = {t.id: t for t in after}
        all_id_todos = {
            i: t for i, t in self.todos.items() if i not in before_id_todos
        }
        self.todos = all_id_todos | after_id_todos
        updates = []
        for b, a in zip(before, after):
            if b != a:
                updates.append((b, a))
        before, after = zip(*updates) if updates else ([], [])
        result = EditResult(before, after)
        logger.debug(f"Result: {result}")
        return result

    def action(
        self,
        todos: List[TodoItem],
        actions: Optional[Dict[str, Literal["editor"] | str | List[str]]],
    ) -> EditResult:
        if actions is None:
            return EditResult(todos, todos)

        selected = list(todos)
        if not selected:
            return EditResult([], [])
        selected_ids = {todo.id for todo in selected}
        status_deletes = False
        if actions.get("status"):
            status_deletes = (
                self._resolve_alias("status", actions["status"]) == "delete"
            )
        parent = self._normalize_parent_id(actions.get("parent"))
        needs_subtree = status_deletes or "project" in actions
        needs_subtree = needs_subtree or parent is not None
        before = self._subtree(selected) if needs_subtree else selected
        after = copy.deepcopy(before)
        after_by_id = {todo.id: todo for todo in after}

        if "project" in actions:
            clears_parent = actions.get("parent") == 0
            for todo in selected:
                if todo.parent is not None and not clears_parent:
                    raise ActionValueError(
                        "Cannot edit the project of a child item directly."
                    )

        if parent is not None and "project" in actions:
            project = self.project(selected[0], actions["project"])
            if project != self.todos[parent].project:
                raise ActionValueError(
                    "Child project must match the parent project."
                )

        if "parent" in actions:
            for todo in selected:
                new_parent = self.parent(todo, actions["parent"])
                after_by_id[todo.id].parent = new_parent
            if parent is not None:
                inherited_project = self.todos[parent].project
                for todo in after:
                    todo.project = inherited_project

        if "project" in actions and parent is None:
            project = self.project(selected[0], actions["project"])
            for todo in after:
                todo.project = project

        if "status" in actions:
            if status_deletes:
                for todo in after:
                    todo.status = "delete"
            else:
                for todo_id in selected_ids:
                    todo = after_by_id[todo_id]
                    todo.status = self.status(todo, actions["status"])

        for action, value in actions.items():
            if action in ["parent", "project", "status"]:
                continue
            for todo_id in selected_ids:
                todo = after_by_id[todo_id]
                value = getattr(self, action)(todo, value)
                logger.debug(
                    f"Setting {action!r} to {value!r} for {todo.id}."
                )
                setattr(todo, action, value)
        return self._update_and_return(before, after)

    def re_index(self) -> EditResult:
        before = copy.deepcopy(list(self.todos.values()))
        for i, todo in enumerate(self.todos.values()):
            todo.id = self.id(todo, i + 1)
        updates = [(b, a) for b, a in zip(before, self.todos) if b != a]
        if not updates:
            result = EditResult([], [])
        else:
            before, after = zip(*updates)
            result = EditResult(before, after)
        logger.debug(f"Result: {result}")
        return result
