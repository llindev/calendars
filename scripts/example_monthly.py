"""
Example: Monthly recurring event calendar.

Generates a calendar with an event on the first Friday of every month.
"""
import uuid
from calendar import monthrange
from datetime import date, datetime, timedelta, timezone

from icalendar import Calendar, Event

from scripts.base import CalendarGenerator


def first_weekday_of_month(year: int, month: int, weekday: int) -> date:
    """Return the date of the first `weekday` (0=Mon … 6=Sun) in month."""
    first = date(year, month, 1)
    offset = (weekday - first.weekday()) % 7
    return first + timedelta(days=offset)


class MonthlyReviewCalendar(CalendarGenerator):
    """Example: a monthly review on the first Friday of every month."""

    @property
    def calendar_id(self) -> str:
        return "monthly-review"

    @property
    def calendar_name(self) -> str:
        return "Monthly Review"

    @property
    def calendar_description(self) -> str:
        return "Monthly review event on the first Friday of every month at 14:00 UTC."

    def generate(self, cal: Calendar) -> None:
        today = date.today()

        for i in range(12):
            month = (today.month - 1 + i) % 12 + 1
            year = today.year + (today.month - 1 + i) // 12

            event_date = first_weekday_of_month(year, month, 4)  # 4 = Friday
            if event_date < today:
                continue

            dt_start = datetime(
                event_date.year, event_date.month, event_date.day,
                14, 0, 0, tzinfo=timezone.utc
            )
            dt_end = dt_start + timedelta(hours=2)

            event = Event()
            event.add("uid", str(uuid.uuid4()))
            event.add("summary", "Monthly Review")
            event.add("description", "Monthly review — first Friday of the month.")
            event.add("dtstart", dt_start)
            event.add("dtend", dt_end)
            event.add("dtstamp", datetime.now(timezone.utc))
            cal.add_component(event)
