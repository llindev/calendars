"""
Weather calendar for Monterey Park, CA.

Mirrors:
  https://weather-in-calendar.com/cal/weather-cal.php
    ?city=Monterey+Park&units=imperial&temperature=low-high

Rules
-----
- Past events (before today) are preserved from the existing output file
  exactly as-is; they are never re-fetched or altered.
- Today and future events are re-fetched from the source on every run.
- A future event is only written with a new DTSTAMP / LAST-MODIFIED when
  its SUMMARY or DESCRIPTION has actually changed, so git diffs only
  appear when the forecast changed.
"""
import hashlib
import time
import uuid
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import requests
from icalendar import Calendar, Event

from scripts.base import CalendarGenerator

_FETCH_RETRIES = 3
_FETCH_RETRY_BACKOFF = 2  # seconds; doubles each retry

_SOURCE_URL = (
    "https://weather-in-calendar.com/cal/weather-cal.php"
    "?city=Monterey+Park&units=imperial&temperature=low-high"
)

# Path is relative to the repo root where generate.py is executed
_OUTPUT_PATH = Path("output/weather-monterey-park.ics")

_UID_SUFFIX = "@weather-monterey-park.calendars"

_FETCH_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64; rv:124.0) Gecko/20100101 Firefox/124.0"
    ),
    "Referer": "https://weather-in-calendar.com/",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _event_uid(d: date) -> str:
    """Stable UID for a given date; same event always gets the same ID."""
    return f"{d.isoformat()}{_UID_SUFFIX}"


def _content_dtstamp(summary: str, description: str) -> datetime:
    """
    Deterministic DTSTAMP derived from event content.

    If summary + description are unchanged between runs, DTSTAMP stays
    the same, so the .ics file bytes don't change and git produces no diff.
    The timestamp is a fixed synthetic value in year 2020; calendar clients
    only care that it's stable, not that it reflects a real wall-clock time.
    """
    digest = hashlib.sha256(f"{summary}\x00{description}".encode()).hexdigest()
    epoch = datetime(2020, 1, 1, tzinfo=timezone.utc)
    # Spread within one year (≤ 31 536 000 s) using the first 8 hex digits
    seconds = int(digest[:8], 16) % (365 * 24 * 3600)
    return epoch + timedelta(seconds=seconds)


def _make_event(d: date, summary: str, description: str) -> Event:
    ev = Event()
    ev.add("uid", _event_uid(d))
    ev.add("summary", summary)
    ev.add("description", description)
    ev.add("dtstart", d)
    ev.add("dtend", d + timedelta(days=1))
    ev.add("location", "Monterey Park, CA")
    dtstamp = _content_dtstamp(summary, description)
    ev.add("dtstamp", dtstamp)
    ev.add("last-modified", dtstamp)
    return ev


def _fetch_source_events() -> dict[date, tuple[str, str]]:
    """
    Fetch the source ICS and return {date: (summary, description)}.

    Retries up to _FETCH_RETRIES times with exponential backoff.
    Raises on final failure so the caller can fall back to stale data.
    """
    last_exc: Exception | None = None
    for attempt in range(_FETCH_RETRIES):
        try:
            resp = requests.get(_SOURCE_URL, headers=_FETCH_HEADERS, timeout=30)
            resp.raise_for_status()
            cal = Calendar.from_ical(resp.content)
            events: dict[date, tuple[str, str]] = {}
            for component in cal.walk():
                if component.name != "VEVENT":
                    continue
                dtstart = component.get("dtstart")
                if dtstart is None:
                    continue
                d = dtstart.dt
                if isinstance(d, datetime):
                    d = d.date()
                summary = str(component.get("summary", ""))
                description = str(component.get("description", ""))
                events[d] = (summary, description)
            return events
        except Exception as exc:
            last_exc = exc
            if attempt < _FETCH_RETRIES - 1:
                delay = _FETCH_RETRY_BACKOFF * (2 ** attempt)
                print(
                    f"  [warn] Weather fetch attempt {attempt + 1} failed: {exc}. "
                    f"Retrying in {delay}s..."
                )
                time.sleep(delay)
    assert last_exc is not None
    raise last_exc


def _load_existing_past_events(before: date) -> list[Event]:
    """
    Return VEVENT components from the existing output file whose date
    is strictly before *before* (i.e. already-passed days).
    """
    if not _OUTPUT_PATH.exists():
        return []
    try:
        cal = Calendar.from_ical(_OUTPUT_PATH.read_bytes())
    except Exception:
        return []
    past: list[Event] = []
    for component in cal.walk():
        if component.name != "VEVENT":
            continue
        dtstart = component.get("dtstart")
        if dtstart is None:
            continue
        d = dtstart.dt
        if isinstance(d, datetime):
            d = d.date()
        if d < before:
            past.append(component)
    return past


def _load_existing_future_events(from_date: date) -> list[Event]:
    """
    Return VEVENT components from the existing output file whose date
    is on or after *from_date* (today and future days).

    Used as a fallback when the upstream fetch fails so the calendar
    retains its most-recently-fetched forecast rather than going blank.
    """
    if not _OUTPUT_PATH.exists():
        return []
    try:
        cal = Calendar.from_ical(_OUTPUT_PATH.read_bytes())
    except Exception:
        return []
    future: list[Event] = []
    for component in cal.walk():
        if component.name != "VEVENT":
            continue
        dtstart = component.get("dtstart")
        if dtstart is None:
            continue
        d = dtstart.dt
        if isinstance(d, datetime):
            d = d.date()
        if d >= from_date:
            future.append(component)
    return future


# ---------------------------------------------------------------------------
# Generator
# ---------------------------------------------------------------------------

class WeatherMontereyParkCalendar(CalendarGenerator):
    """Daily weather forecast for Monterey Park, CA (imperial, low/high)."""

    @property
    def calendar_id(self) -> str:
        return "weather-monterey-park"

    @property
    def calendar_name(self) -> str:
        return "Weather – Monterey Park"

    @property
    def calendar_description(self) -> str:
        return (
            "Daily weather forecast for Monterey Park, CA "
            "(imperial units, low/high temperature). "
            "Past events are preserved; future events refresh daily."
        )

    def generate(self, cal: Calendar) -> None:
        today = date.today()

        # 1. Preserve already-passed days from the existing output file
        for ev in _load_existing_past_events(before=today):
            cal.add_component(ev)

        # 2. Fetch the latest forecast from the upstream source
        try:
            source_events = _fetch_source_events()
        except Exception as exc:
            # Upstream unreachable – keep whatever future events exist in the
            # current output file so the calendar isn't left empty and the
            # pipeline doesn't fail due to a third-party outage.
            print(
                f"  [warn] Weather fetch failed after {_FETCH_RETRIES} attempts: {exc}. "
                "Preserving existing future events."
            )
            for ev in _load_existing_future_events(from_date=today):
                cal.add_component(ev)
            return

        # 3. Add/update today and all future events from the source
        for d, (summary, description) in sorted(source_events.items()):
            if d >= today:
                cal.add_component(_make_event(d, summary, description))
