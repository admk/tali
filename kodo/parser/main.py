import os
from typing import Literal, Optional
from datetime import datetime

from parsimonious.grammar import Grammar
from parsimonious.nodes import NodeVisitor
from parsimonious.exceptions import ParseError, VisitationError

from .. import constants
from .common import CommonMixin
from .datetime import DateTimeParser


Mode = Literal["selection", "action"]

class CommandParser(NodeVisitor, CommonMixin):
    def __init__(self, reference_dt: Optional[datetime] = None):
        super().__init__()
        self.datetime_parser = DateTimeParser(reference_dt or datetime.now())
        root = os.path.dirname(__file__)
        with open(os.path.join(root, 'main.grammar'), 'r') as f:
            grammar = f.read()
            grammar = grammar.format(**constants.TOKENS)
            for mode in ["selection", "action"]:
                entry = "command = {mode}_chain\n\n"
                grammar = entry.format(mode=mode) + grammar
                setattr(self, f"{mode}_grammar", Grammar(grammar))

    def _parse_mode(self, mode: Mode, text: str, pos: int = 0):
        grammar = getattr(self, f"{mode}_grammar")
        parsed = super().visit(grammar.parse(text, pos))
        if 'deadline' in parsed:
            parsed['deadline'] = self.datetime_parser.parse(
                " ".join(parsed['deadline']))
        return parsed

    def parse(self, text: str, pos: int = 0):
        if " . " in text:
            commands = text.split(" . ")
            try:
                selection, action = commands
            except ValueError:
                raise SyntaxError("Invalid command format.")
            selection = self._parse_mode("selection", selection, pos)
            action = self._parse_mode("action", action, pos),
        elif text.startswith(". "):
            selection = None
            action = self._parse_mode("action", text[2:], pos),
        else:
            selection = self._parse_mode("selection", text, pos),
            action = None,
        return selection, action

    def visit_text(self, node, visited_children):
        return "text", node.text

    def visit_ws(self, node, visited_children):
        return None

    def _visit_chain(self, node, visited_children):
        _, items = visited_children
        parsed = {}
        for item in items:
            (kind, value), _ = item
            if kind == "id":
                parsed.setdefault("id", []).append(value)
            elif kind == "project":
                parsed["project"] = value
            elif kind == "tag":
                parsed.setdefault("tag", []).append(value)
            elif kind == "status":
                parsed["status"] = value
            elif kind == "priority":
                parsed["priority"] = value
            elif kind == "deadline":
                parsed.setdefault("deadline", []).append(value)
            elif kind == "text":
                parsed.setdefault("title", []).append(value)
            else:
                raise ValueError(f"Unknown kind {kind!r}.")
        return parsed

    def visit_action_chain(self, node, visited_children):
        return self._visit_chain(node, visited_children)

    def visit_selection_chain(self, node, visited_children):
        return self._visit_chain(node, visited_children)

    def visit_task_range(self, node, visited_children):
        first, last = visited_children
        if last is None:
            return list(range(1, first + 1))
        last = last[0][1]
        return "id", list(range(first, last + 1))

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
        return "status", status

    def visit_priority(self, node, visited_children):
        _, priority = visited_children
        return "priority", priority

    visit_task_id = CommonMixin._visit_int
    visit_project_name = visit_tag_name = \
        visit_status_val = visit_priority_val = \
        visit_pm = CommonMixin._visit_str
    visit_selection = visit_action = \
        visit_group = visit_sort = visit_shared = \
        CommonMixin._visit_any_of

    visit_ws = CommonMixin._visit_noop

    def generic_visit(self, node, visited_children):
        return visited_children


if __name__ == "__main__":
    parser = CommandParser()
    commands = """
    . Buy milk /grocery                      # Basic task
    . "Team meeting" /work @meeting ^fri :n  # Note with tag and deadline
    . Fix bug! !high /dev @+urgent ^+2h      # High-priority task, due 2 hours from now
    hello, world.
    1..5 . /home
    """
    import pprint
    commands = commands.strip().split("\n")
    commands = [command.split("#")[0].strip() for command in commands]
    for command in commands:
        result = parser.parse(command)
        print(command)
        pprint.pprint(result)
