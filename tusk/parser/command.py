import os
from typing import Literal, Optional, Dict, List, Tuple
from datetime import datetime

from parsimonious.exceptions import ParseError
from parsimonious.grammar import Grammar
from parsimonious.nodes import NodeVisitor, VisitationError

from box import Box

from ..common import debug, error
from ..book.select import GroupBy, SortBy, FilterBy, FilterValue
from .common import CommonMixin
from .datetime import DateTimeParser


Mode = Literal["selection", "action"]


class CommandParser(NodeVisitor, CommonMixin):
    def __init__(self, config: Box, reference_dt: Optional[datetime] = None):
        super().__init__()
        self.config = config
        self.datetime_parser = DateTimeParser(reference_dt or datetime.now())
        root = os.path.dirname(__file__)
        with open(os.path.join(root, 'command.grammar'), 'r') as f:
            grammar = f.read()
            grammar = grammar.format(**config.token)
        for mode in ["selection", "action"]:
            entry = "command = {mode}_chain\n\n"
            mode_grammar = entry.format(mode=mode) + grammar
            setattr(self, f"{mode}_grammar", Grammar(mode_grammar))

    def _parse_mode(
        self, mode: Mode, text: str, pos: int = 0
    ) -> Dict[str, str | List[str]]:
        grammar = getattr(self, f"{mode}_grammar")
        try:
            ast = grammar.parse(text.strip(), pos)
            debug(f"Parsed {mode} AST:\n{ast}")
        except ParseError as e:
            arrow = " " * e.pos + "^ "
            msg = f"{e.text}\n{arrow}\n{e}"
            error(msg)
        return super().visit(ast)

    def parse(self, text: str, pos: int = 0) -> Tuple[
        Optional[Dict[FilterBy, FilterValue]],
        Optional[GroupBy], Optional[SortBy],
        Optional[Dict[str, str | List[str]]],
    ]:
        if not text.strip():
            return None, None, None, None
        separator = self.config.token.separator
        if f" {separator} " in text:
            commands = text.split(f" {separator} ")
            try:
                selection, action = commands
            except ValueError:
                raise SyntaxError("Invalid command format.")
            selection = self._parse_mode("selection", selection, pos)
            action = self._parse_mode("action", action, pos)
        elif text.startswith(f"{separator} "):
            selection = None
            action = self._parse_mode("action", text[2:], pos)
        else:
            if text.endswith(f" {separator}"):
                # a hack for separator at the end
                text = text[:-len(f" {separator}")]
            selection = self._parse_mode("selection", text, pos)
            action = None
        if selection is not None:
            group: Optional[GroupBy] = \
                selection.pop("group", None)  # type: ignore
            sort: Optional[SortBy] = \
                selection.pop("sort", None)  # type: ignore
        else:
            group = sort = None
        return selection, group, sort, action  # type: ignore

    def _visit_chain(self, node, visited_children):
        item, items = visited_children
        items = [item] + [i for _, i in items]
        parsed = {}
        for item in items:
            if isinstance(item, tuple):
                kind, value = item
            elif isinstance(item, str):
                kind, value = "text", item
            else:
                raise ValueError(f"Unknown item {item!r}.")
            if kind == "ids":
                parsed.setdefault("ids", []).extend(value)
            elif kind == "project":
                parsed["project"] = value
            elif kind == "tag":
                parsed.setdefault("tags", []).append(value)
            elif kind == "status":
                parsed["status"] = value
            elif kind == "priority":
                parsed["priority"] = value
            elif kind == "deadline":
                parsed.setdefault("deadline", []).append(value)
            elif kind == "text":
                parsed.setdefault("title", []).append(value)
            elif kind == "group":
                parsed["group"] = value
            elif kind == "sort":
                parsed["sort"] = value
            elif kind == "delete":
                parsed["delete"] = True
            else:
                raise ValueError(f"Unknown kind {kind!r}.")
        if "ids" in parsed:
            parsed["ids"] = list(sorted(set(parsed["ids"])))
        if "title" in parsed:
            parsed["title"] = " ".join(parsed["title"]).strip()
        if "deadline" in parsed:
            try:
                dt = self.datetime_parser.parse(" ".join(parsed["deadline"]))
            except (ParseError, VisitationError) as e:
                error(f"Invalid date time syntax. {e}")
            parsed["deadline"] = dt
        return parsed

    def visit_action_chain(self, node, visited_children):
        parsed = self._visit_chain(node, visited_children)
        if "!" in parsed.get("title", ""):
            parsed["priority"] = "high"
        if parsed.get("priority") == "":
            parsed["priority"] = "high"
        return parsed

    def visit_selection_chain(self, node, visited_children):
        parsed = self._visit_chain(node, visited_children)
        for group in ["priority", "status"]:
            if parsed.get(group) == "":
                del parsed[group]
                parsed["group"] = group
        return parsed

    def visit_task_range(self, node, visited_children):
        first, last = visited_children
        if not last:
            return "ids", [first]
        last = last[0][1]
        return "ids", list(range(first, last + 1))

    def visit_project(self, node, visited_children):
        _, project = visited_children
        return "project", project

    def visit_tag(self, node, visited_children):
        _, op, tag = visited_children
        op = "" if not op else op[0]
        return "tag", op + tag

    def visit_deadline(self, node, visited_children):
        _, deadline = visited_children
        return "deadline", deadline.strip()

    def visit_status(self, node, visited_children):
        _, status = visited_children
        status = status[0] if status else ""
        return "status", status

    def visit_priority(self, node, visited_children):
        _, priority = visited_children
        priority = priority[0] if priority else ""
        return "priority", priority

    def visit_group(self, node, visited_children):
        group = node.children[0].expr_name.replace("_token", "")
        return "group", group

    def visit_sort(self, node, visited_children):
        sort = node.children[1].children[0].expr_name.replace("_token", "")
        return "sort", sort

    def visit_delete_token(self, node, visited_children):
        return "delete", None

    visit_task_id = CommonMixin._visit_int
    visit_word = visit_project_name = visit_tag_name = visit_pm = \
        CommonMixin._visit_str
    visit_selection = visit_action = visit_shared = CommonMixin._visit_any_of
    visit_ws = CommonMixin._visit_noop

    def generic_visit(self, node, visited_children):
        return visited_children
