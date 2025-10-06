"""Scraper for Bergen Live (https://bergenlive.no/konserter/)."""

from __future__ import annotations

from datetime import datetime
from typing import Optional, Tuple
from urllib.parse import urljoin

import dateparser
import requests
from bs4 import BeautifulSoup, Tag

from scraper.normalize import build_event, to_weekday_label

PROGRAM_URL = "https://bergenlive.no/konserter/"
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
    for candidate in [node] + list(node.parents)[:3]:
        if not isinstance(candidate, Tag):
            continue
        for time_tag in candidate.find_all("time"):
            stamp = time_tag.get("datetime") or time_tag.get("content")
            dt = _parse_datetime(stamp) or _parse_datetime(time_tag.get_text(" ", strip=True))
            if dt:
                return dt
        text = " ".join(candidate.stripped_strings)
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

    for card in soup.select("article, li, div.event"):
        link = card.find("a", href=True)
        if not link:
            continue
        href = link.get("href")
        absolute_url = urljoin(PROGRAM_URL, href)
        if not absolute_url.startswith("https://bergenlive.no"):
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

        extra = {"where": "Bergen Live"}
        label = to_weekday_label(starts_at)
        if label:
            extra["when"] = label

        venue = None
        description = None
        if detail:
            for paragraph in detail.select(".event-meta, .event-info, .entry-content p"):
                text = paragraph.get_text(" ", strip=True)
                if not text:
                    continue
                if venue is None and any(keyword in text.lower() for keyword in ("bergenhus", "plenen", "koengen", "usf", "grieghallen", "forum")):
                    venue = text
                if description is None:
                    description = text
                if venue and description:
                    break

        payload_extra = dict(extra)
        if description:
            payload_extra["description"] = description
        if venue:
            payload_extra["where"] = venue

        tags = ["live"]
        teaser = card.get_text(" ", strip=True).lower()
        if any(keyword in teaser for keyword in ("festival", "fest", "koengen")):
            tags.append("festival")

        events.append(
            build_event(
                source="Bergen Live",
                title=title,
                url=absolute_url,
                starts_at=starts_at,
                venue=venue or "Bergen Live",
                tags=tags,
                extra=payload_extra,
            )
        )

    return events
