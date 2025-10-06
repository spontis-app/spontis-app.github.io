"""Scraper for Østre via Ekko.no (https://www.ekko.no/ostre)."""

from __future__ import annotations

from datetime import datetime
from typing import Optional, Tuple
from urllib.parse import urljoin

import dateparser
from bs4 import BeautifulSoup, Tag

from scraper.normalize import TZ, build_event, to_weekday_label
from scraper.http import get as http_get

PROGRAM_URL = "https://www.ekko.no/ostre"
HEADERS = {
    "User-Agent": "SpontisBot/0.2 (+https://spontis-app.github.io)",
    "Accept-Language": "nb,en;q=0.8",
}
PARSE_SETTINGS = {
    "TIMEZONE": "Europe/Oslo",
    "DATE_ORDER": "DMY",
    "PREFER_DATES_FROM": "future",
    "RETURN_AS_TIMEZONE_AWARE": False,
}


def _looks_like_event(href: str) -> bool:
    if any(fragment in href for fragment in ("/program/", "/arrangement", "/events/", "/konsert")):
        return True
    base = "https://www.ekko.no/"
    if href.startswith(base):
        return href.rstrip("/") != PROGRAM_URL.rstrip("/")
    return False


def _parse_datetime(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    return dateparser.parse(value, languages=["nb", "en"], settings=PARSE_SETTINGS)


def _extract_datetime(node: Tag) -> Optional[datetime]:
    """Try to locate a datetime for the card by walking ancestors."""
    for ancestor in [node] + list(node.parents)[:3]:
        if ancestor is None or not isinstance(ancestor, Tag):
            continue

        for time_tag in ancestor.find_all("time"):
            dt = _parse_datetime(time_tag.get("datetime") or time_tag.get("data-start"))
            if dt:
                return dt
            dt = _parse_datetime(time_tag.get_text(" ", strip=True))
            if dt:
                return dt

        text = " ".join(ancestor.stripped_strings)
        dt = _parse_datetime(text)
        if dt:
            return dt
    return None


def fetch() -> list[dict]:
    response = http_get(PROGRAM_URL, headers=HEADERS)
    soup = BeautifulSoup(response.text, "html.parser")

    events: list[dict] = []
    seen: set[Tuple[str, str]] = set()

    for link in soup.select("a[href]"):
        href = link.get("href")
        if not href:
            continue
        absolute_url = urljoin(PROGRAM_URL, href)
        if not _looks_like_event(absolute_url):
            continue

        title = link.get_text(" ", strip=True)
        if not title:
            continue

        key = (title, absolute_url)
        if key in seen:
            continue
        seen.add(key)

        starts_at = _extract_datetime(link)
        extra = {"where": "Østre"}
        label = to_weekday_label(starts_at)
        if label:
            extra["when"] = label

        events.append(
            build_event(
                source="Østre",
                title=title,
                url=absolute_url,
                starts_at=starts_at,
                venue="Østre",
                tags=["culture"],
                extra=extra,
            )
        )

    return events
