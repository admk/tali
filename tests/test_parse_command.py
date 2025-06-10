import os
import unittest
from datetime import datetime

import yaml
from box import Box

from tali import __toolname__ as _NAME
from tali.common import format_config
from tali.parser.command import CommandParseError, CommandParser


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

    def test_edit(self):
        expected = ({"ids": [42]}, None, None, None, {"status": ""})
        self._assert_parse_result("42 . ,", expected)
        expected = ({"ids": [42]}, None, None, None, {"status": "x"})
        self._assert_parse_result("42 . ,x", expected)
        expected = ({"ids": [42]}, None, None, None, {"status": "done"})
        self._assert_parse_result("42 . ,done", expected)
        expected = ({"ids": [42]}, None, None, None, {"priority": "h"})
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
            {"ids": [42]},
            None,
            None,
            None,
            {"title": "New title", "project": "newproject", "status": "n"},
        )
        self._assert_parse_result("42 . New title /newproject ,n", expected)

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

    def test_group_sort(self):
        expected = ({}, "tag", "deadline", None, None)
        self._assert_parse_result("@ =^", expected)

    def test_query(self):
        for key, value in self.config.token.items():
            if key in ["separator", "sort", "description", "stdin"]:
                continue
            if key == "query":
                key = "title"
            expected = ({"ids": [42]}, None, None, [key], None)
            self._assert_parse_result(f"42 ?{value}", expected)

    def test_description(self):
        expected = (
            {"ids": [42]},
            None,
            None,
            None,
            {"description": '"Details..."'},
        )
        self._assert_parse_result('42 . : "Details..."', expected)

    def test_set_deadline(self):
        for value in ["+3d", "2mon", "oo"]:
            deadline = self.parser.datetime_parser.parse(value)
            if value == "oo":
                deadline = None
            deadline = {"deadline": deadline}
            expected = ({"ids": [42]}, None, None, None, deadline)
            self._assert_parse_result(f"42 . ^{value}", expected)

    def test_id_range(self):
        expected = (
            {"ids": list(range(1, 6))},
            None,
            None,
            None,
            {"status": "x"},
        )
        self._assert_parse_result("1..5 . ,x", expected)

    def test_editor(self):
        expected = ({"project": "home"}, None, None, None, "editor")
        self._assert_parse_result("/home .", expected)
