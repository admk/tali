import unittest
from datetime import datetime
from unittest.mock import patch

from box import Box
from dateutil.relativedelta import relativedelta

from tali.book import TaskBook, TodoItem


class TestDeadlineAction(unittest.TestCase):
    def test_relative_deadline_uses_existing_deadline(self):
        todo = TodoItem(
            1,
            "task",
            deadline=datetime(2025, 5, 20, 9, 0, 0),
        )
        book = TaskBook(Box({}), [todo])

        book.action([todo], {"deadline": relativedelta(days=3, hours=2)})

        self.assertEqual(
            book.todos[1].deadline,
            datetime(2025, 5, 23, 11, 0, 0),
        )

    def test_relative_deadline_uses_now_when_deadline_absent(self):
        class FixedDateTime(datetime):
            @classmethod
            def now(cls):
                return cls(2025, 5, 20, 9, 0, 0)

        todo = TodoItem(1, "task")
        book = TaskBook(Box({}), [todo])

        with patch("tali.book.book.datetime", FixedDateTime):
            deadline = book.deadline(todo, relativedelta(days=3, hours=2))

        self.assertEqual(deadline, datetime(2025, 5, 23, 11, 0, 0))
