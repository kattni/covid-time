"""Tests for the COVID-time clock logic (no GUI)."""
import datetime
import time

from covid_time.clock import EPOCH, covid_time_string, day_number


def _struct(year, month, day, weekday):
    """Build a struct_time. weekday: Mon=0 .. Sun=6 (matches date.weekday())."""
    return time.struct_time((year, month, day, 0, 0, 0, weekday, 0, -1))


def test_day_number_at_epoch_is_one():
    # 2020-03-01 was a Sunday (tm_wday 6).
    assert day_number(_struct(2020, 3, 1, 6)) == 1


def test_day_number_one_month_later():
    # 2020-03-01 -> 2020-04-01 is 31 days; +1 => 32.
    assert day_number(_struct(2020, 4, 1, 2)) == 32


def test_day_number_at_day_two():
    assert day_number(_struct(2020, 3, 2, 0)) == 2


def test_day_number_today_matches_formula():
    today = datetime.date.today()
    now = _struct(today.year, today.month, today.day, today.weekday())
    assert day_number(now) == (today - EPOCH).days + 1


def test_covid_time_string_at_epoch():
    s = covid_time_string(_struct(2020, 3, 1, 6))  # Sunday, day 1
    assert s.startswith("Sun Mar 1 ")
    assert s.endswith(" 2020")


def test_covid_time_string_advances_day_number():
    s = covid_time_string(_struct(2020, 4, 1, 2))  # Wednesday, day 32
    assert s.startswith("Wed Mar 32 ")
    assert s.endswith(" 2020")


def test_covid_time_string_carries_time():
    now = time.struct_time((2020, 3, 1, 13, 42, 7, 6, 0, -1))
    assert "13:42:07" in covid_time_string(now)
