"""Run all SPONTIS scrapers, validate output and persist to disk."""
from __future__ import annotations

import argparse
import json
import logging
import os
import re
from collections import Counter
from collections.abc import Iterable as IterableCollection
from datetime import datetime, timedelta
from difflib import SequenceMatcher
from pathlib import Path
from typing import Callable, Iterable, List, Sequence, Tuple
from zoneinfo import ZoneInfo

from scraper.normalize import DEFAULT_CITY, WEEKDAYS
from scraper.schema import validate_events
from scraper.sources import bergen_kino, ostre

LOG_FORMAT = "%(asctime)s [%(levelname)s] %(message)s"
TZ = ZoneInfo("Europe/Oslo")

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "data" / "events.json"

USE_RA = os.getenv("SCRAPE_RA", "0") == "1"
USE_OSTRE = os.getenv("SCRAPE_OSTRE", "1") != "0"
USE_USF = os.getenv("ENABLE_USF", "1") != "0"
USE_BERGEN_KJOTT = os.getenv("ENABLE_BERGEN_KJOTT", "1") != "0"
USE_KUNSTHALL = os.getenv("ENABLE_KUNSTHALL", "1") != "0"
USE_KENNEL = os.getenv("ENABLE_IG_KENNEL", "0") == "1"

if USE_RA:
    from scraper.sources import resident_advisor

if USE_USF:
    from scraper.sources import usf_verftet

if USE_BERGEN_KJOTT:
    from scraper.sources import bergen_kjott

if USE_KUNSTHALL:
    from scraper.sources import bergen_kunsthall

if USE_KENNEL:
    from scraper.sources import kennel_vinylbar


logger = logging.getLogger("spontis.scraper")

Source = Tuple[str, Callable[[], Iterable[dict]]]


def configure_logging(level: str) -> None:
    logging.basicConfig(level=level, format=LOG_FORMAT)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default=str(DEFAULT_OUT),
        help="Destination path for events JSON (default: %(default)s)",
    )
    parser.add_argument(
        "--log-level",
        default=os.getenv("SCRAPER_LOG_LEVEL", "INFO"),
        help="Logging level (default: %(default)s)",
    )
    parser.add_argument(
        "--grace-hours",
        type=int,
        default=int(os.getenv("SCRAPER_GRACE_HOURS", "4")),
        help=(
            "How many hours after an event has started we continue to keep it in "
            "the dataset (default: %(default)s)"
        ),
    )
    parser.add_argument(
        "--now",
        help="Override the current time (ISO 8601, defaults to now in Europe/Oslo)",
    )
    return parser.parse_args(argv)


def _sources() -> List[Source]:
    sources: List[Source] = [("Bergen Kino", bergen_kino.fetch)]
    if USE_OSTRE:
        sources.append(("Østre", ostre.fetch))
    if USE_USF:
        sources.append(("USF Verftet", usf_verftet.fetch))
    if USE_BERGEN_KJOTT:
        sources.append(("Bergen Kjøtt", bergen_kjott.fetch))
    if USE_KUNSTHALL:
        sources.append(("Bergen Kunsthall", bergen_kunsthall.fetch))
    if USE_RA:
        sources.append(("Resident Advisor", resident_advisor.fetch))
    if USE_KENNEL:
        sources.append(("Kennel Vinylbar", kennel_vinylbar.fetch))
    return sources


def _run_source(name: str, fetch: Callable[[], Iterable[dict]]) -> List[dict]:
    try:
        events = list(fetch())
    except Exception:
        logger.exception("%s failed", name)
        return []

    logger.info("%s: %d events", name, len(events))
    return events


