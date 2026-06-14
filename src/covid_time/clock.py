"""COVID time: the date is always March 2020; only the day count advances."""
import datetime
import time

EPOCH = datetime.date(2020, 3, 1)


def day_number(now=None):
    """Days into eternal March 2020. 2020-03-01 -> 1.

    Args:
        now: A ``time.struct_time``. Defaults to the current local time.
    """
    if now is None:
        now = time.localtime()
    today = datetime.date(now.tm_year, now.tm_mon, now.tm_mday)
    return (today - EPOCH).days + 1


def covid_time_string(now=None):
    """The COVID-time line, e.g. ``Sun Mar 2298 13:42:07 EDT 2020``.

    The weekday, time-of-day and timezone are real; only the date is frozen
    at "March 2020" with a climbing day number. ``now`` is a
    ``time.struct_time`` defaulting to the current local time.
    """
    if now is None:
        now = time.localtime()
    weekday = time.strftime("%a", now)
    clock = time.strftime("%H:%M:%S", now)
    zone = time.strftime("%Z", now)
    return f"{weekday} Mar {day_number(now)} {clock} {zone} 2020"
