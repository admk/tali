import operator
import functools
from datetime import date, datetime
from typing import get_args, Optional, Any, List, Dict, Literal

from box import Box
from rich.panel import Panel
from rich.console import RenderableType, Group
from rich.box import SIMPLE_HEAVY
from rich.table import Table

from ..common import strip_rich
from ..book.item import TodoItem, Status, Priority
from ..book.select import GroupBy
from ..book.result import (
    ActionResult, ViewResult, QueryResult, AddResult, EditResult,
    HistoryResult, SwitchResult)
from .utils import shorten, timedelta_format, pluralize


RenderStats = Literal[True, False, "all"]


class Renderer:
    def __init__(self, config: Box):
        super().__init__()
        self.config = config

    def _get_stats(self, todos: List[TodoItem]):
        stats = {}
        for status in get_args(Status):
            if status == "delete":
                continue
            stats[status] = len([t for t in todos if t.status == status])
        total = stats["done"] + stats["pending"]
        progress = stats["done"] / total if total > 0 else None
        return stats | {"progress": progress}

    def render_stats(self, todos: List[TodoItem]) -> str:
        stats = self._get_stats(todos)
        text = []
        progress = stats["progress"]
        if progress is not None:
            progress_str = f"{stats['progress']:.0%}"
            progress_map = self.config.stats.progress
            progress_format = progress_map._
            for k, v in progress_map.items():
                if isinstance(k, int) and progress * 100 <= k:
                    progress_format = v
            progress_str = progress_format.format(progress_str)
            text.append(self.config.stats.title.format(progress_str))
        stats_text = []
        for key, value in self.config.stats.status.items():
            stats_text.append(value.format(stats[key]))
        text.append(self.config.stats.separator.join(stats_text))
        return "\n".join(text)

    def _render_id(self, id: int) -> Optional[str]:
        return self.config.item.id.format.format(id)

    def _render_status(
        self, status: Status, header: bool = False
    ) -> Optional[str]:
        if header:
            return self.config.group.header.status[status]
        return self.config.item.status.format[status]

    def _render_title(self, todo: TodoItem) -> Optional[str]:
        title = todo.title
        for token in self.config.token.values():
            title = title.replace(f'\\{token}', token)
        title = shorten(title, self.config.item.title.max_length)
        for k, v in self.config.item.title.format.items():
            p, q = k.split("_")
            if getattr(todo, p) == q:
                return v.format(title)
        return title

    def _render_tags(self, tags: List[str]) -> Optional[str]:
        new_tags = []
        tag_formats = self.config.item.tag.format
        for tag in tags:
            key = tag if tag in tag_formats else "_"
            text = tag_formats[key].format(tag)
            new_tags.append(text)
        return " ".join([tag for tag in new_tags])

    def _render_project(self, project: str) -> Optional[str]:
        return f"{self.config.token.project}{project}"

    def _render_priority(
        self, priority: Priority, header: bool = False
    ) -> Optional[str]:
        if header:
            return self.config.group.header.priority[priority]
        return self.config.item.priority.format[priority]

    def _render_deadline(
        self, deadline: Optional[date | datetime], status: Status,
        header: bool = False
    ) -> Optional[str]:
        prefix = self.config.token.deadline
        if deadline is None:
            return "{prefix}oo" if header else None
        d = deadline.date() if isinstance(deadline, datetime) else deadline
        if (datetime.now().date() - d).days / 365 > 1000:
            return self.config.item.deadline.format[0].format(f"{prefix}-oo")
        if isinstance(deadline, date):
            deadline = datetime.combine(deadline, datetime.max.time())
        remaining_time = deadline - datetime.now()
        seconds = abs(remaining_time.total_seconds())
        if abs(seconds) < 365 * 24 * 60 * 60:  # one year
            num_components = self.config.item.deadline.num_components
            timedelta_fmt = self.config.item.deadline.timedelta
            text = prefix + timedelta_format(
                remaining_time, timedelta_fmt, num_components)
        else:
            dt_fmt = self.config.item.deadline.datetime
            text = f"{prefix}{deadline:{dt_fmt}}"
        rich_format = self.config.item.deadline.format
        if status in ["done", "note"]:
            fmt = rich_format.status_done
        else:
            fmt = rich_format._
            for k, v in rich_format.items():
                if isinstance(k, int) and remaining_time.total_seconds() < k:
                    fmt = v
        return fmt.format(text)

    def _render_created_at(self, created_at: datetime) -> Optional[str]:
        return self.config.item.created_at.format.format(created_at)

    def _render_description(self, description: Optional[str]) -> Optional[str]:
        if description is None:
            return None
        desc = shorten(description, self.config.item.description.max_length)
        return self.config.item.description.format.format(desc)

    def _render_header(
        self, group_by: GroupBy, value: Any
    ) -> str | None:
        if group_by == "id":
            return None
        if group_by == "project":
            return self._render_project(value)
        if group_by == "tag":
            return self._render_tags([value])
        if group_by == "priority":
            return self._render_priority(value, True)
        if group_by == "status":
            return self._render_status(value, True)
        if group_by == "deadline":
            return self._render_deadline(value, "pending", True)
        if group_by == "created_at":
            return self._render_created_at(value)
        raise ValueError(f"Unknown group_by: {group_by}")

    def _render_fields(self, todo: TodoItem) -> Dict[str, str]:
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
        return {k: " " + v if v else "" for k, v in fields.items()}

    def render_item(
        self, todo: TodoItem, group_by: GroupBy = "id"
    ) -> str:
        fields = self._render_fields(todo)
        format = self.config.group.format[group_by]
        return format.format(**fields)[1:]

    def render_item_diff(
        self, before_todo: TodoItem, after_todo: TodoItem
    ) -> str:
        strip_color = lambda fields: \
            {k: strip_rich(v) for k, v in fields.items()}
        before_nc = strip_color(self._render_fields(before_todo))
        after = self._render_fields(after_todo)
        after_nc = strip_color(after)
        fields = {}
        diff_format = self.config.item.diff.format
        for k, v in before_nc.items():
            if v == after_nc[k]:
                fields[k] = after[k]
            else:
                bv, av = before_nc[k].lstrip(), after[k].lstrip()
                fields[k] = " " + diff_format.format(bv, av)
        return self.config.item.format.format(**fields)[1:]

    def render(
        self, grouped_todos: Dict[Any, List[TodoItem]],
        group_by: GroupBy, render_stats: bool = True
    ) -> str:
        text = []
        if not grouped_todos:
            text.append(self.config.message.empty)
        for group, gtodos in grouped_todos.items():
            if not gtodos:
                continue
            if group_by != "id":
                stats = self._get_stats(gtodos)
                progress = f"[{stats['done']}/{len(gtodos)}]"
                group = self._render_header(group_by, group)
                header = self.config.group.header.format.format(
                    group=group, progress=progress)
                text.append(header)
            for todo in gtodos:
                item = f"{self.render_item(todo, group_by)}"
                text.append(item)
            text.append("")
        if grouped_todos and render_stats:
            all_todos = functools.reduce(operator.add, grouped_todos.values())
            text.append(self.render_stats(all_todos))
        else:
            text = text[:-1]  # remove last empty line
        return "\n".join(text)

    def render_result(
        self, result: ActionResult
    ) -> str | RenderableType | List[str | RenderableType]:
        try:
            render_func = getattr(self, f"render_{type(result).__name__}")
        except AttributeError:
            raise ValueError(f"Unknown result type: {type(result)}")
        return render_func(result)

    def render_ViewResult(self, result: ViewResult) -> str:
        render_stats = self.config.view.stats
        render_stats = result.is_all if render_stats == "all" else render_stats
        return self.render(result.grouped_todos, result.group_by, render_stats)

    def render_QueryResult(self, result: QueryResult) -> str:
        values = [", ".join([repr(v) for v in row]) for row in result.values]
        return "\n".join(values)

    def render_AddResult(self, result: AddResult) -> str:
        return "\n".join(
            [self.config.message.add, "", self.render_item(result.item)])

    def render_EditResult(self, result: EditResult) -> str:
        if not result.after:
            text = [self.config.message.no_edit]
        else:
            c = len(result.after)
            message = self.config.message.edit.format(
                c, pluralize('item', c))
            text = [message]
            text.append("")
        for btodo, atodo in zip(result.before, result.after):
            text.append(self.render_item_diff(btodo, atodo))
        return "\n".join(text)

    def render_HistoryResult(self, result: HistoryResult) -> RenderableType:
        table = Table(box=SIMPLE_HEAVY)
        table.add_column("Time", justify="right")
        table.add_column("Commit")
        for item in result.history:
            dt = item["timestamp"].replace(tzinfo=None)  # type: ignore
            dt = timedelta_format(datetime.now() - dt, num_components=1)
            message = item["message"].splitlines()[0]  # type: ignore
            table.add_row(dt, message)
        return table

    def render_SwitchResult(
        self, result: SwitchResult
    ) -> List[RenderableType]:
        format = getattr(self.config.message, result.action)
        text = format.format(result.message)
        ar = result.action_result
        panel = []
        if isinstance(ar, AddResult) and result.action == "undo":
            after = TodoItem.from_dict(ar.item.to_dict())
            after.status = "delete"
            panel = [
                self.config.message.undo_add, "",
                self.render_item_diff(ar.item, after)]
        if isinstance(ar, AddResult) and result.action == "redo":
            panel = [
                self.config.message.add, "",
                self.render_item(ar.item)]
        if isinstance(ar, EditResult):
            message = self.config.message.undo_edit.format(
                len(ar.after), pluralize('item', len(ar.after)))
            panel = [message, ""]
            for btodo, atodo in zip(ar.before, ar.after):
                if result.action == "undo":
                    btodo, atodo = atodo, btodo
                panel.append(self.render_item_diff(btodo, atodo))
        return [text, Panel.fit(Group(*panel))]
