from datetime import time, datetime, timedelta
from dateutil.relativedelta import relativedelta

from parsimonious.grammar import Grammar
from parsimonious.nodes import NodeVisitor
from parsimonious.exceptions import ParseError, VisitationError


class DateTimeParser(NodeVisitor):
    def __init__(self, reference_date=None):
        super().__init__()
        self.reference_date = reference_date or datetime.now()
        self.weekday_map = {
            'mon': 0, 'tue': 1, 'wed': 2, 'thu': 3,
            'fri': 4, 'sat': 5, 'sun': 6,
            'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3,
            'friday': 4, 'saturday': 5, 'sunday': 6,
        }
        self.month_map = {
            'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'jun': 6, 'jul': 7,
            'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12,
            'january': 1, 'february': 2, 'march': 3, 'april': 4, 'may': 5,
            'june': 6, 'july': 7, 'august': 8, 'september': 9,
            'october': 10, 'november': 11, 'december': 12,
        }
        self.unit_map = {
            'year': 'years', 'y': 'years', 'month': 'months', 'M': 'months',
            'week': 'weeks', 'w': 'weeks', 'day': 'days', 'd': 'days',
            'hour': 'hours', 'h': 'hours', 'minute': 'minutes', 'm': 'minutes',
        }
        self.grammar = Grammar(r"""
            expression = relative_datetime / date_time / time_date
            date_time = date ws? time?
            time_date = time ws? date?
            date = absolute_date / named_date / end_date
            time = hour (":" minute)? ws? ampm?
            ampm = "am" / "pm" / "AM" / "PM"
            hour = ~r"[0-2]?[0-9]"
            minute = ~r"[0-5][0-9]"
            absolute_date = (year date_sep)? month date_sep day
            year = ~r"[0-9]{2,4}"
            day = ~r"[0-3]?[0-9]"
            date_sep = "-" / "/" / " "

            relative_datetime = "+" count_unit+
            count_unit = ordinal? unit "s"?

            end_date = ordinal? end "s"?
            end = unit / weekday / month

            named_date = "today" / "tomorrow"

            ordinal = ~r"[1-9][0-9]*"
            unit =
                unit_year / unit_month / unit_week /
                unit_day / unit_hour / unit_minute
            unit_year = "year" / "y"
            unit_month = "month" / "M"
            unit_week = "week" / "w"
            unit_day = "day" / "d"
            unit_hour = "hour" / "h"
            unit_minute = "minute" / "m"
            weekday =
                monday / tuesday / wednesday / thursday /
                friday / saturday / sunday
            monday = ~r"mon(day)?"i
            tuesday = ~r"tue(sday)?"i
            wednesday = ~r"wed(nesday)?"i
            thursday = ~r"thu(rsday)?"i
            friday = ~r"fri(day)?"i
            saturday = ~r"sat(urday)?"i
            sunday = ~r"sun(day)?"i
            month =
                january / february / march / april / may / june / july /
                august / september / october / november / december
            january = ~r"jan(uary)?"i
            february = ~r"feb(ruary)?"i
            march = ~r"mar(ch)?"i
            april = ~r"apr(il)?"i
            may = ~r"may"i
            june = ~r"jun(e)?"i
            july = ~r"jul(y)?"i
            august = ~r"aug(ust)?"i
            september = ~r"sep(tember)?"i
            october = ~r"oct(ober)?"i
            november = ~r"nov(ember)?"i
            december = ~r"dec(ember)?"i

            ws = ~r"\s+"
            """)

    @staticmethod
    def _datetime(*args, **kwargs) -> datetime:
        try:
            return datetime(*args, **kwargs)
        except ValueError as e:
            raise ValueError(f"Invalid date/time format") from e

    @staticmethod
    def _any_of(*args):
        for arg in args:
            if arg is not None:
                return arg

    def visit_expression(self, node, visited_children):
        return self._any_of(*visited_children)

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
                new_date = self.reference_date + reldelta
                delta = new_date - self.reference_date
            else:
                delta += timedelta(**{unit: count})
        return (self.reference_date + delta)

    def visit_date_time(self, node, visited_children):
        date, _, time = visited_children
        date = date or self.reference_date.date()
        if time is None:
            time = datetime.max.time()
        dt = datetime.combine(date, time)
        if dt <= self.reference_date:
            dt += timedelta(days=1)
        return dt

    def visit_time_date(self, node, visited_children):
        time, _, date = visited_children
        return self.visit_date_time(node, [date, _, time])

    def visit_date(self, node, visited_children):
        return self._any_of(*visited_children)

    def visit_absolute_date(self, node, visited_children):
        year, month, _, day = visited_children
        if year:
            year = int(year[0])
            if year < 100:
                year += 2000 if year < self.reference_date.year % 100 else 1900
        else:
            year = self.reference_date.year
        month = self.month_map[month.lower()]
        day = int(day)
        result = self._datetime(year, month, day).date()
        if result < self.reference_date.date():
            result = self._datetime(year + 1, month, day).date()
        return result

    def visit_named_date(self, node, visited_children):
        text = node.text.lower()
        if text == 'today':
            return self.reference_date.date()
        elif text == 'tomorrow':
            return self.reference_date.date() + timedelta(days=1)
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
        days_ahead = (weekday - self.reference_date.weekday() + 7) % 7
        if days_ahead == 0:
            days_ahead = 7
        days_ahead += (count - 1) * 7
        return self.reference_date.date() + timedelta(days=days_ahead)

    def _end_month(self, month, count):
        year = self.reference_date.year
        next_year = month == self.reference_date.month
        next_year = next_year and self.reference_date.day > 1
        next_year = next_year or (month < self.reference_date.month)
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
            return self._datetime(
                self.reference_date.year + count, 12, 31).date()
        elif unit == 'months':
            next_month = self.reference_date.replace(day=1) + relativedelta(months=count)
            last_day = (next_month.replace(day=1) + relativedelta(months=1) - timedelta(days=1)).day
            return next_month.replace(day=last_day).date()
        elif unit == 'weeks':
            return self.reference_date.date() + timedelta(days=7 * count - (self.reference_date.weekday() + 1) % 7)
        elif unit == 'days':
            return self.reference_date.date() + timedelta(days=count)

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
