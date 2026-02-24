"""
黄历 (Huánglì) — Traditional Chinese Almanac Calendar.

Uses the cnlunar library to dynamically generate all-day events for:
  - The 24 Solar Terms (二十四节气)
  - Chinese national/legal holidays (法定节假日)
  - Traditional lunar calendar festivals (传统节日)

Events cover a rolling 12-month window from today.
"""
import uuid
from datetime import date, datetime, timedelta, timezone

import cnlunar
from icalendar import Calendar, Event

from scripts.base import CalendarGenerator


def _all_day_event(event_date: date, summary: str, description: str) -> Event:
    event = Event()
    event.add("uid", str(uuid.uuid4()))
    event.add("summary", summary)
    event.add("description", description)
    event.add("dtstart", event_date)
    event.add("dtend", event_date + timedelta(days=1))
    event.add("dtstamp", datetime.now(timezone.utc))
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
        cutoff = today + timedelta(days=366)

        current = today
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
