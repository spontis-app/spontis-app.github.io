from __future__ import annotations

from collections import OrderedDict
from datetime import datetime
from typing import Iterable, Optional, Sequence
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Europe/Oslo")
DEFAULT_CITY = "Bergen"
WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def _ensure_local(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=TZ)
    return dt.astimezone(TZ)


def to_iso(dt: Optional[datetime]) -> Optional[str]:
    if dt is None:
        return None
    return _ensure_local(dt).replace(microsecond=0).isoformat()


def to_weekday_label(dt: Optional[datetime]) -> Optional[str]:
    if dt is None:
        return None
    local = _ensure_local(dt)
    return f"{WEEKDAYS[local.weekday()]} {local:%H:%M}"


def _clean_tags(tags: Optional[Iterable[str]]) -> Optional[list[str]]:
    if not tags:
        return None
    cleaned = sorted({t.strip() for t in tags if t and t.strip()})
    return cleaned or None


def build_event(
    *,
    source: str,
    title: str,
    url: str,
    starts_at: Optional[datetime] = None,
    ends_at: Optional[datetime] = None,
    venue: Optional[str] = None,
    city: Optional[str] = DEFAULT_CITY,
    tags: Optional[Iterable[str]] = None,
    extra: Optional[dict] = None,
) -> dict:
    event: dict = {
        "source": source.strip(),
        "title": title.strip(),
        "url": url,
        "city": (city or DEFAULT_CITY).strip(),
    }

    starts_iso = to_iso(starts_at)
    if starts_iso:
        event["starts_at"] = starts_iso

    ends_iso = to_iso(ends_at)
    if ends_iso:
        event["ends_at"] = ends_iso

    if venue and venue.strip():
        event["venue"] = venue.strip()

    cleaned_tags = _clean_tags(tags)
    if cleaned_tags:
        event["tags"] = cleaned_tags

    if extra:
        event.update(extra)

    return event


def format_showtimes(times: Sequence[datetime], *, max_days: int = 2, max_per_day: int = 3) -> str:
    if not times:
        return ""

    localized = sorted({
        _ensure_local(dt)
        for dt in times
    })

    buckets: "OrderedDict[str, list[str]]" = OrderedDict()
    for dt in localized:
        day = WEEKDAYS[dt.weekday()]
        buckets.setdefault(day, []).append(dt.strftime("%H:%M"))

    parts: list[str] = []
    for day, slots in list(buckets.items())[:max_days]:
        visible = list(slots[:max_per_day])
        rest = len(slots) - len(visible)
        chunk = f"{day} {' • '.join(visible)}"
        if rest > 0:
            chunk += f" (+{rest} later)"
        parts.append(chunk)

    remaining_days = len(buckets) - min(len(buckets), max_days)
    if remaining_days > 0:
        suffix = "s" if remaining_days > 1 else ""
        parts.append(f"+{remaining_days} more day{suffix}")

    return " / ".join(parts)
