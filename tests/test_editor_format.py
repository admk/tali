import unittest

from tali.book.item import TodoItem
from tali.cli import CLI
from tali.parser.editor import (
    EditorCommand,
    EditorSyntaxError,
    escape_command_text,
    process_editor_commands,
    process_prefix_sharing_lines,
    strip_comments,
    unescape_command_text,
)


class TestStripComments(unittest.TestCase):
    def test_strip_unescaped_comment(self):
        lines = ["task title # editor note"]
        self.assertEqual(strip_comments(lines), ["task title"])

    def test_preserve_escaped_comment_token(self):
        lines = [r"task title \# not a comment # editor note"]
        self.assertEqual(
            strip_comments(lines), [r"task title \# not a comment"]
        )

    def test_preserve_comment_token_inside_quotes(self):
        lines = ['task "issue #42" # editor note']
        self.assertEqual(strip_comments(lines), ['task "issue #42"'])


class TestEditorEscaping(unittest.TestCase):
    def test_escape_text_protects_comment_tokens(self):
        tokens = [".", "#", ":", "/", "@"]
        text = r"Fix /project @tag #42 . keep \# literal"

        escaped = escape_command_text(text, tokens)

        self.assertEqual(
            escaped,
            r"Fix \/project \@tag \#42 \. keep \\\# literal",
        )
        self.assertEqual(strip_comments([escaped]), [escaped])
        self.assertEqual(unescape_command_text(escaped, tokens), text)


class TestEditorAction(unittest.TestCase):
    def test_noop_editor_escapes_raw_comment_token(self):
        cli = CLI(["tali"])
        cli._edit_file = lambda path: None
        todo = TodoItem(
            78,
            "some special characters such as # and : are not escaped",
            tags=["bug"],
        )

        self.assertEqual(cli.editor_action([todo]), [])

    def test_noop_editor_preserves_escaped_comment_token(self):
        cli = CLI(["tali"])
        cli._edit_file = lambda path: None
        todo = TodoItem(
            78,
            r"some special characters such as \# and \: are not escaped",
            tags=["bug"],
        )

        self.assertEqual(cli.editor_action([todo]), [])


class TestProcessIndent(unittest.TestCase):
    def test_basic_case(self):
        input_text = """hello
  world
this is
  great
  awesome
    stuff
    thing
something else"""
        expected = [
            "hello world",
            "this is great",
            "this is awesome stuff",
            "this is awesome thing",
            "something else",
        ]
        self.run_test(input_text, expected)

    def test_varied_indentation(self):
        input_text = """
first
    second
    third
        fourth
second prefix
    continuation"""
        expected = [
            "first second",
            "first third fourth",
            "second prefix continuation",
        ]
        self.run_test(input_text, expected)

    def test_empty_lines(self):
        input_text = """start

    middle

end"""
        expected = ["start middle", "end"]
        self.run_test(input_text, expected)

    def test_single_line(self):
        input_text = """just one line"""
        expected = ["just one line"]
        self.run_test(input_text, expected)

    def test_deep_nesting(self):
        input_text = """
a
  b
    c
      d
  e
    f"""
        expected = ["a b c d", "a e f"]
        self.run_test(input_text, expected)

    def test_nothing_changed(self):
        input_text = """
        no changes needed
        this is just to test
        identical lines
        """
        expected = [
            line.strip() for line in input_text.splitlines() if line.strip()
        ]
        self.run_test(input_text, expected)

    def run_test(self, input_text, expected):
        lines = input_text.splitlines()
        result = process_prefix_sharing_lines(lines)
        self.assertEqual(result, expected)


class TestProcessEditorCommands(unittest.TestCase):
    def test_fenced_description_block(self):
        lines = [
            '. Task : """',
            "first # literal",
            "/project @tag",
            '"""',
        ]

        result = process_editor_commands(lines, comment_token="#")

        self.assertEqual(
            result,
            [EditorCommand(". Task : first \\# literal\n\\/project \\@tag")],
        )

    def test_fenced_description_accepts_compact_start(self):
        lines = ['. Task :"""', "first", "second", '"""']

        result = process_editor_commands(lines)

        self.assertEqual(result, [EditorCommand(". Task : first\nsecond")])

    def test_fenced_description_uses_configured_fence(self):
        lines = [". Task : END", "first", "second", "END"]

        result = process_editor_commands(lines, description_fence="END")

        self.assertEqual(result, [EditorCommand(". Task : first\nsecond")])

    def test_fence_inside_one_line_description_is_literal(self):
        lines = ['. Task : hello """ world """']

        result = process_editor_commands(lines)

        self.assertEqual(
            result, [EditorCommand('. Task : hello """ world """')]
        )

    def test_unclosed_fenced_description_errors(self):
        lines = ['. Task : """', "first"]

        with self.assertRaises(EditorSyntaxError):
            process_editor_commands(lines)

    def test_indented_description_lines_fold_into_parent(self):
        lines = """
. Task
  : first
  : second
""".splitlines()

        result = process_editor_commands(lines)

        self.assertEqual(result, [EditorCommand(". Task : first\nsecond")])

    def test_indented_description_lines_mix_with_nested_adds(self):
        lines = """
. Parent
  : parent line 1
  : parent line 2
  . Child
    : child line
""".splitlines()

        result = process_editor_commands(lines)

        self.assertEqual(
            result,
            [
                EditorCommand(". Parent : parent line 1\nparent line 2"),
                EditorCommand(". Child : child line", parent_ref=0),
            ],
        )

    def test_nested_add_lines_track_parent_refs(self):
        lines = """
. /work Parent
  . Child
  . Sibling
    . Grandchild
""".splitlines()

        result = process_editor_commands(lines)

        self.assertEqual(
            result,
            [
                EditorCommand(". /work Parent"),
                EditorCommand(". Child", parent_ref=0),
                EditorCommand(". Sibling", parent_ref=0),
                EditorCommand(". Grandchild", parent_ref=2),
            ],
        )

    def test_prefix_sharing_still_handles_plain_indents(self):
        lines = """
. /home/grocery ^today buy
  @fruit
    apples
    oranges
  milk
""".splitlines()

        result = process_editor_commands(lines)

        self.assertEqual(
            result,
            [
                EditorCommand(". /home/grocery ^today buy @fruit apples"),
                EditorCommand(". /home/grocery ^today buy @fruit oranges"),
                EditorCommand(". /home/grocery ^today buy milk"),
            ],
        )

    def test_nested_add_lines_can_mix_prefix_sharing(self):
        lines = """
. /work
  Parent
    @urgent
      . Child
      . Sibling
    . Detail
      @tag
        leaf
""".splitlines()

        result = process_editor_commands(lines)

        self.assertEqual(
            result,
            [
                EditorCommand(". /work Parent"),
                EditorCommand(". @urgent Child", parent_ref=0),
                EditorCommand(". @urgent Sibling", parent_ref=0),
                EditorCommand(". Detail @tag leaf", parent_ref=0),
            ],
        )
