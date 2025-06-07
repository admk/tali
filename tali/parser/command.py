import os
from typing import Literal, Optional, Dict, List, Tuple
from datetime import datetime

from parsimonious.exceptions import ParseError
from parsimonious.grammar import Grammar
from parsimonious.nodes import NodeVisitor, VisitationError

from box import Box

from ..common import logger
from ..book.select import GroupBy, SortBy, FilterBy, FilterValue
from .common import CommonMixin
from .datetime import DateTimeParser


Mode = Literal["selection", "action"]


class CommandParseError(Exception):
    pass


class CommandSyntaxError(CommandParseError):
    """An exception raised when a command syntax is invalid."""


class CommandSemanticError(CommandParseError):
    """An exception raised when a command is semantically invalid."""


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
            logger.debug(f"Parsed {mode} AST:\n{ast}")
        except ParseError as e:
            arrow = " " * e.pos + "[bold red]⌃[/bold red] "
            msg = f"Syntax Error:\n  {e.text}\n  {arrow}\n  {e}"
            raise CommandSyntaxError(msg) from e
        return super().visit(ast)

    def parse(self, text: str, pos: int = 0) -> Tuple[
        Optional[Dict[FilterBy, FilterValue]],
        Optional[GroupBy], Optional[SortBy], Optional[List[str]],
        Optional[Literal["editor"] | Dict[str, str | List[str]]],
    ]:
        separator = self.config.token.separator
        if not text:
            return None, None, None, None, None
        if text == separator:
            return None, None, None, None, "editor"
        if f" {separator} " in text:
            # filter and update
            commands = text.split(f" {separator} ")
            try:
                selection, action = commands
            except ValueError as e:
                raise CommandSyntaxError(
                    "Invalid command format. "
                    f"Expected '(selection) {separator} (action)'.")
            selection = self._parse_mode("selection", selection, pos)
            action = self._parse_mode("action", action, pos)
        elif text.startswith(f"{separator} "):
            # add new item
            selection = None
            action = self._parse_mode("action", text[2:], pos)
        elif text.endswith(f" {separator}"):
            text = text[:-len(f" {separator}")]
            selection = self._parse_mode("selection", text, pos)
            # a separator at the end launches the editor
            action = "editor"
        else:
            selection = self._parse_mode("selection", text, pos)
            action = None
        if selection is not None:
            group = selection.pop("group", None)
            sort = selection.pop("sort", None)
            query = selection.pop("query", None)
        else:
            group = sort = query = None
        return selection, group, sort, query, action  # type: ignore

    def _visit_chain(self, node, visited_children):
        item, items = visited_children
        items = [item] + [i for _, i in items]
        parsed = {}
        kinds = {
            "unique": [
                "project", "status", "priority",
                "group", "sort", "description"],
            "list": ["ids", "tag", "deadline", "title", "query"],
        }
        for item in items:
            if isinstance(item, tuple):
                kind, value = item
            elif isinstance(item, str):
                kind, value = "title", item
            else:
                raise CommandSemanticError(f"Unknown item {item!r}.")
            if kind in kinds["unique"]:
                if kind in parsed:
                    raise CommandSemanticError(
                        f"Duplicate {kind!r} in command.")
                parsed[kind] = value
            elif kind in kinds["list"]:
                kind_list = parsed.setdefault(kind, [])
                if isinstance(value, list):
                    kind_list.extend(value)
                else:
                    kind_list.append(value)
            else:
                raise CommandSemanticError(f"Unknown kind {kind!r}.")
        if "ids" in parsed:
            parsed["ids"] = list(sorted(set(parsed["ids"])))
        if "title" in parsed:
            parsed["title"] = " ".join(parsed["title"]).strip()
        if "deadline" in parsed:
            try:
                dts = [
                    self.datetime_parser.parse(dt)
                    for dt in parsed["deadline"]]
            except (ParseError, VisitationError) as e:
                raise CommandSemanticError(
                    f"Invalid date time syntax: {e}") from e
            parsed["deadline"] = dts
        if "tag" in parsed:
            parsed["tags"] = parsed.pop("tag")
        return parsed

    def visit_action_chain(self, node, visited_children):
        parsed = self._visit_chain(node, visited_children)
        if "!" in parsed.get("title", ""):
            parsed["priority"] = "high"
        if parsed.get("priority") == "":
            parsed["priority"] = "high"
        if "deadline" in parsed:
            if len(parsed["deadline"]) > 1:
                raise CommandSemanticError(
                    "Multiple deadlines are not allowed.")
            dt = parsed["deadline"][0]
            years = (dt - datetime.now()).days / 365
            parsed["deadline"] = None if years >= 1000 else dt
        return parsed

    def visit_selection_chain(self, node, visited_children):
        parsed = self._visit_chain(node, visited_children)
        for group in ["priority", "status"]:
            if parsed.get(group) == "":
                del parsed[group]
                parsed["group"] = group
        return parsed

    def visit_query(self, node, visited_children):
        name = node.children[1].children[0].expr_name
        if name == "group":
            query = visited_children[1][0][1]
        elif name == "query_token":
            query = "title"
        else:
            raise CommandSemanticError(
                f"Unexpected query type: {node.children[1].expr_name}")
        return "query", query

    def visit_group(self, node, visited_children):
        group = node.children[0].expr_name.replace("_token", "")
        return "group", group

    def visit_sort(self, node, visited_children):
        sort = node.children[1].children[0].expr_name.replace("_token", "")
        return "sort", sort

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
        return "deadline", self._unquote_str(deadline)

    def visit_status(self, node, visited_children):
        _, status = visited_children
        status = status[0] if status else ""
        return "status", status

    def visit_priority(self, node, visited_children):
        _, priority = visited_children
        priority = priority[0] if priority else ""
        return "priority", priority

    def visit_description(self, node, visited_children):
        text = node.text.strip().lstrip(self.config.token.description).lstrip()
        return "description", text

    visit_task_id = CommonMixin._visit_int
    visit_word = visit_project_name = visit_tag_name = visit_pm = \
        CommonMixin._visit_str
    visit_selection = visit_action = visit_shared = CommonMixin._visit_any_of
    visit_ws = CommonMixin._visit_noop

    def generic_visit(self, node, visited_children):
        return visited_children
