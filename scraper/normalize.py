from collections import OrderedDict
from datetime import datetime
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Europe/Oslo")
WEEKDAYS = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]

def to_when_label(dt: datetime) -> str:
    """Thu 21:15, local time."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=TZ)
    dt = dt.astimezone(TZ)
    wd = WEEKDAYS[dt.weekday()]
    return f"{wd} {dt:%H:%M}"

def event(title: str, dt: datetime, where: str, tags: list[str], url: str) -> dict:
    return {
        "title": title.strip(),
        "when": to_when_label(dt),
        "where": where.strip(),
        "tags": tags,
        "url": url
    }


def format_showtimes(times: list[datetime], *, max_days: int = 2, max_per_day: int = 3) -> str:
    """
    Compress a list of datetimes into a readable label such as
    "Fri 12:00 • 14:30 / Sat 18:00". Limits the number of days and slots so
    the label stays compact for the UI chip format.
    """
    if not times:
        return ""

    localized = sorted({
        (dt if dt.tzinfo else dt.replace(tzinfo=TZ)).astimezone(TZ)
        for dt in times
    })

    buckets: "OrderedDict[str, list[str]]" = OrderedDict()
    for dt in localized:
        day = WEEKDAYS[dt.weekday()]
        buckets.setdefault(day, []).append(dt.strftime("%H:%M"))

    parts: list[str] = []
    for day, slots in list(buckets.items())[:max_days]:
        visible = slots[:max_per_day]
        rest = len(slots) - len(visible)
        chunk = f"{day} {' • '.join(visible)}"
        if rest > 0:
            chunk += f" (+{rest} later)"
        parts.append(chunk)

    remaining_days = len(buckets) - min(len(buckets), max_days)
    if remaining_days > 0:
        parts.append(f"+{remaining_days} more day{'s' if remaining_days > 1 else ''}")

    return " / ".join(parts)
