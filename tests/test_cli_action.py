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

    def _set_editor_text(self, cli, text):
        def edit_file(path):
            with open(path, "w") as f:
                f.write(text)

        cli._edit_file = edit_file

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

    def test_editor_nested_adds_resolve_new_parent_ids(self):
        cli = self._cli()
        book = TaskBook(cli.config, [])
        self._set_editor_text(
            cli,
            """. /work Parent
  . Child
  . Sibling
    . Grandchild
""",
        )

        cli._process_editor_action([], book)

        self.assertEqual(book.todos[1].title, "Parent")
        self.assertIsNone(book.todos[1].parent)
        self.assertEqual(book.todos[2].title, "Child")
        self.assertEqual(book.todos[2].parent, 1)
        self.assertEqual(book.todos[2].project, "work")
        self.assertEqual(book.todos[3].title, "Sibling")
        self.assertEqual(book.todos[3].parent, 1)
        self.assertEqual(book.todos[4].title, "Grandchild")
        self.assertEqual(book.todos[4].parent, 3)

    def test_editor_nested_add_under_existing_parent(self):
        cli = self._cli()
        parent = TodoItem(73, "Parent", project="work")
        book = TaskBook(cli.config, [parent])

        def edit_file(path):
            with open(path, "a") as f:
                f.write("  . Child\n")

        cli._edit_file = edit_file

        cli._process_editor_action([parent], book)

        self.assertEqual(book.todos[74].title, "Child")
        self.assertEqual(book.todos[74].parent, 73)
        self.assertEqual(book.todos[74].project, "work")

    def test_editor_nested_adds_mix_with_prefix_sharing(self):
        cli = self._cli()
        book = TaskBook(cli.config, [])
        self._set_editor_text(
            cli,
            """. /work
  Parent
    @urgent
      . Child
      . Sibling
    . Detail
      @tag
        leaf
""",
        )

        cli._process_editor_action([], book)

        self.assertEqual(book.todos[1].title, "Parent")
        self.assertEqual(book.todos[1].project, "work")
        self.assertIsNone(book.todos[1].parent)
        self.assertEqual(book.todos[2].title, "Child")
        self.assertEqual(book.todos[2].tags, ["urgent"])
        self.assertEqual(book.todos[2].parent, 1)
        self.assertEqual(book.todos[3].title, "Sibling")
        self.assertEqual(book.todos[3].tags, ["urgent"])
        self.assertEqual(book.todos[3].parent, 1)
        self.assertEqual(book.todos[4].title, "Detail leaf")
        self.assertEqual(book.todos[4].tags, ["tag"])
        self.assertEqual(book.todos[4].parent, 1)

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

    def test_query_parent_renders_parent_id(self):
        cli = self._cli("80", "?_")
        child = TodoItem(80, "Child", project="work", parent=79)
        book = TaskBook(cli.config, [child])

        result = cli._process_action(book, cli.command)[0]
        text = cli.renderer.render_result(result)

        self.assertEqual(text, "79")

    def test_query_parent_renders_null_without_parent(self):
        cli = self._cli("80", "?_")
        todo = TodoItem(80, "Task", project="work")
        book = TaskBook(cli.config, [todo])

        result = cli._process_action(book, cli.command)[0]
        text = cli.renderer.render_result(result)

        self.assertEqual(text, "null")

    def test_query_id_renders_integer(self):
        cli = self._cli("80", "?..")
        todo = TodoItem(80, "Task", project="work")
        book = TaskBook(cli.config, [todo])

        result = cli._process_action(book, cli.command)[0]
        text = cli.renderer.render_result(result)

        self.assertEqual(text, "80")
