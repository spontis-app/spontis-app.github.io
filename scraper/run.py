# scraper/run.py
from __future__ import annotations

import json
import os
import re
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path
from typing import Callable, Iterable, List, Optional, Tuple

from scraper.sources import bergen_kino, ostre

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "events.json"

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


Source = Tuple[str, Callable[[], Iterable[dict]]]


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
        print(f"{name}: {len(events)} events")
        return events
    except Exception as exc:
        print(f"{name} failed: {exc}")
        return []


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

    kept = len(deduped)
    print(f"Deduped events: merged {merged}, kept {kept}, skipped-key {skipped}")
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


def _append_unique(values: List[str], new_value: str) -> None:
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
            sources = []
            _append_unique(sources, new_event.get("source"))
            new_event["sources"] = sources
            merged.append(new_event)

    for event in merged:
        if event.get("tags"):
            event["tags"] = _normalize_tags(event["tags"])

    return merged, merges


def main():
    collected: List[dict] = []
    for name, fetch in _sources():
        collected.extend(_run_source(name, fetch))

    events = _sort(_dedupe(collected))
    events, merges = _merge_related(events)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(events, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Merged related events: {merges}")
    print(f"Wrote {len(events)} events → {OUT}")


if __name__ == "__main__":
    main()
