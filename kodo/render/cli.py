import operator
import functools
from datetime import datetime
from typing import Optional, List, Dict, Any

from termcolor import colored

from .. import constants
from ..book.item import TodoItem, Status, Priority
from ..book.select import GroupBy
from .utils import shorten, format_datetime


class Renderer:
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

    def _render_id(self, id: int) -> Optional[str]:
        return colored(str(id), **constants.ID_ATTRS)

    def _render_status(
        self, status: Status, header: bool = False
    ) -> Optional[str]:
        if header:
            symbol = constants.STATUS_FORMATTED[status]
        else:
            symbol = constants.STATUS_SYMBOLS[status]
        return colored(symbol, **constants.STATUS_ATTRS[status])

    def _render_title(self, todo: TodoItem) -> Optional[str]:
        title = shorten(todo.title, constants.MAX_TITLE_LENGTH)
        attrs = {}
        for k, v in constants.TITLE_ATTRS.items():
            p, q = k.split(".")
            if getattr(todo, p) == q:
                attrs |= v
        return colored(title, **attrs)

    def _render_tags(self, tags: List[str]) -> Optional[str]:
        new_tags = []
        for tag in tags:
            key = tag if tag in constants.TAG_SYMBOLS else "_default"
            default_tag = f"{constants.TOKENS['tag']}{tag}"
            new_tags.append(colored(
                constants.TAG_SYMBOLS.get(key, default_tag),
                **constants.TAG_ATTRS[key]))
        return " ".join([tag for tag in new_tags])

    def _render_project(self, project: str) -> Optional[str]:
        return colored(
            f"{constants.TOKENS['project']}{project}",
            **constants.PROJECT_ATTRS)  # type: ignore

    def _render_priority(
        self, priority: Priority, header: bool = False
    ) -> Optional[str]:
        if header:
            symbol = constants.PRIORITY_FORMATTED[priority]
        else:
            symbol = constants.PRIORITY_SYMBOLS[priority] or ""
        if not symbol:
            return None
        return colored(symbol, **constants.PRIORITY_ATTRS[priority])

    def _render_deadline(
        self, deadline: Optional[datetime], status: Status,
    ) -> Optional[str]:
        if deadline is None:
            return None
        return format_datetime(deadline, status)  # type: ignore

    def _render_created_at(self, created_at: datetime) -> Optional[str]:
        return format_datetime(
            created_at, todo.status,  # type: ignore
            "created_at", use_color=False)

    def _render_description(self, description: Optional[str]) -> Optional[str]:
        if description is None:
            return None
        desc = shorten(description, constants.MAX_DESCRIPTION_LENGTH)
        return colored(desc, **constants.DESCRIPTION_ATTRS)

    def _render_header(self, group_by: GroupBy, value: Any) -> str | None:
        if group_by == "all":
            return None
        if group_by == "project":
            return self._render_project(value)
        if group_by == "tag":
            return self._render_tags([value])
        if group_by == "priority":
            return self._render_priority(value, header=True)
        if group_by == "status":
            return self._render_status(value, header=True)
        if group_by == "deadline":
            return self._render_deadline(value, "pending")
        if group_by == "created_at":
            return self._render_created_at(value)
        raise ValueError(f"Unknown group_by: {group_by}")

    def render_item(self, todo: TodoItem, group_by: GroupBy) -> str:
        fields = {
            "id": self._render_id(todo.id),
            "status": self._render_status(todo.status),
            "title": self._render_title(todo),
            "tags": self._render_tags(todo.tags),
            "priority": self._render_priority(todo.priority),
            "project": self._render_project(todo.project),
            "deadline": self._render_deadline(todo.deadline, todo.status),
            "description": self._render_description(todo.description),
        }
        fields = {k: " " + v if v else "" for k, v in fields.items()}
        return constants.FORMAT[group_by].format(**fields)

    def render(
        self, grouped_todos: Dict[Any, List[TodoItem]],
        group_by: GroupBy, render_stats: bool = True
    ) -> str:
        text = []
        if not grouped_todos:
            text.append("\n  Nothing to show.")
        for group, gtodos in grouped_todos.items():
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
                group = self._render_header(group_by, group)
                group = colored(group, **constants.GROUP_ATTRS)  # type: ignore
                text.append(f"  {group} {progress}")
            for todo in gtodos:
                item = f"  {self.render_item(todo, group_by)}"
                text.append(item)
        if render_stats:
            all_todos = functools.reduce(operator.add, grouped_todos.values())
            text.append(self.render_stats(all_todos))
        return "\n".join(text)


if __name__ == "__main__":
    from ..book import TaskBook
    book = TaskBook(path="book.json")
    print(Renderer().render(book.group(book.todos, "priority"), "priority"))
