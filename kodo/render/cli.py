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

    def _render_id(self, id: int, color: bool = True) -> Optional[str]:
        text = f"{id:>4}"
        if not color:
            return text
        return colored(text, **constants.ID_ATTRS)

    def _render_status(
        self, status: Status, header: bool = False, color: bool = True
    ) -> Optional[str]:
        if header:
            symbol = constants.STATUS_FORMATTED[status]
        else:
            symbol = constants.STATUS_SYMBOLS[status]
        if not color:
            return symbol
        return colored(symbol, **constants.STATUS_ATTRS[status])

    def _render_title(
        self, todo: TodoItem, color: bool = True
    ) -> Optional[str]:
        title = shorten(todo.title, constants.MAX_TITLE_LENGTH)
        attrs = {}
        for k, v in constants.TITLE_ATTRS.items():
            p, q = k.split(".")
            if getattr(todo, p) == q:
                attrs |= v
        if not color:
            return title
        return colored(title, **attrs)

    def _render_tags(
        self, tags: List[str], color: bool = True
    ) -> Optional[str]:
        new_tags = []
        for tag in tags:
            key = tag if tag in constants.TAG_SYMBOLS else "_default"
            default_tag = f"{constants.TOKENS['tag']}{tag}"
            text = constants.TAG_SYMBOLS.get(key, default_tag)
            if color:
                text = colored(text, **constants.TAG_ATTRS[key])
            new_tags.append(text)
        return " ".join([tag for tag in new_tags])

    def _render_project(
        self, project: str, color: bool = True
    ) -> Optional[str]:
        text = f"{constants.TOKENS['project']}{project}"
        if not color:
            return text
        return colored(text, **constants.PROJECT_ATTRS)  # type: ignore

    def _render_priority(
        self, priority: Priority, header: bool = False, color: bool = True
    ) -> Optional[str]:
        if header:
            symbol = constants.PRIORITY_FORMATTED[priority]
        else:
            symbol = constants.PRIORITY_SYMBOLS[priority] or ""
        if not symbol:
            return None
        if not color:
            return symbol
        return colored(symbol, **constants.PRIORITY_ATTRS[priority])

    def _render_deadline(
        self, deadline: Optional[datetime], status: Status, color: bool = True
    ) -> Optional[str]:
        if deadline is None:
            return None
        return format_datetime(deadline, status, use_color=color)

    def _render_created_at(
        self, created_at: datetime, color: bool = True
    ) -> Optional[str]:
        return format_datetime(
            created_at, "pending", "created_at", use_color=color)

    def _render_description(
        self, description: Optional[str], color: bool = True
    ) -> Optional[str]:
        if description is None:
            return None
        desc = shorten(description, constants.MAX_DESCRIPTION_LENGTH)
        if not color:
            return desc
        return colored(desc, **constants.DESCRIPTION_ATTRS)

    def _render_header(
        self, group_by: GroupBy, value: Any, color: bool = True
    ) -> str | None:
        if group_by == "all":
            return None
        if group_by == "project":
            return self._render_project(value, color)
        if group_by == "tag":
            return self._render_tags([value], color)
        if group_by == "priority":
            return self._render_priority(value, True, color)
        if group_by == "status":
            return self._render_status(value, True, color)
        if group_by == "deadline":
            return self._render_deadline(value, "pending", color)
        if group_by == "created_at":
            return self._render_created_at(value, color)
        raise ValueError(f"Unknown group_by: {group_by}")

    def _render_fields(
        self, todo: TodoItem, color: bool = True
    ) -> Dict[str, str]:
        fields = {
            "id": self._render_id(todo.id, color),
            "status": self._render_status(todo.status, color=color),
            "title": self._render_title(todo, color),
            "tags": self._render_tags(todo.tags, color),
            "priority": self._render_priority(todo.priority, color=color),
            "project": self._render_project(todo.project, color),
            "deadline": self._render_deadline(
                todo.deadline, todo.status, color),
            "description": self._render_description(todo.description, color),
        }
        return {k: " " + v if v else "" for k, v in fields.items()}

    def render_item(
        self, todo: TodoItem, group_by: GroupBy = "all", color: bool = True
    ) -> str:
        fields = self._render_fields(todo, color)
        return constants.FORMAT[group_by].format(**fields)[1:]

    def render_item_diff(
        self, before_todo: TodoItem, after_todo: TodoItem, color: bool = True
    ) -> str:
        before_fields = self._render_fields(before_todo, False)
        after_fields = self._render_fields(after_todo, False)
        after_fields_colored = self._render_fields(after_todo, True)
        fields = {}
        for k, v in before_fields.items():
            if v == after_fields[k]:
                fields[k] = after_fields_colored[k]
            else:
                bv = before_fields[k].lstrip()
                bv = colored(bv, color="grey", attrs=["strike"])
                lb, arrow, rb = (
                    colored(t, color="red", attrs=["bold"]) for t in "{→}")
                av = after_fields_colored[k].lstrip()
                fields[k] = f" {lb}{bv} {arrow} {av}{rb}"
        return constants.FORMAT["all"].format(**fields)[1:]

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
