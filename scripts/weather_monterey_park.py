"""
Weather calendar for Monterey Park, CA.

Source:
  https://api.open-meteo.com – free, no API key required.
  Coordinates: 34.0625° N, 118.1228° W (Monterey Park, CA)

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

# Open-Meteo free forecast API – no authentication required.
# 16-day daily forecast for Monterey Park, CA in imperial units.
_SOURCE_URL = (
    "https://api.open-meteo.com/v1/forecast"
    "?latitude=34.0625&longitude=-118.1228"
    "&daily=temperature_2m_max,temperature_2m_min,weathercode"
    "&temperature_unit=fahrenheit"
    "&forecast_days=16"
    "&timezone=America%2FLos_Angeles"
)

# Path is relative to the repo root where generate.py is executed
_OUTPUT_PATH = Path("output/weather-monterey-park.ics")

_UID_SUFFIX = "@weather-monterey-park.calendars"

# WMO Weather interpretation codes → human-readable description
_WMO_DESCRIPTIONS: dict[int, str] = {
    0: "Clear sky",
    1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
    45: "Foggy", 48: "Icy fog",
    51: "Light drizzle", 53: "Moderate drizzle", 55: "Dense drizzle",
    56: "Freezing drizzle", 57: "Heavy freezing drizzle",
    61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
    66: "Freezing rain", 67: "Heavy freezing rain",
    71: "Slight snow", 73: "Moderate snow", 75: "Heavy snow",
    77: "Snow grains",
    80: "Slight showers", 81: "Moderate showers", 82: "Violent showers",
    85: "Slight snow showers", 86: "Heavy snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm with hail", 99: "Thunderstorm with heavy hail",
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


def _debug_response(resp: requests.Response) -> None:
    """Print verbose request/response info to help diagnose fetch failures."""
    print(f"  [debug] Request URL      : {resp.url}")
    print(f"  [debug] Request headers  :")
    for k, v in resp.request.headers.items():
        print(f"            {k}: {v}")
    print(f"  [debug] Response status  : {resp.status_code} {resp.reason}")
    print(f"  [debug] Response headers :")
    for k, v in resp.headers.items():
        print(f"            {k}: {v}")
    body_preview = resp.text[:1000].replace("\n", "\\n")
    print(f"  [debug] Response body    : {body_preview}")


def _fetch_source_events() -> dict[date, tuple[str, str]]:
    """
    Fetch the Open-Meteo forecast and return {date: (summary, description)}.

    Retries up to _FETCH_RETRIES times with exponential backoff.
    Raises on final failure so the caller can fall back to stale data.
    """
    last_exc: Exception | None = None
    for attempt in range(_FETCH_RETRIES):
        try:
            resp = requests.get(_SOURCE_URL, timeout=30)
            if not resp.ok:
                _debug_response(resp)
            resp.raise_for_status()
            data = resp.json()
            daily = data["daily"]
            events: dict[date, tuple[str, str]] = {}
            for date_str, t_max, t_min, wmo in zip(
                daily["time"],
                daily["temperature_2m_max"],
                daily["temperature_2m_min"],
                daily["weathercode"],
            ):
                if t_max is None or t_min is None or wmo is None:
                    continue
                d = date.fromisoformat(date_str)
                t_lo = round(t_min)
                t_hi = round(t_max)
                condition = _WMO_DESCRIPTIONS.get(int(wmo), "Unknown")
                summary = f"{t_lo}°F / {t_hi}°F – {condition}"
                description = (
                    f"Monterey Park, CA\n"
                    f"Low: {t_lo}°F | High: {t_hi}°F\n"
                    f"{condition}"
                )
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