def _dedupe(events: Iterable[dict]) -> List[dict]:
    seen = set()
    deduped: List[dict] = []
    for event in events:
        key = (
            event.get("title"),
            event.get("starts_at"),
            event.get("url"),
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(event)
    return deduped


def _sort(events: List[dict]) -> List[dict]:
    def sort_key(ev: dict):
        starts_at = ev.get("starts_at")
        title = (ev.get("title") or "").lower()
        if starts_at:
            return (0, starts_at, title)
        return (1, title)

    return sorted(events, key=sort_key)


CATEGORY_PATTERNS = {
    "techno": re.compile(
        r"\b(dj|club|techno|rave|house|electro|afterparty|warehouse|disco)\b",
        re.IGNORECASE,
    ),
    "jazz": re.compile(r"\bjazz\b", re.IGNORECASE),
    "lecture": re.compile(
        r"\b(lecture|talk|seminar|conference|panel|debate|foredrag|samtale)\b",
        re.IGNORECASE,
    ),
    "festival": re.compile(r"\b(festival|weekender)\b", re.IGNORECASE),
    "underground": re.compile(r"\b(underground|basement|secret|warehouse)\b", re.IGNORECASE),
    "family": re.compile(r"\b(family|familie|kids|children|barn|ungdom)\b", re.IGNORECASE),
    "culture": re.compile(
        r"\b(art|kunsthall|museum|culture|utstilling|performance|kunst|lecture|talk|seminar|conference|panel|debate|foredrag|samtale)\b",
        re.IGNORECASE,
    ),
}

LATE_NIGHT_KEYWORDS = re.compile(
    r"\b(late night|afterparty|after-hours|night session)\b", re.IGNORECASE
)


def _append_unique(values: List[str], new_value: str | None) -> None:
    if new_value and new_value not in values:
        values.append(new_value)


def _normalize_tags(tags: Iterable[str]) -> List[str]:
    cleaned = sorted({tag.strip() for tag in tags if tag and tag.strip()})
    return cleaned


def _infer_tags(event: dict) -> None:
    tags = set(event.get("tags", []))
    haystack = " ".join(
        part.lower() for part in (event.get("title"), event.get("venue")) if part
    )

    for tag, pattern in CATEGORY_PATTERNS.items():
        if pattern.search(haystack):
            tags.add(tag)

    if LATE_NIGHT_KEYWORDS.search(haystack):
        tags.add("late-night")

    starts_at = event.get("starts_at")
    if starts_at:
        try:
            dt = datetime.fromisoformat(starts_at)
        except ValueError:
            dt = None
        if dt and (dt.hour >= 22 or dt.hour < 5):
            tags.add("late-night")

    if tags:
        event["tags"] = _normalize_tags(tags)
    elif "tags" in event:
        event.pop("tags", None)


def _normalize_title(value: str) -> str:
    lowered = value.lower()
    without_punct = re.sub(r"[^\w\s]", " ", lowered)
    collapsed = re.sub(r"\s+", " ", without_punct)
    return collapsed.strip()


def _titles_match(a: str, b: str, threshold: float = 0.8) -> bool:
    if not a or not b:
        return False
    ratio = SequenceMatcher(None, _normalize_title(a), _normalize_title(b)).ratio()
    return ratio >= threshold


def _same_event_day(a: dict, b: dict) -> bool:
    starts_a = a.get("starts_at")
    starts_b = b.get("starts_at")
    if not starts_a or not starts_b:
        return False
    return starts_a[:10] == starts_b[:10]


def _merge_into(existing: dict, incoming: dict) -> None:
    sources = existing.setdefault("sources", [])
    _append_unique(sources, existing.get("source"))
    _append_unique(sources, incoming.get("source"))

    incoming_sources = incoming.get("sources", [])
    for extra_source in incoming_sources:
        _append_unique(sources, extra_source)

    existing_tags = set(existing.get("tags", []))
    incoming_tags = set(incoming.get("tags", []))
    if incoming_tags or existing_tags:
        existing["tags"] = _normalize_tags(existing_tags | incoming_tags)

    for key in ("starts_at", "ends_at", "venue", "city", "when", "where"):
        if not existing.get(key) and incoming.get(key):
            existing[key] = incoming[key]


def _merge_related(events: List[dict]) -> Tuple[List[dict], int]:
    merged: List[dict] = []
    merges = 0

    for event in events:
        _infer_tags(event)
        matched = False
        for candidate in merged:
            if not _same_event_day(candidate, event):
                continue
            if not _titles_match(candidate.get("title", ""), event.get("title", "")):
                continue
            _merge_into(candidate, event)
            merges += 1
            matched = True
            break

        if not matched:
            new_event = dict(event)
            sources: List[str] = []
            _append_unique(sources, new_event.get("source"))
            new_event["sources"] = sources
            merged.append(new_event)

    for event in merged:
        if event.get("tags"):
            event["tags"] = _normalize_tags(event["tags"])

    return merged, merges


def _normalize_time(value: str | None) -> str | None:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=TZ)
    dt = dt.astimezone(TZ).replace(microsecond=0)
    return dt.isoformat()


