from datetime import datetime
import pytz

TZ = pytz.timezone("Europe/Oslo")
WEEKDAYS = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]

def to_when_label(dt: datetime) -> str:
    """Thu 21:15, local time."""
    if dt.tzinfo is None:
        dt = TZ.localize(dt)
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
