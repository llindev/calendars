"""Base class for calendar generators."""
from abc import ABC, abstractmethod
from icalendar import Calendar


class CalendarGenerator(ABC):
    """
    Base class for all calendar generators.

    Subclass this and implement `calendar_id`, `calendar_name`,
    `calendar_description`, and `generate()`.
    """

    @property
    @abstractmethod
    def calendar_id(self) -> str:
        """Unique identifier used as the output filename (without .ics)."""
        ...

    @property
    @abstractmethod
    def calendar_name(self) -> str:
        """Human-readable calendar name."""
        ...

    @property
    def calendar_description(self) -> str:
        """Optional calendar description."""
        return ""

    @abstractmethod
    def generate(self, cal: Calendar) -> None:
        """
        Populate `cal` with VEVENT components.

        Args:
            cal: An icalendar.Calendar instance, already initialised with
                 standard metadata (PRODID, VERSION, X-WR-CALNAME, etc.).
                 Add events directly to this object.
        """
        ...
