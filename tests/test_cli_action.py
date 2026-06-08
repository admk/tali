import tempfile
import unittest

from tali.book import ActionValueError, TaskBook
from tali.cli import CLI
from tali.common import os_env_swap


class TestCLIAction(unittest.TestCase):
    def _cli(self, *args):
        with tempfile.TemporaryDirectory() as data_home:
            with os_env_swap(XDG_DATA_HOME=data_home):
                return CLI(["tali", *args])

    def test_add_missing_title_exits_cleanly(self):
        cli = self._cli(".", "/proj")
        book = TaskBook(cli.config, [])

        with self.assertLogs("rich", level="ERROR") as logs:
            with self.assertRaises(SystemExit) as cm:
                cli._process_action(book, cli.command)

        self.assertEqual(cm.exception.code, 1)
        self.assertIn("Missing title in command: '. /proj'.", logs.output[0])

    def test_nested_add_missing_title_stays_catchable(self):
        cli = self._cli(".", "/proj")
        book = TaskBook(cli.config, [])

        with self.assertRaisesRegex(
            ActionValueError, "Missing title in command"
        ):
            cli._process_action(book, cli.command, nested=True)