def _human_when(value: str | None) -> str | None:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value)
    except ValueError:
        return None
    weekday = WEEKDAYS[dt.weekday()]
    return f"{weekday} {dt:%H:%M}"


def _normalize_event(event: dict) -> dict | None:
    """Clean up a single event payload before validation."""

    cleaned = dict(event)
    cleaned["source"] = (cleaned.get("source") or "").strip()
    cleaned["title"] = (cleaned.get("title") or "").strip()
    cleaned["url"] = (cleaned.get("url") or "").strip()
    cleaned["city"] = (cleaned.get("city") or DEFAULT_CITY).strip()

    starts = _normalize_time(cleaned.get("starts_at"))
    if starts:
        cleaned["starts_at"] = starts
        cleaned.setdefault("when", _human_when(starts))
    else:
        cleaned.pop("starts_at", None)

    ends = _normalize_time(cleaned.get("ends_at"))
    if ends:
        cleaned["ends_at"] = ends
    else:
        cleaned.pop("ends_at", None)

    if cleaned.get("venue"):
        cleaned["venue"] = cleaned["venue"].strip()
        cleaned.setdefault("where", cleaned["venue"])

    tags = cleaned.get("tags")
    if isinstance(tags, IterableCollection) and not isinstance(tags, (str, bytes)):
        cleaned["tags"] = _normalize_tags(tags)

    sources = cleaned.get("sources")
    if isinstance(sources, IterableCollection) and not isinstance(sources, (str, bytes)):
        cleaned["sources"] = _normalize_tags(sources)

    if not cleaned["source"] or not cleaned["title"] or not cleaned["url"]:
        return None

    return cleaned


def _normalize_events(events: Iterable[dict]) -> List[dict]:
    normalized: List[dict] = []
    dropped = 0
    for event in events:
        normalized_event = _normalize_event(event)
        if normalized_event is None:
            dropped += 1
            continue
        normalized.append(normalized_event)

    if dropped:
        logger.warning("Dropped %d events missing required fields", dropped)
    return normalized


def _drop_past_events(events: Iterable[dict], now: datetime, grace_hours: int) -> List[dict]:
    cutoff = now - timedelta(hours=grace_hours)
    kept: List[dict] = []
    dropped = 0

    for event in events:
        starts_at = event.get("starts_at")
        if not starts_at:
            kept.append(event)
            continue

        try:
            dt = datetime.fromisoformat(starts_at)
        except ValueError:
            logger.debug("Invalid starts_at format after normalization: %s", starts_at)
            kept.append(event)
            continue

        if dt < cutoff:
            dropped += 1
            continue

        kept.append(event)

    if dropped:
        logger.info("Removed %d past events (cutoff %s)", dropped, cutoff.isoformat())

    return kept


def _summarize(events: Iterable[dict]) -> Counter:
    counts: Counter[str] = Counter()
    for event in events:
        for source in event.get("sources") or [event.get("source")]:
            if source:
                counts[source] += 1
    return counts


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    configure_logging(args.log_level.upper())

    out_path = Path(args.out)
    now = datetime.now(TZ)
    if args.now:
        try:
            parsed = datetime.fromisoformat(args.now)
        except ValueError as exc:
            logger.error("Invalid --now value %s", args.now)
            raise SystemExit(2) from exc
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=TZ)
        now = parsed.astimezone(TZ)

    collected: List[dict] = []
    for name, fetch in _sources():
        collected.extend(_run_source(name, fetch))

    logger.info("Collected %d raw events", len(collected))

    normalized = _normalize_events(collected)
    valid, invalid = validate_events(normalized)

    for payload, errors in invalid:
        logger.warning("Dropping invalid event '%s': %s", payload.get("title"), "; ".join(errors))

    events = _sort(_dedupe(valid))
    events, merges = _merge_related(events)
    events = _drop_past_events(events, now, args.grace_hours)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(events, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    counts = _summarize(events)
    for source, total in counts.most_common():
        logger.info("%s → %d events", source, total)

    logger.info("Merged related events: %d", merges)
    logger.info("Wrote %d events → %s", len(events), out_path)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

