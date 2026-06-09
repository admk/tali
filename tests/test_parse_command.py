import os
import unittest
from datetime import datetime

import yaml
from box import Box

from tali import __toolname__ as _NAME
from tali.book.select import FilterClause, SelectAnd, SelectNot, SelectOr
from tali.common import format_config
from tali.parser.command import CommandParseError, CommandParser


def F(filters):
    return FilterClause(filters)


def AND(*children):
    return SelectAnd(list(children))


def OR(*children):
    return SelectOr(list(children))


def NOT(child):
    return SelectNot(child)


class TestCommandParser(unittest.TestCase):
    def setUp(self):
        root = os.path.dirname(os.path.abspath(__file__))
        config_path = os.path.join(root, "..", _NAME, "config.yaml")
        with open(config_path, "r") as f:
            config = Box(yaml.safe_load(f), box_dots=True)
            self.config = format_config(config)
        dt = datetime(2025, 5, 11, 11, 0, 0)
        self.parser = CommandParser(self.config, dt)

    def _assert_parse_result(self, text, expected):
        result = self.parser.parse(text)
        self.assertEqual(result, expected)

    def _assert_parse_error(self, text):
        with self.assertRaises(CommandParseError):
            self.parser.parse(text)

    def test_add(self):
        expected = (
            None,
            None,
            None,
            None,
            {
                "title": "Buy milk",
                "project": "grocery",
                "deadline": self.parser.datetime_parser.parse("today"),
            },
        )
        self._assert_parse_result(". Buy milk /grocery ^today", expected)
        command = '. Meeting notes /work ^"tue 4pm" ,n'
        expected = (
            None,
            None,
            None,
            None,
            {
                "title": "Meeting notes",
                "project": "work",
                "deadline": self.parser.datetime_parser.parse("tue 4pm"),
                "status": "n",
            },
        )
        self._assert_parse_result(command, expected)
        expected = (
            None,
            None,
            None,
            None,
            {
                "title": "Fix bug",
                "project": "tali",
                "priority": "high",
                "tags": ["urgent"],
            },
        )
        self._assert_parse_result(". Fix bug /tali !high @urgent", expected)

    def test_escaped_title_tokens(self):
        expected = (
            None,
            None,
            None,
            None,
            {"title": "literal # and : characters"},
        )
        self._assert_parse_result(r". literal \# and \: characters", expected)

    def test_separator_in_title(self):
        expected = (None, None, None, None, {"title": "hello . 2"})
        self._assert_parse_result(". hello . 2", expected)

        expected = ({"id": [42]}, None, None, None, {"title": "hello . 2"})
        self._assert_parse_result("42 . hello . 2", expected)

        expected = ({"title": ". hello"}, None, None, None, {"title": "2"})
        self._assert_parse_result(r"\. hello . 2", expected)

    def test_edit(self):
        expected = ({"id": [42]}, None, None, None, {"status": ""})
        self._assert_parse_result("42 . ,", expected)
        expected = ({"id": [42]}, None, None, None, {"status": "x"})
        self._assert_parse_result("42 . ,x", expected)
        expected = ({"id": [42]}, None, None, None, {"status": "done"})
        self._assert_parse_result("42 . ,done", expected)
        expected = ({"id": [42]}, None, None, None, {"priority": "h"})
        self._assert_parse_result("42 . !h", expected)
        expected = (
            {"deadline": [self.parser.datetime_parser.parse("today")]},
            None,
            None,
            None,
            {"tags": ["star"]},
        )
        self._assert_parse_result("^today . @star", expected)
        expected = (
            {"id": [42]},
            None,
            None,
            None,
            {"title": "New title", "project": "newproject", "status": "n"},
        )
        self._assert_parse_result("42 . New title /newproject ,n", expected)

        expected = (
            {"id": [42]},
            None,
            None,
            None,
            {
                "title": "Fix /project @tag #42 . now",
                "project": "inbox",
                "tags": ["bug"],
                "status": "done",
            },
        )
        self._assert_parse_result(
            r"42 . ,done Fix \/project \@tag \#42 \. now /inbox @bug",
            expected,
        )

        expected = (
            {"id": [42]},
            None,
            None,
            None,
            {"title": "literal ! priority"},
        )
        self._assert_parse_result(r"42 . literal \! priority", expected)

    def test_filter(self):
        expected = (
            {
                "project": "work",
                "priority": "high",
                "deadline": [self.parser.datetime_parser.parse("today")],
            },
            None,
            None,
            None,
            None,
        )
        self._assert_parse_result("/work !high ^today", expected)

    def test_boolean_or_selection(self):
        expected = (
            OR(F({"project": "work"}), F({"project": "home"})),
            None,
            None,
            None,
            None,
        )
        self._assert_parse_result("/work + /home", expected)

        expected = (
            OR(
                F({"project": "work", "tags": ["urgent"]}),
                F({"project": "home", "priority": "high"}),
            ),
            None,
            None,
            None,
            None,
        )
        self._assert_parse_result("/work @urgent + /home !high", expected)

        expected = (
            OR(
                F({"project": "work"}),
                F({"project": "home", "tags": ["urgent"]}),
            ),
            None,
            None,
            None,
            None,
        )
        self._assert_parse_result("/work + /home @urgent", expected)

    def test_boolean_not_selection(self):
        expected = (
            AND(F({"project": "work"}), NOT(F({"tags": ["waiting"]}))),
            None,
            None,
            None,
            None,
        )
        self._assert_parse_result("/work ~@waiting", expected)

        expected = (
            OR(NOT(F({"tags": ["waiting"]})), F({"project": "home"})),
            None,
            None,
            None,
            None,
        )
        self._assert_parse_result("~@waiting + /home", expected)

        expected = (
            NOT(NOT(F({"tags": ["waiting"]}))),
            None,
            None,
            None,
            None,
        )
        self._assert_parse_result("~~@waiting", expected)

    def test_boolean_operator_literals(self):
        expected = ({"title": "C++"}, None, None, None, None)
        self._assert_parse_result("C++", expected)

        expected = ({"title": "foo+bar"}, None, None, None, None)
        self._assert_parse_result("foo+bar", expected)

        expected = ({"title": "foo +bar"}, None, None, None, None)
        self._assert_parse_result("foo +bar", expected)

        expected = ({"title": "foo+ bar"}, None, None, None, None)
        self._assert_parse_result("foo+ bar", expected)

        expected = (
            {"deadline": [self.parser.datetime_parser.parse("+3d")]},
            None,
            None,
            None,
            None,
        )
        self._assert_parse_result("^+3d", expected)

        expected = ({"tags": ["+urgent"]}, None, None, None, None)
        self._assert_parse_result("@+urgent", expected)

        expected = ({"title": "+"}, None, None, None, None)
        self._assert_parse_result(r"\+", expected)

        expected = ({"title": "~waiting"}, None, None, None, None)
        self._assert_parse_result(r"\~waiting", expected)

    def test_boolean_does_not_affect_actions(self):
        expected = (None, None, None, None, {"title": "Buy + milk"})
        self._assert_parse_result(". Buy + milk", expected)

        expected = (None, None, None, None, {"title": "Buy ~ milk"})
        self._assert_parse_result(". Buy ~ milk", expected)

        expected = (
            {"id": [42]},
            None,
            None,
            None,
            {"title": "New + title ~ ok"},
        )
        self._assert_parse_result("42 . New + title ~ ok", expected)

    def test_boolean_selection_modifiers(self):
        expected = (
            OR(F({"project": "work"}), F({"project": "home"})),
            None,
            "deadline",
            None,
            None,
        )
        self._assert_parse_result("/work + /home =^", expected)

        expected = (
            OR(F({"project": "work"}), F({"project": "home"})),
            None,
            None,
            ["project"],
            None,
        )
        self._assert_parse_result("/work + /home ?/", expected)

        expected = (
            OR(F({"project": "work"}), F({"project": "home"})),
            None,
            None,
            None,
            {"status": "done"},
        )
        self._assert_parse_result("/work + /home . ,done", expected)

    def test_boolean_selection_errors(self):
        for command in [
            "/work +",
            "+ /work",
            "+ +",
            "/work + + /home",
            "~",
            "/work ~",
        ]:
            self._assert_parse_error(command)

    def test_parent(self):
        expected = ({"parent": 73}, None, None, None, None)
        self._assert_parse_result("_73", expected)

        expected = ({"parent": 0}, None, None, None, None)
        self._assert_parse_result("_0", expected)

        expected = (
            None,
            None,
            None,
            None,
            {"title": "Child", "parent": 73},
        )
        self._assert_parse_result(". Child _73", expected)

        expected = ({"id": [42]}, None, None, None, {"parent": 0})
        self._assert_parse_result("42 . _0", expected)

    def test_group_sort(self):
        expected = ({}, "tag", "deadline", None, None)
        self._assert_parse_result("@ =^", expected)

        expected = ({}, "priority", "deadline", None, None)
        self._assert_parse_result("! =^", expected)

        expected = ({}, "status", "deadline", None, None)
        self._assert_parse_result(", =^", expected)

    def test_query(self):
        for key, value in self.config.token.items():
            if key in [
                "separator",
                "sort",
                "comment",
                "stdin",
                "description_fence",
            ]:
                continue
            if key == "query":
                key = "title"
            expected = ({"id": [42]}, None, None, [key], None)
            self._assert_parse_result(f"42 ?{value}", expected)

    def test_description(self):
        expected = (
            {"id": [42]},
            None,
            None,
            None,
            {"description": '"Details..."'},
        )
        self._assert_parse_result('42 . : "Details..."', expected)
        self._assert_parse_result('42 . :"Details..."', expected)

        expected = (
            {"id": [42]},
            None,
            None,
            None,
            {"description": "literal # and : characters"},
        )
        self._assert_parse_result(
            r"42 . : literal \# and \: characters", expected
        )
        self._assert_parse_result(
            r"42 . :literal \# and \: characters", expected
        )

        expected = ({"id": [42]}, None, None, None, {"description": ""})
        self._assert_parse_result("42 . :", expected)

        expected = (
            {"id": [42]},
            None,
            None,
            None,
            {"description": ":leading colon"},
        )
        self._assert_parse_result("42 . ::leading colon", expected)
        self._assert_parse_result("42 . : :leading colon", expected)

    def test_set_deadline(self):
        for value in ["+3d", "2mon", "oo"]:
            deadline = self.parser.datetime_parser.parse(value)
            if value == "oo":
                deadline = None
            deadline = {"deadline": deadline}
            expected = ({"id": [42]}, None, None, None, deadline)
            self._assert_parse_result(f"42 . ^{value}", expected)

    def test_id_range(self):
        expected = (
            {"id": list(range(1, 6))},
            None,
            None,
            None,
            {"status": "x"},
        )
        self._assert_parse_result("1..5 . ,x", expected)

    def test_number_prefixed_word_selection(self):
        expected = ({"title": "1x"}, None, None, None, None)
        self._assert_parse_result("1x", expected)

    def test_editor(self):
        expected = ({"project": "home"}, None, None, None, "editor")
        self._assert_parse_result("/home .", expected)
