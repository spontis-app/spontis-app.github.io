"""SPONTIS scraper entry point with validation and view generation."""
from __future__ import annotations

import argparse
from collections import Counter
import json
import logging
import os
import re
from datetime import datetime, timedelta
from difflib import SequenceMatcher
from pathlib import Path
from typing import Callable, Iterable, List, Optional, Tuple

from scraper.normalize import DEFAULT_CITY, TZ as NORMALIZE_TZ
from scraper.schema import (
    BOOLEAN_FIELDS,
    IDENTIFIER_FIELDS,
    INTEGER_FIELDS,
    REQUIRED_FIELDS,
    SOURCE_LINK_KEYS,
    STRING_FIELDS,
)
from scraper.source_registry import SOURCE_CONFIGS

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "events.json"
SAMPLE_PATH = ROOT / "data" / "events.sample.json"
TZ = NORMALIZE_TZ
OFFLINE_MODE = os.getenv("SPONTIS_OFFLINE", "0") == "1"
DEFAULT_RETENTION_HOURS = int(os.getenv("SPONTIS_EVENT_RETENTION_HOURS", "6"))

LOG_LEVEL = os.getenv("SPONTIS_LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s - %(message)s",
)
LOGGER = logging.getLogger("spontis.scraper")


Source = Tuple[str, Callable[[], Iterable[dict]]]

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


def _sources() -> List[Source]:
    sources: List[Source] = []
    for config in SOURCE_CONFIGS:
        if not config.is_enabled(os.environ):
            continue
        try:
            fetcher = config.resolve()
        except Exception as exc:  # noqa: BLE001 - we want to keep scraper running
            LOGGER.warning("Skipping %s: %s", config.name, exc)
            continue
        sources.append((config.name, fetcher))
    return sources


def _load_sample_events() -> List[dict]:
    if not SAMPLE_PATH.exists():
        LOGGER.warning("Sample data file %s is missing", SAMPLE_PATH)
        return []

    try:
        data = json.loads(SAMPLE_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        LOGGER.error("Failed to parse sample events: %s", exc)
        return []

    hydrated: List[dict] = []
    for raw in data:
        if not isinstance(raw, dict):
            continue
        sample = dict(raw)
        sample.setdefault("source", "Sample")
        sample.setdefault("city", DEFAULT_CITY)
        sample.setdefault("url", sample.get("url") or "https://spontis-app.github.io/")
        hydrated.append(sample)
    return hydrated


def _run_source(name: str, fetch: Callable[[], Iterable[dict]]) -> List[dict]:
    LOGGER.info("Fetching %s", name)
    try:
        events = list(fetch())
        LOGGER.info("%s: %d events", name, len(events))
        return events
    except Exception:
        LOGGER.exception("%s failed", name)
        return []


def _append_unique(values: List[str], new_value: Optional[str]) -> None:
    if not new_value:
        return
    if new_value not in values:
        values.append(new_value)


def _normalize_tags(tags: Iterable[str]) -> List[str]:
    cleaned = sorted({tag.strip() for tag in tags if tag and str(tag).strip()})
    return cleaned


def _coerce_datetime(value: object, field: str, index: int) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, str):
        try:
            dt = datetime.fromisoformat(value)
        except ValueError:
            LOGGER.warning("Event %s has invalid %s: %r", index, field, value)
            return None
    else:
        LOGGER.warning("Event %s has unsupported %s type: %r", index, field, type(value))
        return None

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=TZ)
    return dt.astimezone(TZ)


def _clean_string(value: object) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        value = str(value)
    if isinstance(value, bool):
        value = "true" if value else "false"
    if not isinstance(value, str):
        return None
    cleaned = value.strip()
    return cleaned or None


def _coerce_int(value: object) -> Optional[int]:
    if value is None:
        return None
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, str) and value.strip():
        try:
            return int(float(value))
        except ValueError:
            return None
    return None


def _coerce_bool(value: object) -> Optional[bool]:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "yes", "1"}:
            return True
        if lowered in {"false", "no", "0"}:
            return False
    return None


def _sanitize_source_links(event: dict, target: dict) -> None:
    for key in SOURCE_LINK_KEYS:
        links = event.get(key)
        if not isinstance(links, Iterable):
            continue
        cleaned_links = []
        for entry in links:
            if not isinstance(entry, dict):
                continue
            url = _clean_string(entry.get("url"))
            if not url:
                continue
            label = _clean_string(entry.get("source") or entry.get("label"))
            payload = {"url": url}
            if label:
                payload["source"] = label
            cleaned_links.append(payload)
        if cleaned_links:
            target["sourceLinks"] = cleaned_links
            break


