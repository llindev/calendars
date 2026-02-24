"""
黄历 (Huánglì) — Traditional Chinese Almanac Calendar.

Generates all-day events for:
  - The 24 Solar Terms (二十四节气), based on the sun's ecliptic longitude
  - Major traditional Chinese festivals (based on the lunisolar calendar)

Dates cover a rolling 12-month window from today.
"""
import uuid
from datetime import date, datetime, timedelta, timezone

from icalendar import Calendar, Event

from scripts.base import CalendarGenerator


# ---------------------------------------------------------------------------
# Static data: Solar Terms (节气)
# Each entry: (month, day, chinese_name, pinyin, english_name)
# Dates are given for 2025, 2026, and 2027 (China Standard Time, UTC+8).
# ---------------------------------------------------------------------------
_SOLAR_TERMS: dict[int, list[tuple[int, int, str, str, str]]] = {
    2025: [
        (1,  5,  "小寒", "Xiǎohán",       "Minor Cold"),
        (1,  20, "大寒", "Dàhán",          "Major Cold"),
        (2,  3,  "立春", "Lìchūn",         "Start of Spring"),
        (2,  18, "雨水", "Yǔshuǐ",         "Rain Water"),
        (3,  5,  "惊蛰", "Jīngzhé",        "Awakening of Insects"),
        (3,  20, "春分", "Chūnfēn",        "Spring Equinox"),
        (4,  4,  "清明", "Qīngmíng",       "Clear and Bright"),
        (4,  20, "谷雨", "Gǔyǔ",           "Grain Rain"),
        (5,  5,  "立夏", "Lìxià",          "Start of Summer"),
        (5,  21, "小满", "Xiǎomǎn",        "Grain Buds"),
        (6,  5,  "芒种", "Mángzhòng",      "Grain in Ear"),
        (6,  21, "夏至", "Xiàzhì",         "Summer Solstice"),
        (7,  7,  "小暑", "Xiǎoshǔ",        "Minor Heat"),
        (7,  22, "大暑", "Dàshǔ",          "Major Heat"),
        (8,  7,  "立秋", "Lìqiū",          "Start of Autumn"),
        (8,  23, "处暑", "Chǔshǔ",         "End of Heat"),
        (9,  7,  "白露", "Báilù",          "White Dew"),
        (9,  23, "秋分", "Qiūfēn",         "Autumnal Equinox"),
        (10, 8,  "寒露", "Hánlù",          "Cold Dew"),
        (10, 23, "霜降", "Shuāngjiàng",    "Frost's Descent"),
        (11, 7,  "立冬", "Lìdōng",         "Start of Winter"),
        (11, 22, "小雪", "Xiǎoxuě",        "Minor Snow"),
        (12, 7,  "大雪", "Dàxuě",          "Major Snow"),
        (12, 22, "冬至", "Dōngzhì",        "Winter Solstice"),
    ],
    2026: [
        (1,  5,  "小寒", "Xiǎohán",       "Minor Cold"),
        (1,  20, "大寒", "Dàhán",          "Major Cold"),
        (2,  4,  "立春", "Lìchūn",         "Start of Spring"),
        (2,  19, "雨水", "Yǔshuǐ",         "Rain Water"),
        (3,  6,  "惊蛰", "Jīngzhé",        "Awakening of Insects"),
        (3,  20, "春分", "Chūnfēn",        "Spring Equinox"),
        (4,  5,  "清明", "Qīngmíng",       "Clear and Bright"),
        (4,  20, "谷雨", "Gǔyǔ",           "Grain Rain"),
        (5,  5,  "立夏", "Lìxià",          "Start of Summer"),
        (5,  21, "小满", "Xiǎomǎn",        "Grain Buds"),
        (6,  6,  "芒种", "Mángzhòng",      "Grain in Ear"),
        (6,  21, "夏至", "Xiàzhì",         "Summer Solstice"),
        (7,  7,  "小暑", "Xiǎoshǔ",        "Minor Heat"),
        (7,  23, "大暑", "Dàshǔ",          "Major Heat"),
        (8,  7,  "立秋", "Lìqiū",          "Start of Autumn"),
        (8,  23, "处暑", "Chǔshǔ",         "End of Heat"),
        (9,  8,  "白露", "Báilù",          "White Dew"),
        (9,  23, "秋分", "Qiūfēn",         "Autumnal Equinox"),
        (10, 8,  "寒露", "Hánlù",          "Cold Dew"),
        (10, 23, "霜降", "Shuāngjiàng",    "Frost's Descent"),
        (11, 7,  "立冬", "Lìdōng",         "Start of Winter"),
        (11, 22, "小雪", "Xiǎoxuě",        "Minor Snow"),
        (12, 7,  "大雪", "Dàxuě",          "Major Snow"),
        (12, 22, "冬至", "Dōngzhì",        "Winter Solstice"),
    ],
    2027: [
        (1,  6,  "小寒", "Xiǎohán",       "Minor Cold"),
        (1,  20, "大寒", "Dàhán",          "Major Cold"),
        (2,  4,  "立春", "Lìchūn",         "Start of Spring"),
        (2,  18, "雨水", "Yǔshuǐ",         "Rain Water"),
        (3,  6,  "惊蛰", "Jīngzhé",        "Awakening of Insects"),
        (3,  21, "春分", "Chūnfēn",        "Spring Equinox"),
        (4,  5,  "清明", "Qīngmíng",       "Clear and Bright"),
        (4,  20, "谷雨", "Gǔyǔ",           "Grain Rain"),
        (5,  6,  "立夏", "Lìxià",          "Start of Summer"),
        (5,  21, "小满", "Xiǎomǎn",        "Grain Buds"),
        (6,  6,  "芒种", "Mángzhòng",      "Grain in Ear"),
        (6,  21, "夏至", "Xiàzhì",         "Summer Solstice"),
        (7,  7,  "小暑", "Xiǎoshǔ",        "Minor Heat"),
        (7,  23, "大暑", "Dàshǔ",          "Major Heat"),
        (8,  7,  "立秋", "Lìqiū",          "Start of Autumn"),
        (8,  23, "处暑", "Chǔshǔ",         "End of Heat"),
        (9,  8,  "白露", "Báilù",          "White Dew"),
        (9,  23, "秋分", "Qiūfēn",         "Autumnal Equinox"),
        (10, 8,  "寒露", "Hánlù",          "Cold Dew"),
        (10, 23, "霜降", "Shuāngjiàng",    "Frost's Descent"),
        (11, 7,  "立冬", "Lìdōng",         "Start of Winter"),
        (11, 22, "小雪", "Xiǎoxuě",        "Minor Snow"),
        (12, 7,  "大雪", "Dàxuě",          "Major Snow"),
        (12, 22, "冬至", "Dōngzhì",        "Winter Solstice"),
    ],
}

