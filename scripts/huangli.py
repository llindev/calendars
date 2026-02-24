"""
黄历 (Huánglì) — Traditional Chinese Almanac Calendar.

Uses the cnlunar library to dynamically generate all-day events for:
  - The 24 Solar Terms (二十四节气)
  - Chinese national/legal holidays (法定节假日)
  - Traditional lunar calendar festivals (传统节日)

Events cover a rolling window from 1 year ago to 1 year ahead.
UIDs and DSTAMPs are derived deterministically from the event identity so
that regenerating the calendar only produces a diff when event data changes.
"""
import uuid
from datetime import date, datetime, timedelta, timezone

import cnlunar
from icalendar import Calendar, Event

from scripts.base import CalendarGenerator

# Stable namespace for deterministic UUID generation
_UID_NAMESPACE = uuid.UUID("b1e2c3d4-e5f6-7890-abcd-ef1234567890")


def _all_day_event(event_date: date, summary: str, description: str) -> Event:
    # Deterministic UID: same event always gets the same identifier
    uid = str(uuid.uuid5(_UID_NAMESPACE, f"{event_date.isoformat()}:{summary}"))
    # Deterministic DTSTAMP: midnight UTC of the event date so the field
    # doesn't change on every regeneration
    dtstamp = datetime(event_date.year, event_date.month, event_date.day,
                       tzinfo=timezone.utc)
    event = Event()
    event.add("uid", uid)
    event.add("summary", summary)
    event.add("description", description)
    event.add("dtstart", event_date)
    event.add("dtend", event_date + timedelta(days=1))
    event.add("dtstamp", dtstamp)
    return event


class HuangliCalendar(CalendarGenerator):
    """黄历 — Traditional Chinese Almanac with Solar Terms and festivals."""

    @property
    def calendar_id(self) -> str:
        return "huangli"

    @property
    def calendar_name(self) -> str:
        return "黄历 (Chinese Almanac)"

    @property
    def calendar_description(self) -> str:
        return (
            "Traditional Chinese almanac (黄历) with the 24 Solar Terms "
            "(二十四节气), national holidays (法定节假日), and traditional "
            "lunar festivals (传统节日). Generated via cnlunar."
        )

    def generate(self, cal: Calendar) -> None:
        today = date.today()
        start = today - timedelta(days=365)
        cutoff = today + timedelta(days=366)

        current = start
        while current <= cutoff:
            dt = datetime(current.year, current.month, current.day, 12, 0, 0)
            lunar = cnlunar.Lunar(dt, godType='8char')

            lunar_date_str = f"{lunar.lunarYearCn}年{lunar.lunarMonthCn}{lunar.lunarDayCn}"

            # Solar term
            solar_term = lunar.todaySolarTerms
            if solar_term and solar_term != "无":
                cal.add_component(_all_day_event(
                    current,
                    f"【节气】{solar_term}",
                    f"{solar_term} — 农历{lunar_date_str}",
                ))

            # Legal / national holidays
            legal = lunar.get_legalHolidays()
            if legal:
                cal.add_component(_all_day_event(
                    current,
                    f"【节假日】{legal}",
                    f"{legal} — 农历{lunar_date_str}",
                ))

            # Traditional lunar festivals
            lunar_festival = lunar.get_otherLunarHolidays()
            if lunar_festival:
                cal.add_component(_all_day_event(
                    current,
                    f"【传统节日】{lunar_festival}",
                    f"{lunar_festival} — 农历{lunar_date_str}",
                ))

            current += timedelta(days=1)