def _sanitize_event(raw: dict, index: int) -> Optional[dict]:
    if not isinstance(raw, dict):
        LOGGER.warning("Event %s is not a mapping: %r", index, type(raw))
        return None

    event = dict(raw)
    cleaned: dict = {}

    for field in REQUIRED_FIELDS:
        value = _clean_string(event.get(field))
        if not value:
            LOGGER.warning("Event %s missing required field %s", index, field)
            return None
        cleaned[field] = value

    city = _clean_string(event.get("city")) or DEFAULT_CITY
    cleaned["city"] = city

    for field in STRING_FIELDS:
        value = _clean_string(event.get(field))
        if value:
            cleaned[field] = value

    for field in IDENTIFIER_FIELDS:
        value = _clean_string(event.get(field))
        if value:
            cleaned[field] = value

    for field in INTEGER_FIELDS:
        value = _coerce_int(event.get(field))
        if value is not None:
            cleaned[field] = value

    for field in BOOLEAN_FIELDS:
        value = _coerce_bool(event.get(field))
        if value is not None:
            cleaned[field] = value

    tags = event.get("tags")
    if isinstance(tags, Iterable) and not isinstance(tags, (str, bytes)):
        cleaned_tags = _normalize_tags(str(tag) for tag in tags)
        if cleaned_tags:
            cleaned["tags"] = cleaned_tags

    sources: List[str] = []
    raw_sources = event.get("sources")
    if isinstance(raw_sources, Iterable) and not isinstance(raw_sources, (str, bytes)):
        for label in raw_sources:
            cleaned_label = _clean_string(label)
            if cleaned_label:
                _append_unique(sources, cleaned_label)

    _append_unique(sources, cleaned.get("source"))
    if sources:
        cleaned["sources"] = sources

    _sanitize_source_links(event, cleaned)

    for field in ("starts_at", "ends_at"):
        dt = _coerce_datetime(event.get(field), field, index)
        if dt:
            cleaned[field] = dt.replace(microsecond=0).isoformat()

    # Remove empty entries explicitly set to falsy values
    for key in list(cleaned.keys()):
        value = cleaned[key]
        if value in ("", [], {}, None):
            cleaned.pop(key)

    return cleaned


def _dedupe_key(event: dict) -> Optional[tuple]:
    title = (event.get("title") or "").strip().lower()
    venue = (event.get("venue") or event.get("where") or "").strip().lower()
    starts_at = event.get("starts_at")
    when = event.get("when")
    url_hash = event.get("urlHash") or event.get("url_hash")
    url = event.get("url")

    if not starts_at and not when and not url_hash and not url:
        return None

    date_key: Optional[str] = None
    if starts_at:
        start_str = str(starts_at).strip()
        if start_str:
            date_key = start_str[:10]

    if date_key:
        return ("starts", title, date_key, venue, url_hash or url)

    normalized_when = (when or "").strip().lower() or None
    if normalized_when:
        if url_hash or url:
            return ("when", title, normalized_when, venue, url_hash or url)
        return ("when", title, normalized_when, venue)

    if url_hash or url:
        return ("url", title, venue, url_hash or url)

    return None


def _dedupe(events: Iterable[dict]) -> List[dict]:
    seen: set = set()
    deduped: List[dict] = []
    merged = 0
    skipped = 0

    for event in events:
        key = _dedupe_key(event)
        if key is None:
            skipped += 1
            deduped.append(event)
            continue

        if key in seen:
            merged += 1
            continue

        seen.add(key)
        deduped.append(event)

    LOGGER.info(
        "Deduped events: merged %d, kept %d, skipped-key %d",
        merged,
        len(deduped),
        skipped,
    )
    return deduped


def _sort(events: List[dict]) -> List[dict]:
    def sort_key(ev: dict):
        starts_at = ev.get("starts_at")
        title = (ev.get("title") or "").strip().lower()
        url_hash = ev.get("urlHash") or ev.get("url_hash") or ev.get("url") or ""
        when = (ev.get("when") or "").strip().lower()

        if starts_at:
            return (0, starts_at, title, url_hash)

        return (1, when, title, url_hash)

    return sorted(events, key=sort_key)


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

    if incoming.get("sourceLinks"):
        existing_links = existing.setdefault("sourceLinks", [])
        for link in incoming["sourceLinks"]:
            if link not in existing_links:
                existing_links.append(link)


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
            sources = []
            _append_unique(sources, new_event.get("source"))
            new_event["sources"] = sources
            merged.append(new_event)

    for event in merged:
        if event.get("tags"):
            event["tags"] = _normalize_tags(event["tags"])

    return merged, merges


def _parse_now(value: Optional[str]) -> datetime:
    if not value:
        return datetime.now(TZ)
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise SystemExit(f"Invalid --now value: {value}") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=TZ)
    return parsed.astimezone(TZ)


