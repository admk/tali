import os
from datetime import datetime, time, timedelta

from dateutil.relativedelta import relativedelta
from parsimonious.exceptions import ParseError, VisitationError
from parsimonious.grammar import Grammar
from parsimonious.nodes import NodeVisitor

from .common import CommonMixin, ParserError as CommonParserError


class DateTimeParseError(CommonParserError):
    pass


class DateTimeSyntaxError(DateTimeParseError):
    """An exception raised when a date time syntax is invalid."""


class DateTimeSemanticError(DateTimeParseError):
    """An exception raised when a date time is semantically invalid."""


class DateTimeParser(NodeVisitor, CommonMixin):
    weekday_map = {
        "mon": 0,
        "tue": 1,
        "wed": 2,
        "thu": 3,
        "fri": 4,
        "sat": 5,
        "sun": 6,
        "monday": 0,
        "tuesday": 1,
        "wednesday": 2,
        "thursday": 3,
        "friday": 4,
        "saturday": 5,
        "sunday": 6,
    }
    month_map = {
        "january": 1,
        "february": 2,
        "march": 3,
        "april": 4,
        "may": 5,
        "june": 6,
        "july": 7,
        "august": 8,
        "september": 9,
        "october": 10,
        "november": 11,
        "december": 12,
    }
    unit_map = {
        "year": "years",
        "y": "years",
        "month": "months",
        "M": "months",
        "week": "weeks",
        "w": "weeks",
        "day": "days",
        "d": "days",
        "hour": "hours",
        "h": "hours",
        "minute": "minutes",
        "m": "minutes",
    }

    def __init__(self, now=None):
        super().__init__()
        self.now = now or datetime.now()
        root = os.path.dirname(__file__)
        with open(os.path.join(root, "datetime.grammar"), "r") as f:
            self.grammar = Grammar(f.read())

    def parse(self, text: str, pos: int = 0) -> datetime:
        try:
            ast = self.grammar.parse(text.strip())
        except ParseError as e:
            raise DateTimeSyntaxError(e) from e
        try:
            return self.visit(ast)
        except VisitationError as e:
            raise DateTimeSemanticError(e) from e

    @staticmethod
    def _datetime(*args, **kwargs) -> datetime:
        try:
            return datetime(*args, **kwargs)
        except ValueError as e:
            raise DateTimeSemanticError(f"Invalid datetime format: {e}") from e

    def visit_datetime_expression(self, node, visited_children):
        return self._visit_any_of(node, visited_children)

    def visit_relative_datetime(self, node, visited_children):
        pm, count_units = visited_children
        units = {u: -c if pm == "-" else c for c, u in count_units}
        return self.now + relativedelta(**units)

    def visit_count_unit(self, node, visited_children):
        ordinal, unit, _ = visited_children
        count = int(ordinal[0]) if ordinal else 1
        unit = self.unit_map[unit]
        return count, unit

    def _visit_date_time(self, date, time):
        time = time or datetime.max.time()
        if date:
            return datetime.combine(date, time)
        date = self.now.date()
        dt = datetime.combine(date, time)
        if dt < self.now:
            dt += relativedelta(days=1)
        return dt

    def visit_date_time(self, node, visited_children):
        date, _, time = visited_children
        time = time[0] if time else None
        return self._visit_date_time(date, time)

    def visit_time_date(self, node, visited_children):
        time, _, date = visited_children
        date = date[0] if date else None
        return self._visit_date_time(date, time)

    visit_date = CommonMixin._visit_any_of_or_none

    def visit_time(self, node, visited_children):
        hour, minute, _, ampm = visited_children
        minute = minute[0][1] if minute and minute[0] else 0
        if ampm:
            ampm = ampm[0].lower()
            if ampm == "pm" and hour < 12:
                hour += 12
            elif ampm == "am" and hour == 12:
                hour = 0
        if not (0 <= hour < 24 and 0 <= minute < 60):
            raise DateTimeSemanticError(f"Invalid time: {node.text!r}")
        return time(hour, minute)

    def visit_absolute_date(self, node, visited_children):
        year, month, _, day = visited_children
        month = self.month_map[month.lower()]
        if not year:
            year = self.now.year
            dt = self._datetime(year, month, day)
            if dt < self.now:
                dt += relativedelta(years=1)
            return dt
        year = year[0][0]
        if year < 100:
            year += 2000
        return self._datetime(year, month, day)

    def visit_end_date(self, node, visited_children):
        ordinal, end, _ = visited_children
        count = ordinal[0] if ordinal else 1
        if end in self.weekday_map:
            return self._end_weekday(self.weekday_map[end.lower()], count)
        elif end in self.month_map:
            return self._end_month(self.month_map[end.lower()], count)
        return self._end_unit(self.unit_map[end], count)

    def _end_weekday(self, weekday, count):
        days_ahead = (weekday - self.now.weekday() + 7) % 7
        if days_ahead == 0:
            days_ahead = 7
        days_ahead += (count - 1) * 7
        return self.now.date() + timedelta(days=days_ahead)

    def _end_month(self, month, count):
        year = self.now.year
        next_year = month == self.now.month
        next_year = next_year and self.now.day > 1
        next_year = next_year or (month < self.now.month)
        if next_year:
            year += 1
        year += count - 1
        last_day = (
            self._datetime(year, month, 1)
            + relativedelta(months=1)
            - timedelta(days=1)
        )
        return self._datetime(year, month, last_day.day).date()

    def _end_unit(self, unit, count):
        count -= 1
        if unit == "years":
            year = self.now.year
            return self._datetime(year + count, 12, 31).date()
        elif unit == "months":
            next_month = self.now.replace(day=1)
            next_month += relativedelta(months=count)
            last_day = (
                next_month.replace(day=1)
                + relativedelta(months=1)
                - timedelta(days=1)
            ).day
            return next_month.replace(day=last_day).date()
        elif unit == "weeks":
            days = 7 * count + (6 - self.now.weekday())
            return self.now.date() + timedelta(days=days)
        elif unit == "days":
            return self.now.date() + timedelta(days=count)
        raise DateTimeSemanticError(f"Unexpected unit {unit!r}.")

    visit_end = CommonMixin._visit_any_of

    def visit_named_date(self, node, visited_children):
        text = node.text.lower()
        if text == "today":
            return self.now.date()
        if text == "tomorrow":
            return self.now.date() + timedelta(days=1)
        if text in ("oo", "+oo"):  # distant future
            return datetime.max.date()
        if text == "-oo":  # distant past
            return datetime.min.date()
        raise DateTimeSemanticError(f"Unexpected named date {node.text!r}.")

    visit_year = visit_day = visit_day = visit_hour = visit_minute = (
        visit_ordinal
    ) = CommonMixin._visit_int

    def visit_unit(self, node, visited_children):
        return node.children[0].expr_name.replace("unit_", "")

    def visit_month(self, node, visited_children):
        return node.children[0].expr_name

    def visit_weekday(self, node, visited_children):
        return node.children[0].expr_name

    visit_pm = visit_ampm = CommonMixin._visit_str

    def generic_visit(self, node, visited_children):
        return visited_children
