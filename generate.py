#!/usr/bin/env python3
"""
Calendar generator entry point.

Discovers every CalendarGenerator subclass defined in scripts/*.py,
runs each one, and writes the resulting .ics files to output/.
"""
import importlib
import inspect
import pkgutil
from pathlib import Path

from icalendar import Calendar

import scripts  # noqa: F401 – ensures the package is importable
from scripts.base import CalendarGenerator

OUTPUT_DIR = Path("output")
PRODID = "-//calendars//generated//EN"


def build_calendar(generator: CalendarGenerator) -> Calendar:
    cal = Calendar()
    cal.add("prodid", PRODID)
    cal.add("version", "2.0")
    cal.add("x-wr-calname", generator.calendar_name)
    cal.add("x-wr-caldesc", generator.calendar_description)
    cal.add("x-wr-timezone", "UTC")
    cal.add("calscale", "GREGORIAN")
    cal.add("method", "PUBLISH")
    generator.generate(cal)
    return cal


def discover_generators() -> list[CalendarGenerator]:
    generators = []
    for module_info in pkgutil.iter_modules(scripts.__path__):
        if module_info.name == "base":
            continue
        module = importlib.import_module(f"scripts.{module_info.name}")
        for _, obj in inspect.getmembers(module, inspect.isclass):
            if issubclass(obj, CalendarGenerator) and obj is not CalendarGenerator:
                generators.append(obj())
    return generators


def main() -> None:
    OUTPUT_DIR.mkdir(exist_ok=True)

    generators = discover_generators()
    if not generators:
        print("No calendar generators found in scripts/.")
        return

    for gen in generators:
        cal = build_calendar(gen)
        output_path = OUTPUT_DIR / f"{gen.calendar_id}.ics"
        output_path.write_bytes(cal.to_ical())
        print(f"  [ok] {output_path}  ({gen.calendar_name})")

    print(f"\nGenerated {len(generators)} calendar(s) in {OUTPUT_DIR}/")


if __name__ == "__main__":
    main()
