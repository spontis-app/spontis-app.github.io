"""Scraper for BIT Teatergarasjen (https://bit-teatergarasjen.no/program)."""

from __future__ import annotations

from datetime import datetime
from typing import Optional, Tuple
from urllib.parse import urljoin

import dateparser
import requests
from bs4 import BeautifulSoup, Tag

from scraper.normalize import build_event, to_weekday_label

PROGRAM_URL = "https://bit-teatergarasjen.no/program"
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
        response = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        response.raise_for_status()
    except Exception:
        return None
    return BeautifulSoup(response.text, "html.parser")


def fetch() -> list[dict]:
    soup = _fetch_html(PROGRAM_URL)
    if not soup:
        return []

    events: list[dict] = []
    seen: set[Tuple[str, str]] = set()

    for card in soup.select("article, li, div.event-card"):
        link = card.find("a", href=True)
        if not link:
            continue
        href = link.get("href")
        absolute_url = urljoin(PROGRAM_URL, href)
        if not absolute_url.startswith("https://bit-teatergarasjen.no"):
            continue

        title = link.get_text(" ", strip=True)
        if not title:
            continue

        key = (title, absolute_url)
        if key in seen:
            continue
        seen.add(key)

        detail_soup: Optional[BeautifulSoup] = None
        starts_at = _extract_datetime(card)
        if not starts_at:
            detail_soup = _fetch_html(absolute_url)
            if detail_soup:
                starts_at = _extract_datetime(detail_soup)

        extra = {"where": "BIT Teatergarasjen"}
        label = to_weekday_label(starts_at)
        if label:
            extra["when"] = label

        description = None
        if detail_soup is None:
            detail_soup = _fetch_html(absolute_url)
        if detail_soup:
            for paragraph in detail_soup.select(".program__description p, .entry-content p"):
                description = paragraph.get_text(" ", strip=True)
                if description:
                    break

        events.append(
            build_event(
                source="BIT Teatergarasjen",
                title=title,
                url=absolute_url,
                starts_at=starts_at,
                venue="BIT Teatergarasjen",
                tags=["culture"],
                extra={**extra, "description": description} if description else extra,
            )
        )

    return events
