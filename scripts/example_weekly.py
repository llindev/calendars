"""
Example: Weekly recurring event calendar.

Generates a calendar with a recurring event every week for the next year.
Rename this file and adjust the events to create your own calendar.
"""
import uuid
from datetime import date, datetime, timedelta, timezone

from icalendar import Calendar, Event, vText, vDatetime

from scripts.base import CalendarGenerator


class WeeklyMeetingCalendar(CalendarGenerator):
    """Example: a weekly team sync every Monday at 10:00 UTC."""

    @property
    def calendar_id(self) -> str:
        return "weekly-meeting"

    @property
    def calendar_name(self) -> str:
        return "Weekly Team Sync"

    @property
    def calendar_description(self) -> str:
        return "Weekly team sync meeting every Monday at 10:00 UTC."

    def generate(self, cal: Calendar) -> None:
        today = date.today()
        # Start from the next Monday (or today if already Monday)
        days_until_monday = (7 - today.weekday()) % 7
        start = today + timedelta(days=days_until_monday if days_until_monday else 7)

        # Generate events for the next 52 weeks
        for week in range(52):
            event_date = start + timedelta(weeks=week)
            dt_start = datetime(
                event_date.year, event_date.month, event_date.day,
                10, 0, 0, tzinfo=timezone.utc
            )
            dt_end = dt_start + timedelta(hours=1)

            event = Event()
            event.add("uid", str(uuid.uuid4()))
            event.add("summary", "Weekly Team Sync")
            event.add("description", "Regular weekly sync. Adjust agenda as needed.")
            event.add("dtstart", dt_start)
            event.add("dtend", dt_end)
            event.add("dtstamp", datetime.now(timezone.utc))
            cal.add_component(event)
