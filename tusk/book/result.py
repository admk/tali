from datetime import datetime
from dataclasses import dataclass
from typing import List, Dict, Literal

from ..common import flatten
from .item import TodoItem
from .select import GroupBy, SortBy, GroupKey


@dataclass
class ActionResult:
    @classmethod
    def _todos_to_list(cls, todos: List[TodoItem]) -> List[dict]:
        return [todo.to_dict() for todo in todos]

    @classmethod
    def _todos_from_list(cls, todos: List[dict]) -> List[TodoItem]:
        return [TodoItem.from_dict(todo) for todo in todos]

    def to_dict(self) -> dict:
        raise NotImplementedError

    @classmethod
    def from_dict(cls, data: dict) -> "ActionResult":
        class_name = data.pop("type")
        class_map = {
            "ViewResult": ViewResult,
            "AddResult": AddResult,
            "EditResult": EditResult,
            "HistoryResult": HistoryResult,
            "SwitchResult": SwitchResult,
        }
        return class_map[class_name].from_dict(data)


@dataclass
class Commit:
    message: str
    hexsha: str
    timestamp: datetime
    is_head: bool
    action_results: List[ActionResult]

    def to_dict(self) -> dict:
        return {
            "message": self.message,
            "hexsha": self.hexsha,
            "timestamp": self.timestamp.isoformat(),
            "is_head": self.is_head,
            "action_results": [ar.to_dict() for ar in self.action_results],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Commit":
        return cls(
            data["message"], data["hexsha"],
            datetime.fromisoformat(data["timestamp"]), data["is_head"],
            [ActionResult.from_dict(ar) for ar in data["action_results"]])


@dataclass
class ViewResult(ActionResult):
    grouped_todos: Dict[GroupKey, List[TodoItem]]
    group_by: GroupBy
    sort_by: SortBy
    is_all: bool

    def flatten(self) -> List[TodoItem]:
        return flatten(list(self.grouped_todos.values()))

    def to_dict(self) -> dict:
        return {
            "type": "ViewResult",
            "grouped_todos": {
                group: self._todos_to_list(todos)
                for group, todos in self.grouped_todos.items()
            },
            "group_by": self.group_by,
            "sort_by": self.sort_by,
            "is_all": self.is_all,
        }


@dataclass
class QueryResult(ActionResult):
    keys: List[str]
    values: List[List[str | datetime]]

    def to_dict(self) -> dict:
        return {
            "keys": self.keys,
            "values": [
                v.isoformat() if isinstance(v, datetime) else v
                for v in self.values],
        }


class RequiresSave:
    pass


@dataclass
class AddResult(ActionResult, RequiresSave):
    items: List[TodoItem]

    def to_dict(self) -> dict:
        return {
            "type": "AddResult",
            "items": self._todos_to_list(self.items),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "AddResult":
        return cls(cls._todos_from_list(data["items"]))


@dataclass
class EditResult(ActionResult, RequiresSave):
    before: List[TodoItem]
    after: List[TodoItem]

    def to_dict(self) -> dict:
        return {
            "type": "EditResult",
            "before": self._todos_to_list(self.before),
            "after": self._todos_to_list(self.after),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "EditResult":
        before = cls._todos_from_list(data["before"])
        after = cls._todos_from_list(data["after"])
        return cls(before, after)


@dataclass
class HistoryResult(ActionResult):
    history: List[Commit]

    def to_dict(self) -> dict:
        return {
            "type": "HistoryResult",
            "history": [h.to_dict() for h in self.history],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "HistoryResult":
        return cls([Commit(**h) for h in data["history"]])


SwitchAction = Literal["undo", "redo"]


@dataclass
class SwitchResult(ActionResult):
    action: SwitchAction
    message: str
    action_results: List[ActionResult]

    def to_dict(self) -> dict:
        return {
            "type": "SwitchResult",
            "action": self.action,
            "message": self.message,
            "action_results": [ar.to_dict() for ar in self.action_results],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SwitchResult":
        results = [ActionResult.from_dict(ar) for ar in data["action_results"]]
        return cls(data["action"], data["message"], results)
