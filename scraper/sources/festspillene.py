"""Scraper for Festspillene i Bergen (https://www.fib.no/program)."""

from __future__ import annotations

from datetime import datetime
from typing import Optional, Tuple
from urllib.parse import urljoin

import dateparser
import requests
from bs4 import BeautifulSoup, Tag

from scraper.normalize import build_event, to_weekday_label

PROGRAM_URL = "https://www.fib.no/program"
HEADERS = {
    "User-Agent": "SpontisBot/0.3 (+https://spontis-app.github.io)",
    "Accept-Language": "nb,en;q=0.8",
}
SETTINGS = {
    "TIMEZONE": "Europe/Oslo",
    "DATE_ORDER": "DMY",
    "PREFER_DATES_FROM": "future",
    "RETURN_AS_TIMEZONE_AWARE": False,
}
TIMEOUT = 25


def _parse_datetime(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    return dateparser.parse(value, languages=["nb", "en"], settings=SETTINGS)


def _extract_datetime(node: Tag) -> Optional[datetime]:
    lineage = [node] + list(node.parents)[:3]
    for candidate in lineage:
        if not isinstance(candidate, Tag):
            continue
        for time_tag in candidate.find_all("time"):
            stamp = time_tag.get("datetime") or time_tag.get("content")
            dt = _parse_datetime(stamp) or _parse_datetime(time_tag.get_text(" ", strip=True))
            if dt:
                return dt
        text = " ".join(candidate.get_text(" ", strip=True).split())
        dt = _parse_datetime(text)
        if dt:
            return dt
    return None


def _fetch_html(url: str) -> Optional[BeautifulSoup]:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        resp.raise_for_status()
    except Exception:
        return None
    return BeautifulSoup(resp.text, "html.parser")


def fetch() -> list[dict]:
    soup = _fetch_html(PROGRAM_URL)
    if not soup:
        return []

    events: list[dict] = []
    seen: set[Tuple[str, str]] = set()

    for card in soup.select("article, li, div.program-item"):
        link = card.find("a", href=True)
        if not link:
            continue
        href = link.get("href")
        absolute_url = urljoin(PROGRAM_URL, href)
        if not absolute_url.startswith("https://www.fib.no"):
            continue
        if "/program/" not in absolute_url:
            continue

        title = link.get_text(" ", strip=True)
        if not title:
            continue

        key = (title, absolute_url)
        if key in seen:
            continue
        seen.add(key)

        detail = _fetch_html(absolute_url)
        starts_at = _extract_datetime(card)
        if not starts_at and detail:
            starts_at = _extract_datetime(detail)

        if not starts_at:
            # Ignore navigation pages and static info without a scheduled event.
            continue

        venue = None
        description = None
        if detail:
            for meta in detail.select(".event-meta, .event-info, .event-location"):
                text = meta.get_text(" ", strip=True)
                if text and venue is None:
                    venue = text
            for paragraph in detail.select(".event-description p, .content p"):
                text = paragraph.get_text(" ", strip=True)
                if text:
                    description = text
                    break

        tags = ["festival", "culture"]

        extra = {}
        if venue:
            extra["where"] = venue
        if description:
            extra["description"] = description
        label = to_weekday_label(starts_at)
        if label:
            extra["when"] = label

        events.append(
            build_event(
                source="Festspillene i Bergen",
                title=title,
                url=absolute_url,
                starts_at=starts_at,
                venue=venue or "Festspillene i Bergen",
                tags=tags,
                extra=extra,
            )
        )

    return events
