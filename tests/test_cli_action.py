import tempfile
import unittest

from tali.book import ActionValueError, TaskBook, TodoItem
from tali.cli import CLI
from tali.common import os_env_swap
from tali.render.common import strip_rich


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

    def test_add_child_command_persists_parent_and_project(self):
        cli = self._cli(".", "test", "_73")
        book = TaskBook(
            cli.config,
            [TodoItem(73, "Parent", project="work")],
        )

        result = cli._process_action(book, cli.command)[0]
        child = result.items[0]

        self.assertEqual(child.id, 74)
        self.assertEqual(child.title, "test")
        self.assertEqual(child.parent, 73)
        self.assertEqual(child.project, "work")
        self.assertEqual(book.todos[74].parent, 73)

    def test_default_cli_rendering_nests_subitems_in_project_group(self):
        cli = self._cli()
        parent = TodoItem(73, "Parent", project="work")
        child = TodoItem(74, "Child", project="work", parent=73)
        book = TaskBook(cli.config, [parent, child])

        result = book.select(
            None,
            cli.config.view.group_by,
            cli.config.view.sort_by,
        )
        text = strip_rich(cli.renderer.render_result(result))
        lines = text.splitlines()

        self.assertTrue(lines[0].startswith("/work"))
        self.assertTrue(lines[1].startswith("  73."))
        self.assertTrue(lines[2].startswith("    74."))
        self.assertNotIn("_73", lines[2])

    def test_tag_and_id_command_matches_child_with_parent_tag(self):
        cli = self._cli("@feat", "80")
        parent = TodoItem(79, "Parent", project="work", tags=["feat"])
        child = TodoItem(80, "Child", project="work", parent=79)
        book = TaskBook(cli.config, [parent, child])

        result = cli._process_action(book, cli.command)[0]

        self.assertEqual([todo.id for todo in result.flatten()], [80])
