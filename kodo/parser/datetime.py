import os

from datetime import time, datetime, timedelta
from dateutil.relativedelta import relativedelta

from parsimonious.grammar import Grammar
from parsimonious.nodes import NodeVisitor
from parsimonious.exceptions import ParseError, VisitationError

from .common import CommonMixin


class DateTimeParser(NodeVisitor, CommonMixin):
    weekday_map = {
        'mon': 0, 'tue': 1, 'wed': 2, 'thu': 3,
        'fri': 4, 'sat': 5, 'sun': 6,
        'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3,
        'friday': 4, 'saturday': 5, 'sunday': 6,
    }
    month_map = {
        'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'jun': 6, 'jul': 7,
        'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12,
        'january': 1, 'february': 2, 'march': 3, 'april': 4, 'may': 5,
        'june': 6, 'july': 7, 'august': 8, 'september': 9,
        'october': 10, 'november': 11, 'december': 12,
    }
    unit_map = {
        'year': 'years', 'y': 'years', 'month': 'months', 'M': 'months',
        'week': 'weeks', 'w': 'weeks', 'day': 'days', 'd': 'days',
        'hour': 'hours', 'h': 'hours', 'minute': 'minutes', 'm': 'minutes',
    }

    def __init__(self, reference_dt=None):
        super().__init__()
        self.reference_dt = reference_dt or datetime.now()
        root = os.path.dirname(__file__)
        with open(os.path.join(root, 'datetime.grammar'), 'r') as f:
            self.grammar = Grammar(f.read())

    @staticmethod
    def _datetime(*args, **kwargs) -> datetime:
        try:
            return datetime(*args, **kwargs)
        except ValueError as e:
            raise ValueError(f"Invalid date/time format") from e

    def visit_expression(self, node, visited_children):
        return self._visit_any_of(node, visited_children)

    def visit_relative_datetime(self, node, visited_children):
        _, count_units = visited_children
        if not isinstance(count_units[0], list):
            count_units = [count_units]  # A hack to undo generic_visit
        delta = timedelta()
        for count, unit, _ in count_units:
            count = int(count) if count else 1
            if count <= 0:
                raise ValueError("Count must be positive.")
            unit = self.unit_map[unit]
            if unit in ('years', 'months'):
                reldelta = relativedelta(**{unit: count})  # type: ignore
                new_date = self.reference_dt + reldelta
                delta = new_date - self.reference_dt
            else:
                delta += timedelta(**{unit: count})
        return self.reference_dt + delta

    def visit_date_time(self, node, visited_children):
        date, _, time = visited_children
        date = date or self.reference_dt.date()
        if time is None:
            time = datetime.max.time()
        dt = datetime.combine(date, time)
        if dt <= self.reference_dt:
            dt += timedelta(days=1)
        return dt

    def visit_time_date(self, node, visited_children):
        time, _, date = visited_children
        return self.visit_date_time(node, [date, _, time])

    def visit_date(self, node, visited_children):
        return self._visit_any_of_or_none(node, visited_children)

    def visit_absolute_date(self, node, visited_children):
        year, month, _, day = visited_children
        if year:
            year = int(year[0])
            if year < 100:
                year += 2000 if year < self.reference_dt.year % 100 else 1900
        else:
            year = self.reference_dt.year
        month = self.month_map[month.lower()]
        day = int(day)
        result = self._datetime(year, month, day).date()
        if result < self.reference_dt.date():
            result = self._datetime(year + 1, month, day).date()
        return result

    def visit_named_date(self, node, visited_children):
        text = node.text.lower()
        if text == 'today':
            return self.reference_dt.date()
        elif text == 'tomorrow':
            return self.reference_dt.date() + timedelta(days=1)
        raise ValueError(f"Unknown named date: {text}")

    def visit_end_date(self, node, visited_children):
        ordinal, end, _ = visited_children
        count = int(ordinal) if ordinal else 1
        if end in self.weekday_map:
            return self._end_weekday(self.weekday_map[end.lower()], count)
        elif end in self.month_map:
            return self._end_month(self.month_map[end.lower()], count)
        return self._end_unit(self.unit_map[end], count)

    def visit_time(self, node, visited_children):
        hour, minute, _, ampm = visited_children
        hour = int(hour)
        minute = int(minute[1]) if minute else 0
        if ampm:
            ampm = ampm.lower()
            if ampm == 'pm' and hour < 12:
                hour += 12
            elif ampm == 'am' and hour == 12:
                hour = 0
        if not (0 <= hour < 24 and 0 <= minute < 60):
            raise ValueError("Invalid time")
        return time(hour, minute)

    def _end_weekday(self, weekday, count):
        days_ahead = (weekday - self.reference_dt.weekday() + 7) % 7
        if days_ahead == 0:
            days_ahead = 7
        days_ahead += (count - 1) * 7
        return self.reference_dt.date() + timedelta(days=days_ahead)

    def _end_month(self, month, count):
        year = self.reference_dt.year
        next_year = month == self.reference_dt.month
        next_year = next_year and self.reference_dt.day > 1
        next_year = next_year or (month < self.reference_dt.month)
        if next_year:
            year += 1
        year += count - 1
        last_day = (
            self._datetime(year, month + 1, 1) - timedelta(days=1)
        ).day
        return self._datetime(year, month, last_day).date()

    def _end_unit(self, unit, count):
        count -= 1
        if unit == 'years':
            year = self.reference_dt.year
            return self._datetime(year + count, 12, 31).date()
        elif unit == 'months':
            next_month = self.reference_dt.replace(day=1)
            next_month += relativedelta(months=count)
            last_day = (
                next_month.replace(day=1) +
                relativedelta(months=1) -
                timedelta(days=1)
            ).day
            return next_month.replace(day=last_day).date()
        elif unit == 'weeks':
            days = 7 * count - (self.reference_dt.weekday() + 1) % 7
            return self.reference_dt.date() + timedelta(days=days)
        elif unit == 'days':
            return self.reference_dt.date() + timedelta(days=count)
        raise ValueError(f'Unexpected unit {unit!r}.')

    def generic_visit(self, node, visited_children):
        if len(visited_children) == 1:
            return visited_children[0]
        return visited_children or node.text or None


