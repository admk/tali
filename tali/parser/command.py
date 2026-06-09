import os
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional, Tuple

from box import Box
from dateutil.relativedelta import relativedelta
from parsimonious.exceptions import ParseError
from parsimonious.grammar import Grammar
from parsimonious.nodes import NodeVisitor, VisitationError

from ..book.select import (
    FilterClause,
    GroupBy,
    SelectAnd,
    Selection,
    SelectionExpr,
    SelectNot,
    SelectOr,
    SortBy,
)
from ..common import logger
from .common import CommonMixin
from .common import ParserError as CommonParserError
from .datetime import DateTimeParser
from .editor import unescape_command_text

Mode = Literal["selection", "action"]
BOOLEAN_TOKENS = ["+", "~"]


class CommandParseError(CommonParserError):
    pass


class CommandSyntaxError(CommandParseError):
    """An exception raised when a command syntax is invalid."""


class CommandSemanticError(CommandParseError):
    """An exception raised when a command is semantically invalid."""


@dataclass
class ParsedSelection:
    selection: Selection
    group: Optional[GroupBy] = None
    sort: Optional[SortBy] = None
    query: Optional[List[str]] = None


class CommandParser(NodeVisitor, CommonMixin):
    _OR = object()

    def __init__(self, config: Box, reference_dt: Optional[datetime] = None):
        super().__init__()
        self.config = config
        self.datetime_parser = DateTimeParser(reference_dt or datetime.now())
        root = os.path.dirname(__file__)
        with open(os.path.join(root, "command.grammar"), "r") as f:
            grammar = f.read()
            grammar = grammar.format(**config.token)
        for mode in ["selection", "action"]:
            entry = "command = {mode}_chain\n\n"
            mode_grammar = entry.format(mode=mode) + grammar
            setattr(self, f"{mode}_grammar", Grammar(mode_grammar))

    def _parse_mode(
        self, mode: Mode, text: str, pos: int = 0
    ) -> ParsedSelection | Dict[str, str | List[str]]:
        grammar = getattr(self, f"{mode}_grammar")
        try:
            ast = grammar.parse(text.strip(), pos)
            logger.debug(f"Parsed {mode} AST:\n{ast}")
        except ParseError as e:
            arrow = " " * e.pos + "[bold red]⌃[/bold red] "
            msg = f"Syntax Error:\n  {e.text}\n  {arrow}\n  {e}"
            raise CommandSyntaxError(msg) from e
        try:
            return super().visit(ast)
        except VisitationError as e:
            raise CommandSemanticError(e) from e

    def parse(
        self, text: str, pos: int = 0
    ) -> Tuple[
        Optional[Selection],
        Optional[GroupBy],
        Optional[SortBy],
        Optional[List[str]],
        Optional[Literal["editor"] | Dict[str, str | List[str]]],
    ]:
        separator = self.config.token.separator
        if not text:
            return None, None, None, None, None
        if text == separator:
            return None, None, None, None, "editor"
        if text.startswith(f"{separator} "):
            # add new item
            selection = None
            action = self._parse_mode("action", text[len(separator) + 1 :], pos)
        elif (
            index := self._find_unescaped_token(text, f" {separator} ")
        ) is not None:
            # filter and update
            selection_text = text[:index]
            action_text = text[index + len(separator) + 2 :]
            selection = self._parse_mode("selection", selection_text, pos)
            action = self._parse_mode("action", action_text, pos)
        elif text.endswith(f" {separator}"):
            text = text[: -len(f" {separator}")]
            selection = self._parse_mode("selection", text, pos)
            # a separator at the end launches the editor
            action = "editor"
        else:
            selection = self._parse_mode("selection", text, pos)
            action = None
        if selection is not None:
            assert isinstance(selection, ParsedSelection)
            group = selection.group
            sort = selection.sort
            query = selection.query
            selection = selection.selection
        else:
            group = sort = query = None
        return selection, group, sort, query, action  # type: ignore

    def _chain_items(self, visited_children):
        item, items = visited_children
        return [item] + [i for _, i in items]

    def _parse_items(self, items):
        parsed = {}
        kinds = {
            "unique": [
                "project",
                "status",
                "priority",
                "group",
                "sort",
                "description",
                "parent",
            ],
            "list": ["id", "tag", "deadline", "title", "query"],
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
                        f"Duplicate {kind!r} in command."
                    )
                parsed[kind] = value
            elif kind in kinds["list"]:
                kind_list = parsed.setdefault(kind, [])
                if isinstance(value, list):
                    kind_list.extend(value)
                else:
                    kind_list.append(value)
            else:
                raise CommandSemanticError(f"Unknown kind {kind!r}.")
        if "id" in parsed:
            parsed["id"] = list(sorted(set(parsed["id"])))
        if "title" in parsed:
            parsed["title"] = " ".join(parsed["title"]).strip()
        if "deadline" in parsed:
            try:
                dts = [
                    self.datetime_parser.parse(dt) for dt in parsed["deadline"]
                ]
            except (ParseError, VisitationError) as e:
                raise CommandSemanticError(
                    f"Invalid date time syntax: {e}"
                ) from e
            parsed["deadline"] = dts
        if "tag" in parsed:
            parsed["tags"] = parsed.pop("tag")
        if "parent" in parsed:
            parsed["parent"] = parsed.pop("parent")
        return parsed

    def _visit_chain(self, node, visited_children):
        return self._parse_items(self._chain_items(visited_children))

    def visit_action_chain(self, node, visited_children):
        parsed = self._visit_chain(node, visited_children)
        if self._has_unescaped_token(
            parsed.get("title", ""), self.config.token.priority
        ):
            parsed["priority"] = "high"
        self._unescape_parsed_text(parsed)
        if parsed.get("priority") == "":
            parsed["priority"] = "high"
        if "deadline" in parsed:
            if len(parsed["deadline"]) > 1:
                raise CommandSemanticError(
                    "Multiple deadlines are not allowed."
                )
            dt = parsed["deadline"][0]
            if not isinstance(dt, relativedelta):
                years = (dt - datetime.now()).days / 365
                dt = None if years >= 1000 else dt
            parsed["deadline"] = dt
        return parsed

    def visit_selection_chain(self, node, visited_children):
        items = self._chain_items(visited_children)
        expr_items, modifier_items = self._split_selection_items(items)
        selection = self._selection_expr_from_items(expr_items)
        modifiers = self._parse_items(modifier_items) if modifier_items else {}
        return ParsedSelection(
            selection,
            modifiers.pop("group", None),
            modifiers.pop("sort", None),
            modifiers.pop("query", None),
        )

    def _split_selection_items(self, items):
        expr_items = []
        modifier_items = []
        for item in items:
            if item is self._OR:
                expr_items.append(item)
                continue
            if isinstance(item, tuple):
                kind, value = item
                if kind in ["group", "sort", "query"]:
                    modifier_items.append(item)
                    continue
                if kind in ["priority", "status"] and value == "":
                    modifier_items.append(("group", kind))
                    continue
            expr_items.append(item)
        return expr_items, modifier_items

    def _is_selection_expr(self, item: Any) -> bool:
        return isinstance(item, (FilterClause, SelectAnd, SelectOr, SelectNot))

    def _as_selection_expr(self, selection: Selection) -> SelectionExpr:
        if isinstance(selection, dict):
            return FilterClause(selection)
        return selection

    def _parse_filter_items(self, items):
        parsed = self._parse_items(items)
        self._unescape_parsed_text(parsed)
        for key in ["group", "sort", "query"]:
            if key in parsed:
                raise CommandSemanticError(
                    f"Cannot use {key!r} inside a selection expression."
                )
        for group in ["priority", "status"]:
            if parsed.get(group) == "":
                raise CommandSemanticError(
                    f"Cannot use bare {group!r} as a filter."
                )
        return parsed

    def _and_expr_from_items(self, items) -> Selection:
        positive_items = []
        children: List[SelectionExpr] = []
        for item in items:
            if self._is_selection_expr(item):
                children.append(item)
            else:
                positive_items.append(item)

        if positive_items:
            filters = self._parse_filter_items(positive_items)
            if not children:
                return filters
            children.insert(0, FilterClause(filters))

        if not children:
            return {}
        if len(children) == 1:
            return children[0]
        return SelectAnd(children)

    def _selection_expr_from_items(self, items) -> Selection:
        if not items:
            return {}
        segments = []
        segment = []
        for item in items:
            if item is self._OR:
                if not segment:
                    raise CommandSemanticError("Missing selection before '+'.")
                segments.append(segment)
                segment = []
            else:
                segment.append(item)
        if not segment:
            raise CommandSemanticError("Missing selection after '+'.")
        segments.append(segment)

        selections = [self._and_expr_from_items(s) for s in segments]
        if len(selections) == 1:
            return selections[0]
        return SelectOr([self._as_selection_expr(s) for s in selections])

    def visit_query(self, node, visited_children):
        name = node.children[1].children[0].expr_name
        if name == "group":
            query = visited_children[1][0][1]
        elif name == "description_token":
            query = "description"
        elif name == "query_token":
            query = "title"
        else:
            raise CommandSemanticError(
                f"Unexpected query type: {node.children[1].expr_name}"
            )
        return "query", query

    def visit_group(self, node, visited_children):
        group = node.children[0].expr_name.replace("_token", "")
        return "group", group

    def visit_sort(self, node, visited_children):
        sort = node.children[1].children[0].expr_name.replace("_token", "")
        return "sort", sort

    def visit_or_token(self, node, visited_children):
        return self._OR

    def visit_not_selection(self, node, visited_children):
        child = visited_children[1][0]
        if self._is_selection_expr(child):
            return SelectNot(child)
        return SelectNot(FilterClause(self._parse_filter_items([child])))

    def visit_selection_word(self, node, visited_children):
        return visited_children[2]

    def visit_task_range(self, node, visited_children):
        first, last = visited_children[:2]
        if not last:
            return "id", [first]
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

    def visit_parent(self, node, visited_children):
        _, task_id = visited_children
        return "parent", task_id

    def visit_description(self, node, visited_children):
        text = node.text.strip()
        text = text.removeprefix(self.config.token.description).lstrip()
        return "description", self._unescape_command_text(text)

    def _unescape_command_text(self, text: str) -> str:
        tokens = [
            value for key, value in self.config.token.items() if key != "stdin"
        ]
        tokens.extend(BOOLEAN_TOKENS)
        return unescape_command_text(text, tokens)

    def _unescape_parsed_text(self, parsed: Dict[str, str | List[str]]) -> None:
        if "title" in parsed:
            parsed["title"] = self._unescape_command_text(parsed["title"])

    def _has_unescaped_token(self, text: str, token: str) -> bool:
        return self._find_unescaped_token(text, token) is not None

    def _find_unescaped_token(self, text: str, token: str) -> Optional[int]:
        if not token:
            return None
        escaped = False
        quote = None
        for i, char in enumerate(text):
            if escaped:
                escaped = False
                continue
            if char == "\\":
                escaped = True
                continue
            if quote:
                if char == quote:
                    quote = None
                continue
            if char in ['"', "'"]:
                quote = char
                continue
            if text.startswith(token, i):
                return i
        return None

    visit_task_id = CommonMixin._visit_int
    visit_word = visit_project_name = visit_tag_name = visit_pm = (
        CommonMixin._visit_str
    )
    visit_selection_piece = visit_action = visit_shared = (
        CommonMixin._visit_any_of
    )
    visit_ws = CommonMixin._visit_noop

    def generic_visit(self, node, visited_children):
        return visited_children
