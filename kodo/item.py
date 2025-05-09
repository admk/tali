from typing import Optional, List, Literal
from datetime import datetime


Status = Literal["pending", "done", "note"]
Priority = Literal["high", "normal", "low"]


class TodoItem:
    def __init__(
        self, id: int, title: str, description: Optional[str] = None,
        project: str = "Uncategorized", tags: Optional[List[str]] = None,
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

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "project": self.project,
            "tags": self.tags,
            "deadline": self.deadline,
            "status": self.status,
            "priority": self.priority,
            "created_at": self.created_at,
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
            deadline=data["deadline"],
            created_at=data["created_at"],
        )