if __name__ == "__main__":
    test_date = datetime(2025, 5, 11, 11, 0, 0)
    parser = DateTimeParser(test_date)
    test_cases = [
        ('today',           datetime(2025, 5, 11, 23, 59, 59, 999999)),
        ('20:00',           datetime(2025, 5, 11, 20, 0, 0)),
        ('10am',            datetime(2025, 5, 12, 10, 0, 0)),
        ('week',            datetime(2025, 5, 11, 23, 59, 59, 999999)),
        ('w',               datetime(2025, 5, 11, 23, 59, 59, 999999)),
        ('tomorrow 6pm',    datetime(2025, 5, 12, 18, 0, 0)),
        ('tomorrow',        datetime(2025, 5, 12, 23, 59, 59, 999999)),
        ('2w',              datetime(2025, 5, 18, 23, 59, 59, 999999)),
        ('2tue',            datetime(2025, 5, 20, 23, 59, 59, 999999)),
        ('2fri',            datetime(2025, 5, 23, 23, 59, 59, 999999)),
        ('M',               datetime(2025, 5, 31, 23, 59, 59, 999999)),
        ('month',           datetime(2025, 5, 31, 23, 59, 59, 999999)),
        ('+M',              datetime(2025, 6, 11, 11, 0, 0, 0)),
        ('+1M',             datetime(2025, 6, 11, 11, 0, 0, 0)),
        ('+Md',             datetime(2025, 6, 12, 11, 0, 0, 0)),
        ('3month',          datetime(2025, 7, 31, 23, 59, 59, 999999)),
        ('february 21 8am', datetime(2026, 2, 21, 8, 0, 0)),
        ('feb 21',          datetime(2026, 2, 21, 23, 59, 59, 999999)),
        ('feb',             datetime(2026, 2, 28, 23, 59, 59, 999999)),
        ('1feb',            datetime(2026, 2, 28, 23, 59, 59, 999999)),
        ('3feb',            datetime(2028, 2, 29, 23, 59, 59, 999999)),
    ]
    error_cases = [
        'invalid',
        '12:99',
        '+feb',
        'feb 29',
    ]

    # Run positive test cases
    for text, expected in test_cases:
        result = parser.parse(text)
        fail_msg = f"FAIL: {text} => {result} (expected {expected})"
        assert result == expected, fail_msg
        print(f"PASS: {text:15} => {result}")
    for text in error_cases:
        try:
            result = parser.parse(text)
            print(
                f"FAIL: {text} should have raised an error "
                f"but returned {result}")
        except (ParseError, VisitationError):
            print(f"PASS: {text} correctly raised an error")
