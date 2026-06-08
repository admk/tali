import unittest

from tali.book.item import TodoItem
from tali.cli import CLI
from tali.parser.editor import (
    escape_command_text,
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
        self.assertEqual(strip_comments(lines), [r"task title \# not a comment"])

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
