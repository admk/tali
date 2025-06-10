import unittest
from datetime import datetime

from tali.parser.datetime import DateTimeParseError, DateTimeParser


class TestDateTimeParser(unittest.TestCase):
    def setUp(self):
        self.test_date = datetime(2025, 5, 11, 11, 0, 0)
        self.parser = DateTimeParser(self.test_date)

    def _assert_parse_result(self, text, expected):
        result = self.parser.parse(text)
        self.assertEqual(result, expected)

    def _assert_parse_error(self, text):
        with self.assertRaises(DateTimeParseError):
            self.parser.parse(text)

    def test_absolute_dates(self):
        test_cases = [
            ("today", datetime(2025, 5, 11, 23, 59, 59, 999999)),
            ("tomorrow", datetime(2025, 5, 12, 23, 59, 59, 999999)),
            ("tomorrow 6pm", datetime(2025, 5, 12, 18, 0, 0)),
            ("february 21 8am", datetime(2026, 2, 21, 8, 0, 0)),
            ("feb 21", datetime(2026, 2, 21, 23, 59, 59, 999999)),
        ]
        for text, expected in test_cases:
            with self.subTest(text=text):
                self._assert_parse_result(text, expected)

    def test_end_of_dates(self):
        test_cases = [
            ("week", datetime(2025, 5, 11, 23, 59, 59, 999999)),
            ("w", datetime(2025, 5, 11, 23, 59, 59, 999999)),
            ("2w", datetime(2025, 5, 18, 23, 59, 59, 999999)),
            ("mon", datetime(2025, 5, 12, 23, 59, 59, 999999)),
            ("2tue", datetime(2025, 5, 20, 23, 59, 59, 999999)),
            ("2fri", datetime(2025, 5, 23, 23, 59, 59, 999999)),
            ("M", datetime(2025, 5, 31, 23, 59, 59, 999999)),
            ("month", datetime(2025, 5, 31, 23, 59, 59, 999999)),
            ("3month", datetime(2025, 7, 31, 23, 59, 59, 999999)),
            ("1feb", datetime(2026, 2, 28, 23, 59, 59, 999999)),
            ("3feb", datetime(2028, 2, 29, 23, 59, 59, 999999)),
        ]
        for text, expected in test_cases:
            with self.subTest(text=text):
                self._assert_parse_result(text, expected)

    def test_relative_offsets(self):
        test_cases = [
            ("+M", datetime(2025, 6, 11, 11, 0, 0)),
            ("+1M", datetime(2025, 6, 11, 11, 0, 0)),
            ("+Md", datetime(2025, 6, 12, 11, 0, 0)),
            ("+M1d", datetime(2025, 6, 12, 11, 0, 0)),
        ]
        for text, expected in test_cases:
            with self.subTest(text=text):
                self._assert_parse_result(text, expected)

    def test_times(self):
        test_cases = [
            ("20:00", datetime(2025, 5, 11, 20, 0, 0)),
            ("10am", datetime(2025, 5, 12, 10, 0, 0)),
        ]
        for text, expected in test_cases:
            with self.subTest(text=text):
                self._assert_parse_result(text, expected)

    def test_invalid_inputs(self):
        error_cases = [
            "invalid",
            "12:99",
            "+feb",
            "feb 29",  # should return leap year?
        ]
        for text in error_cases:
            with self.subTest(text=text):
                self._assert_parse_error(text)

    def test_distant_time(self):
        test_cases = [
            ("oo", datetime.max),
            ("+oo", datetime.max),
            ("-oo", datetime.combine(datetime.min.date(), datetime.max.time())),
        ]
        for text, expected in test_cases:
            with self.subTest(text=text):
                self._assert_parse_result(text, expected)
