import unittest

from tali.parser.indent import process_prefix_sharing_lines


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
            "something else"
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
            "second prefix continuation"
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
        expected = [
            "a b c d",
            "a e f"
        ]
        self.run_test(input_text, expected)

    def test_nothing_changed(self):
        input_text = """
        no changes needed
        this is just to test
        identical lines
        """
        expected = [l.strip() for l in input_text.splitlines() if l.strip()]
        self.run_test(input_text, expected)

    def run_test(self, input_text, expected):
        lines = input_text.splitlines()
        result = process_prefix_sharing_lines(lines)
        self.assertEqual(result, expected)
