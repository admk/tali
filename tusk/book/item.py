from dataclasses import dataclass
from typing import Optional, List, Literal
from datetime import datetime


Status = Literal["pending", "done", "note", "delete", "archive"]
Priority = Literal["high", "normal", "low"]


@dataclass
class TodoItem:
    id: int
    title: str
    project: str
    tags: List[str]
    status: Status
    priority: Priority
    deadline: Optional[datetime]
    created_at: datetime
    _keys = [
        "id", "title", "description", "project", "tags",
        "status", "priority", "deadline", "created_at"]

    def __init__(
        self, id: int, title: str, description: Optional[str] = None,
        project: str = "inbox", tags: Optional[List[str]] = None,
        status: Status = "pending", priority: Priority = "normal",
        deadline: Optional[datetime] = None,
        created_at: Optional[datetime] = None,
    ):
        self.id = id
        self.title = title
        self.description = description
        self.project = project
        self.tags = tags or []
        self.deadline = deadline
        self.status = status
        self.priority = priority
        self.created_at = created_at or datetime.now()

    def __repr__(self):
        attrs = " ".join(f"{k}={v}" for k, v in self.to_dict().items())
        return f"<{self.__class__.__name__} {attrs}>"

    @staticmethod
    def _datetime_to_str(dt: Optional[datetime]) -> Optional[str]:
        return f"{dt:%Y-%m-%dT%H:%M:%S}" if dt else None

    @staticmethod
    def _str_to_datetime(dt_str: Optional[str]) -> Optional[datetime]:
        return datetime.strptime(dt_str, "%Y-%m-%dT%H:%M:%S") if dt_str else None

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "project": self.project,
            "tags": self.tags,
            "status": self.status,
            "priority": self.priority,
            "deadline": self._datetime_to_str(self.deadline),
            "created_at": self._datetime_to_str(self.created_at),
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            id=data["id"],
            title=data["title"],
            description=data["description"],
            project=data["project"],
            tags=data["tags"],
            status=data["status"],
            priority=data["priority"],
            deadline=cls._str_to_datetime(data["deadline"]),
            created_at=cls._str_to_datetime(data["created_at"]),
        )
