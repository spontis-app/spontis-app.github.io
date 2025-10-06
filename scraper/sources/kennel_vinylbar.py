"""Best-effort scraper for Kennel Vinylbar (Instagram)."""

from __future__ import annotations

import re
from datetime import datetime
from typing import List, Optional

import dateparser

from scraper.normalize import build_event, to_weekday_label
from scraper.http import get as http_get

PROFILE_URL = "https://www.instagram.com/kennelvinylbar/"
HEADERS = {
    "User-Agent": "SpontisBot/0.2 (+https://spontis-app.github.io)",
    "Accept-Language": "en,nb;q=0.8",
}
SETTINGS = {
    "TIMEZONE": "Europe/Oslo",
    "DATE_ORDER": "DMY",
    "PREFER_DATES_FROM": "future",
    "RETURN_AS_TIMEZONE_AWARE": False,
}
TIMEOUT = 20
DATE_PATTERN = re.compile(r"(\d{1,2}[.\-/]\d{1,2}[.\-/]\d{2,4})")


def _parse_datetime(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    return dateparser.parse(value, languages=["nb", "en"], settings=SETTINGS)


def _fetch_profile_html() -> Optional[str]:
    try:
        resp = http_get(PROFILE_URL, headers=HEADERS, timeout=TIMEOUT)
    except Exception:
        return None
    return resp.text


def _extract_events_from_text(text: str, limit: int = 10) -> List[dict]:
    events: List[dict] = []
    for match in DATE_PATTERN.finditer(text):
        window_start = max(0, match.start() - 160)
        window_end = min(len(text), match.end() + 160)
        snippet = text[window_start:window_end]

        dt = _parse_datetime(match.group(1))
        if not dt:
            continue

        lines = [line.strip() for line in snippet.splitlines() if line.strip()]
        if not lines:
            continue

        # Use first non-date line as title candidate
        title = None
        for line in lines:
            if DATE_PATTERN.search(line):
                continue
            if len(line) < 3:
                continue
            title = line
            break

        if not title:
            title = f"Kennel Vinylbar event {match.group(1)}"

        extra = {"where": "Kennel Vinylbar"}
        label = to_weekday_label(dt)
        if label:
            extra["when"] = label

        events.append(
            build_event(
                source="Kennel Vinylbar",
                title=title,
                url=PROFILE_URL,
                starts_at=dt,
                venue="Kennel Vinylbar",
                tags=["bar"],
                extra=extra,
            )
        )

        if len(events) >= limit:
            break

    return events


def fetch() -> list[dict]:
    html = _fetch_profile_html()
    if not html:
        print("Kennel Vinylbar note: unable to load public profile; skipping")
        return []

    events = _extract_events_from_text(html)
    if not events:
        print("Kennel Vinylbar note: no date patterns found in latest posts")
    return events
