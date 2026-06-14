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