def _filter_stale(events: List[dict], now: datetime, retention_hours: int) -> List[dict]:
    if retention_hours <= 0:
        return events

    threshold = now - timedelta(hours=retention_hours)
    kept: List[dict] = []
    dropped = 0

    for event in events:
        start_dt = None
        end_dt = None
        if event.get("starts_at"):
            try:
                start_dt = datetime.fromisoformat(event["starts_at"])
            except ValueError:
                start_dt = None
        if event.get("ends_at"):
            try:
                end_dt = datetime.fromisoformat(event["ends_at"])
            except ValueError:
                end_dt = None

        remove = False
        if end_dt and end_dt < threshold:
            remove = True
        elif start_dt and start_dt < threshold:
            remove = True

        if remove:
            dropped += 1
            continue
        kept.append(event)

    if dropped:
        LOGGER.info("Filtered %d stale events older than %dh", dropped, retention_hours)
    return kept


def _refresh_views(events: List[dict], output_path: Path, now: datetime) -> None:
    try:
        from scripts import build_views
    except ImportError as exc:
        LOGGER.warning("Unable to import view builder: %s", exc)
        return

    event_objects = [build_views.Event.from_raw(event) for event in events]
    today = build_views.build_today(event_objects, now)
    tonight = build_views.build_tonight(event_objects, now)
    heatmap = build_views.build_heatmap(event_objects)

    data_dir = output_path.parent
    generated_dir = data_dir / "generated"
    build_views.write_json(generated_dir / "today.json", today)
    build_views.write_json(generated_dir / "tonight.json", tonight)
    build_views.write_json(generated_dir / "heatmap.json", heatmap)
    LOGGER.info("Updated derived views")


def _write_metadata(events: List[dict], output_path: Path, now: datetime) -> None:
    data_dir = output_path.parent
    generated_dir = data_dir / "generated"
    generated_dir.mkdir(parents=True, exist_ok=True)
    sources = sorted({
        str(event.get("source")).strip()
        for event in events
        if event.get("source")
    })
    payload = {
        "last_updated": now.replace(microsecond=0).isoformat(),
        "total_events": len(events),
        "source_count": len(sources),
    }
    if sources:
        payload["sources"] = sources

    if events:
        counts = Counter()
        for event in events:
            source = str(event.get("source") or "").strip()
            if not source:
                continue
            counts[source] += 1

        if counts:
            total = len(events)
            distribution = []
            for name, count in counts.most_common():
                entry = {
                    "name": name,
                    "events": count,
                }
                if total:
                    entry["share"] = round(count / total, 4)
                distribution.append(entry)

            if distribution:
                payload["source_distribution"] = distribution
                payload["top_source"] = distribution[0]["name"]
                payload["top_source_share"] = distribution[0].get("share")
                top_share = distribution[0].get("share") or 0.0
                payload["diversity_index"] = round(max(0.0, 1.0 - top_share), 4)

    meta_path = generated_dir / "meta.json"
    meta_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _collect_events(offline: bool) -> List[dict]:
    if offline:
        LOGGER.info("Offline mode enabled – using sample events only")
        return _load_sample_events()

    collected: List[dict] = []
    for name, fetch in _sources():
        collected.extend(_run_source(name, fetch))

    if not collected:
        LOGGER.warning("No events collected from live sources; falling back to samples")
        collected.extend(_load_sample_events())
    return collected


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Collect and normalise SPONTIS events")
    parser.add_argument("--output", type=Path, default=OUT, help="Destination for events.json")
    parser.add_argument(
        "--retention-hours",
        type=int,
        default=DEFAULT_RETENTION_HOURS,
        help="How many hours past an event start to keep it in the feed",
    )
    parser.add_argument(
        "--offline",
        action="store_true",
        default=OFFLINE_MODE,
        help="Skip network calls and rely on sample data",
    )
    parser.add_argument(
        "--no-update-views",
        dest="update_views",
        action="store_false",
        help="Do not rebuild today/tonight/heatmap files",
    )
    parser.add_argument(
        "--update-views",
        dest="update_views",
        action="store_true",
        help="Force rebuilding of derived view files",
    )
    parser.set_defaults(update_views=os.getenv("SPONTIS_UPDATE_VIEWS", "1") != "0")
    parser.add_argument(
        "--now",
        help="Override the current datetime (ISO8601)",
    )
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> None:
    args = parse_args(argv)
    now = _parse_now(args.now)
    collected = _collect_events(args.offline)
    LOGGER.info("Collected %d raw events", len(collected))

    validated = []
    for idx, raw in enumerate(collected, start=1):
        sanitized = _sanitize_event(raw, idx)
        if sanitized is not None:
            validated.append(sanitized)
    dropped = len(collected) - len(validated)
    if dropped:
        LOGGER.info("Discarded %d invalid events during validation", dropped)

    events = _sort(_dedupe(validated))
    events, merges = _merge_related(events)
    LOGGER.info("Merged related events: %d", merges)

    events = _filter_stale(events, now=now, retention_hours=args.retention_hours)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(events, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    LOGGER.info("Wrote %d events → %s", len(events), output_path)

    _write_metadata(events, output_path, now)

    if args.update_views:
        _refresh_views(events, output_path, now)


if __name__ == "__main__":
    main()
