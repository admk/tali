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

    def test_repeated_undo_flags_run_multiple_undo_actions(self):
        cli = self._cli("-uu")
        calls = []
        printed = []

        cli._data_dir = lambda: "db"
        cli.history_action = lambda db_dir, action: calls.append(
            (db_dir, action)
        ) or f"{action}-{len(calls)}"
        cli._print_results = lambda results: printed.extend(results)

        self.assertEqual(cli.main(), 0)
        self.assertEqual(calls, [("db", "undo"), ("db", "undo")])
        self.assertEqual(printed, ["undo-1", "undo-2"])

    def test_repeated_redo_flags_run_multiple_redo_actions(self):
        cli = self._cli("-rr")
        calls = []

        cli._data_dir = lambda: "db"
        cli.history_action = lambda db_dir, action: calls.append(
            (db_dir, action)
        ) or f"{action}-{len(calls)}"
        cli._print_results = lambda results: None

        self.assertEqual(cli.main(), 0)
        self.assertEqual(calls, [("db", "redo"), ("db", "redo")])

    def test_undo_and_redo_counts_are_mutually_exclusive(self):
        cli = self._cli("-ur")
        cli._data_dir = lambda: "db"

        with self.assertLogs("rich", level="ERROR") as logs:
            with self.assertRaises(SystemExit) as cm:
                cli.main()

        self.assertEqual(cm.exception.code, 1)
        self.assertIn(
            "Cannot use both --undo and --redo at the same time.",
            logs.output[0],
        )

    def test_nested_add_missing_title_stays_catchable(self):
        cli = self._cli(".", "/proj")
        book = TaskBook(cli.config, [])

        with self.assertRaisesRegex(
            ActionValueError, "Missing title in command"
        ):
            cli._process_action(book, cli.command, nested=True)

    def test_invalid_action_warns_and_is_skipped(self):
        cli = self._cli("2", ".", "@-shared")
        parent = TodoItem(1, "Parent", project="work", tags=["shared"])
        child = TodoItem(2, "Child", project="work", parent=1)
        book = TaskBook(cli.config, [parent, child])

        with self.assertLogs("rich", level="WARNING") as logs:
            result = cli._process_action(book, cli.command)

        self.assertEqual(result, [])
        self.assertEqual(book.todos[1].tags, ["shared"])
        self.assertEqual(book.todos[2].tags, [])
        self.assertIn("Skipping action", logs.output[0])
        self.assertIn("inherited tag @shared", logs.output[0])

    def test_editor_skips_invalid_action_and_continues_batch(self):
        cli = self._cli()
        parent = TodoItem(1, "Parent", project="work", tags=["shared"])
        child = TodoItem(2, "Child", project="work", parent=1)
        book = TaskBook(cli.config, [parent, child])
        self._set_editor_text(
            cli,
            """2 . @-shared
. Added
""",
        )

        with self.assertLogs("rich", level="WARNING") as logs:
            cli._process_editor_action([parent, child], book)

        self.assertEqual(book.todos[1].tags, ["shared"])
        self.assertEqual(book.todos[2].tags, [])
        self.assertEqual(book.todos[3].title, "Added")
        self.assertIn("Skipping action", logs.output[0])
        self.assertIn("inherited tag @shared", logs.output[0])

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

    def test_editor_fenced_description_persists_literal_lines(self):
        cli = self._cli()
        book = TaskBook(cli.config, [])
        self._set_editor_text(
            cli,
            '''. Task : """
first # literal
/project @tag
"""
''',
        )

        cli._process_editor_action([], book)

        self.assertEqual(book.todos[1].title, "Task")
        self.assertEqual(
            book.todos[1].description,
            "first # literal\n/project @tag",
        )

    def test_editor_indented_description_persists_with_nested_adds(self):
        cli = self._cli()
        book = TaskBook(cli.config, [])
        self._set_editor_text(
            cli,
            """. Parent
  : parent line 1
  : parent line 2
  . Child
    : child line
""",
        )

        cli._process_editor_action([], book)

        self.assertEqual(
            book.todos[1].description, "parent line 1\nparent line 2"
        )
        self.assertEqual(book.todos[2].title, "Child")
        self.assertEqual(book.todos[2].parent, 1)
        self.assertEqual(book.todos[2].description, "child line")

    def test_editor_multiline_description_noop_roundtrip(self):
        cli = self._cli()
        cli._edit_file = lambda path: None
        todo = TodoItem(
            78,
            "Task",
            description="first # literal\n/project @tag",
            tags=["bug"],
        )

        self.assertEqual(cli.editor_action([todo]), [])

    def test_editor_multiline_description_uses_configured_fence(self):
        cli = self._cli()
        cli.config.token.description_fence = "END"
        cli._edit_file = lambda path: None
        todo = TodoItem(
            78,
            "Task",
            description="first # literal\n/project @tag",
            tags=["bug"],
        )

        rendered = strip_rich(
            cli.renderer.render({None: [todo]}, "id", idempotent=True)
        )

        self.assertIn(": END\nfirst # literal\n/project @tag\nEND", rendered)
        self.assertEqual(cli.editor_action([todo]), [])

    def test_idempotent_render_escapes_custom_boolean_tokens(self):
        cli = self._cli("-i")
        cli.config.token["or"] = "|"
        cli.config.token["not"] = "%"
        cli.config.token.open_paren = "<"
        cli.config.token.close_paren = ">"
        todo = TodoItem(78, "Use | %<brackets>", tags=["bug"])

        rendered = strip_rich(
            cli.renderer.render({None: [todo]}, "id", idempotent=True)
        )

        self.assertIn(r"Use \| \%\<brackets\>", rendered)

    def test_cli_list_multiline_description_uses_marker(self):
        cli = self._cli()
        todo = TodoItem(
            78,
            "Task",
            description="first line\nsecond line",
        )

        rendered = strip_rich(cli.renderer.render({None: [todo]}, "id"))

        self.assertEqual(len(rendered.splitlines()), 1)
        self.assertIn("first line ↳ second line", rendered)

    def test_cli_list_multiline_description_marker_is_configurable(self):
        cli = self._cli()
        cli.config.item.description.newline_marker = "NEXT"
        todo = TodoItem(
            78,
            "Task",
            description="first line\nsecond line",
        )

        rendered = strip_rich(cli.renderer.render({None: [todo]}, "id"))

        self.assertEqual(len(rendered.splitlines()), 1)
        self.assertIn("first line NEXT second line", rendered)

    def test_editor_nested_add_under_existing_multiline_parent(self):
        cli = self._cli()
        parent = TodoItem(
            73,
            "Parent",
            description="parent line 1\nparent line 2",
            project="work",
        )
        book = TaskBook(cli.config, [parent])

        def edit_file(path):
            with open(path, "a") as f:
                f.write("  . Child\n")

        cli._edit_file = edit_file

        cli._process_editor_action([parent], book)

        self.assertEqual(book.todos[74].title, "Child")
        self.assertEqual(book.todos[74].parent, 73)
        self.assertEqual(book.todos[74].project, "work")

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

    def test_boolean_or_selection_matches_either_clause(self):
        cli = self._cli("/work", "+", "/home")
        book = TaskBook(
            cli.config,
            [
                TodoItem(1, "Work", project="work"),
                TodoItem(2, "Home", project="home"),
                TodoItem(3, "Other", project="other"),
            ],
        )

        result = cli._process_action(book, cli.command)[0]

        self.assertEqual({todo.id for todo in result.flatten()}, {1, 2})

    def test_boolean_or_respects_implicit_and_precedence(self):
        cli = self._cli("/work", "+", "/home", "@urgent")
        book = TaskBook(
            cli.config,
            [
                TodoItem(1, "Work", project="work"),
                TodoItem(2, "Urgent home", project="home", tags=["urgent"]),
                TodoItem(3, "Plain home", project="home"),
                TodoItem(4, "Other urgent", project="other", tags=["urgent"]),
            ],
        )

        result = cli._process_action(book, cli.command)[0]

        self.assertEqual({todo.id for todo in result.flatten()}, {1, 2})

    def test_boolean_parentheses_group_or_before_implicit_and(self):
        cli = self._cli("(/work", "+", "/home)", "@urgent")
        book = TaskBook(
            cli.config,
            [
                TodoItem(1, "Plain work", project="work"),
                TodoItem(2, "Urgent work", project="work", tags=["urgent"]),
                TodoItem(3, "Urgent home", project="home", tags=["urgent"]),
                TodoItem(4, "Plain home", project="home"),
                TodoItem(5, "Other urgent", project="other", tags=["urgent"]),
            ],
        )

        result = cli._process_action(book, cli.command)[0]

        self.assertEqual({todo.id for todo in result.flatten()}, {2, 3})

    def test_boolean_not_selection_excludes_matches(self):
        cli = self._cli("/work", "~@waiting")
        book = TaskBook(
            cli.config,
            [
                TodoItem(1, "Ready", project="work"),
                TodoItem(2, "Blocked", project="work", tags=["waiting"]),
                TodoItem(3, "Home", project="home"),
            ],
        )

        result = cli._process_action(book, cli.command)[0]

        self.assertEqual([todo.id for todo in result.flatten()], [1])

    def test_boolean_parenthesized_not_excludes_grouped_or(self):
        cli = self._cli("/work", "~(@waiting", "+", "@blocked)")
        book = TaskBook(
            cli.config,
            [
                TodoItem(1, "Ready", project="work"),
                TodoItem(2, "Waiting", project="work", tags=["waiting"]),
                TodoItem(3, "Blocked", project="work", tags=["blocked"]),
                TodoItem(4, "Home", project="home"),
            ],
        )

        result = cli._process_action(book, cli.command)[0]

        self.assertEqual([todo.id for todo in result.flatten()], [1])

    def test_boolean_selection_can_batch_edit(self):
        cli = self._cli("/work", "+", "/home", ".", ",done")
        book = TaskBook(
            cli.config,
            [
                TodoItem(1, "Work", project="work"),
                TodoItem(2, "Home", project="home"),
                TodoItem(3, "Other", project="other"),
            ],
        )

        cli._process_action(book, cli.command)

        self.assertEqual(book.todos[1].status, "done")
        self.assertEqual(book.todos[2].status, "done")
        self.assertEqual(book.todos[3].status, "pending")
