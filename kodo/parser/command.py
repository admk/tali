import os
import textwrap
from typing import Literal, Optional, Dict, List, Tuple
from datetime import datetime

from parsimonious.exceptions import ParseError
from parsimonious.grammar import Grammar
from parsimonious.nodes import NodeVisitor

from .. import constants
from ..common import error
from ..book.select import GroupBy, SortBy, FilterBy, FilterValue
from .common import CommonMixin
from .datetime import DateTimeParser


Mode = Literal["selection", "action"]


class CommandParser(NodeVisitor, CommonMixin):
    def __init__(self, reference_dt: Optional[datetime] = None):
        super().__init__()
        self.datetime_parser = DateTimeParser(reference_dt or datetime.now())
        root = os.path.dirname(__file__)
        with open(os.path.join(root, 'command.grammar'), 'r') as f:
            grammar = f.read()
            grammar = grammar.format(**constants.TOKENS)
            for mode in ["selection", "action"]:
                entry = "command = {mode}_chain\n\n"
                grammar = entry.format(mode=mode) + grammar
                setattr(self, f"{mode}_grammar", Grammar(grammar))

    def _parse_mode(
        self, mode: Mode, text: str, pos: int = 0
    ) -> Dict[str, str | List[str]]:
        grammar = getattr(self, f"{mode}_grammar")
        try:
            ast = grammar.parse(text, pos)
        except ParseError as e:
            arrow = " " * e.pos + "^ "
            msg = f"{e.text}\n{arrow}\n{e}"
            error(msg)
        parsed = super().visit(ast)
        if not parsed:
            return parsed
        if mode == "selection":
            if parsed.get("status") == "":
                # a hack for empty status to denote group
                del parsed["status"]
                parsed["group"] = "status"
        if mode == "action":
            if "!" in parsed.get("title", ""):
                parsed["priority"] = "high"
        if "deadline" in parsed:
            parsed["deadline"] = \
                self.datetime_parser.parse(" ".join(parsed["deadline"]))
        return parsed

    def parse(self, text: str, pos: int = 0) -> Tuple[
        Optional[Dict[FilterBy, FilterValue]],
        Optional[GroupBy], Optional[SortBy],
        Optional[Dict[str, str | List[str]]],
    ]:
        separator = constants.TOKENS["separator"]
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
            if len(item) == 2:
                kind, value = item
            else:
                kind, value = "text", item
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
            else:
                raise ValueError(f"Unknown kind {kind!r}.")
        if "ids" in parsed:
            parsed["ids"] = list(sorted(set(parsed["ids"])))
        if "title" in parsed:
            parsed["title"] = "".join(parsed["title"]).strip()
        return parsed

    def visit_action_chain(self, node, visited_children):
        return self._visit_chain(node, visited_children)

    def visit_selection_chain(self, node, visited_children):
        return self._visit_chain(node, visited_children)

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
        _, (_, deadline) = visited_children
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

    visit_task_id = CommonMixin._visit_int
    visit_word = visit_project_name = visit_tag_name = visit_pm = \
        CommonMixin._visit_str
    visit_selection = visit_action = visit_shared = CommonMixin._visit_any_of
    visit_ws = CommonMixin._visit_noop

    def generic_visit(self, node, visited_children):
        return visited_children


if __name__ == "__main__":
    parser = CommandParser()
    commands = """
    . Buy milk /grocery                      # Basic task
    . "Team meeting" /work @meeting ^fri :n  # Note with tag and deadline
    . Fix bug! !high /dev @+urgent ^2pm      # High-priority task, due 2 hours from now
    hello, world.
    1..5 . /home
    @ =/
    """
    commands = commands.strip().split("\n")
    commands = [command.split("#")[0].strip() for command in commands]
    for command in commands:
        result = parser.parse(command)
        print(command, result)