# ---------------------------------------------------------------------------
# Static data: Traditional Chinese Festivals (传统节日)
# Each entry: (year, month, day, chinese_name, pinyin, english_name, description)
# Dates are Gregorian equivalents of lunisolar festival dates.
# ---------------------------------------------------------------------------
_FESTIVALS: list[tuple[int, int, int, str, str, str, str]] = [
    # 2025
    (2025, 1,  29, "除夕",   "Chúxī",         "Chinese New Year's Eve",
     "除夕 — the last day of the lunar year; family reunion dinner (年夜饭)."),
    (2025, 1,  29, "春节",   "Chūnjié",        "Chinese New Year (Year of the Snake)",
     "农历正月初一，蛇年。Spring Festival, the most important traditional holiday."),
    (2025, 2,  12, "元宵节", "Yuánxiāojié",    "Lantern Festival",
     "农历正月十五。Marks the end of the Spring Festival with lantern displays and tangyuan."),
    (2025, 4,  4,  "清明节", "Qīngmíngjié",    "Qingming Festival",
     "清明节 — Tomb-Sweeping Day; honouring ancestors and the arrival of spring."),
    (2025, 5,  31, "端午节", "Duānwǔjié",      "Dragon Boat Festival",
     "农历五月初五。Dragon boat races and zongzi to commemorate Qu Yuan."),
    (2025, 8,  2,  "七夕节", "Qīxījié",        "Qixi Festival (Double Seventh)",
     "农历七月初七。Chinese Valentine's Day, celebrating the legend of the Cowherd and Weaver Girl."),
    (2025, 8,  10, "中元节", "Zhōngyuánjié",   "Ghost Festival",
     "农历七月十五。The Hungry Ghost Festival; offerings are made to ancestors and wandering spirits."),
    (2025, 10, 6,  "中秋节", "Zhōngqiūjié",    "Mid-Autumn Festival",
     "农历八月十五。Mooncake Festival; families gather to view the full moon."),
    (2025, 10, 29, "重阳节", "Chóngyángjié",   "Double Ninth Festival",
     "农历九月初九。Seniors' Day; climbing mountains and drinking chrysanthemum wine."),
    (2026, 1,  5,  "腊八节", "Làbājié",        "Laba Festival",
     "农历腊月初八。Laba porridge (腊八粥) is eaten to mark the start of the New Year season."),
    # 2026
    (2026, 2,  16, "除夕",   "Chúxī",         "Chinese New Year's Eve",
     "除夕 — the last day of the Year of the Snake; family reunion dinner (年夜饭)."),
    (2026, 2,  17, "春节",   "Chūnjié",        "Chinese New Year (Year of the Horse)",
     "农历正月初一，马年丙午。Spring Festival, the most important traditional holiday."),
    (2026, 3,  3,  "元宵节", "Yuánxiāojié",    "Lantern Festival",
     "农历正月十五。Marks the end of the Spring Festival with lantern displays and tangyuan."),
    (2026, 4,  5,  "清明节", "Qīngmíngjié",    "Qingming Festival",
     "清明节 — Tomb-Sweeping Day; honouring ancestors and the arrival of spring."),
    (2026, 6,  19, "端午节", "Duānwǔjié",      "Dragon Boat Festival",
     "农历五月初五。Dragon boat races and zongzi to commemorate Qu Yuan."),
    (2026, 8,  22, "七夕节", "Qīxījié",        "Qixi Festival (Double Seventh)",
     "农历七月初七。Chinese Valentine's Day, celebrating the legend of the Cowherd and Weaver Girl."),
    (2026, 8,  28, "中元节", "Zhōngyuánjié",   "Ghost Festival",
     "农历七月十五。The Hungry Ghost Festival; offerings are made to ancestors and wandering spirits."),
    (2026, 10, 1,  "中秋节", "Zhōngqiūjié",    "Mid-Autumn Festival",
     "农历八月十五，与国庆节同日。Mooncake Festival coincides with National Day in 2026."),
    (2026, 10, 17, "重阳节", "Chóngyángjié",   "Double Ninth Festival",
     "农历九月初九。Seniors' Day; climbing mountains and drinking chrysanthemum wine."),
    (2026, 12, 26, "腊八节", "Làbājié",        "Laba Festival",
     "农历腊月初八。Laba porridge (腊八粥) is eaten to mark the start of the New Year season."),
    # 2027
    (2027, 2,  5,  "除夕",   "Chúxī",         "Chinese New Year's Eve",
     "除夕 — the last day of the Year of the Horse; family reunion dinner (年夜饭)."),
    (2027, 2,  6,  "春节",   "Chūnjié",        "Chinese New Year (Year of the Goat)",
     "农历正月初一，羊年丁未。Spring Festival, the most important traditional holiday."),
    (2027, 2,  20, "元宵节", "Yuánxiāojié",    "Lantern Festival",
     "农历正月十五。Marks the end of the Spring Festival with lantern displays and tangyuan."),
]


def _all_day_event(
    event_date: date,
    summary: str,
    description: str,
) -> Event:
    """Return a VEVENT representing a single all-day event."""
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
            "Traditional Chinese almanac (黄历) featuring the 24 Solar Terms "
            "(二十四节气) and major traditional festivals for the lunisolar year."
        )

    def generate(self, cal: Calendar) -> None:
        today = date.today()
        cutoff = today + timedelta(days=366)

        # --- Solar Terms ---
        for year, terms in _SOLAR_TERMS.items():
            for month, day, zh, pinyin, en in terms:
                event_date = date(year, month, day)
                if event_date < today or event_date > cutoff:
                    continue
                summary = f"{zh} {pinyin} — {en}"
                description = (
                    f"{zh}（{pinyin}）is one of the 24 Solar Terms (二十四节气). "
                    f"English: {en}."
                )
                cal.add_component(_all_day_event(event_date, summary, description))

        # --- Traditional Festivals ---
        for year, month, day, zh, pinyin, en, desc in _FESTIVALS:
            event_date = date(year, month, day)
            if event_date < today or event_date > cutoff:
                continue
            summary = f"{zh} {pinyin} — {en}"
            cal.add_component(_all_day_event(event_date, summary, desc))
