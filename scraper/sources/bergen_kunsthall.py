"""Scraper for Bergen Kunsthall / Landmark events."""

from __future__ import annotations

from datetime import datetime
from typing import Iterable, Optional, Tuple
from urllib.parse import urljoin

import dateparser
from bs4 import BeautifulSoup, Tag

from scraper.normalize import build_event, to_weekday_label
from scraper.http import get as http_get

EVENT_URLS = [
    "https://www.kunsthall.no/en/events/",
    "https://www.kunsthall.no/en/whats-on/",
]
HEADERS = {
    "User-Agent": "SpontisBot/0.2 (+https://spontis-app.github.io)",
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
        if candidate is None or not isinstance(candidate, Tag):
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


def _fetch(url: str) -> Optional[BeautifulSoup]:
    try:
        resp = http_get(url, headers=HEADERS, timeout=TIMEOUT)
    except Exception:
        return None
    return BeautifulSoup(resp.text, "html.parser")


def _detail_datetime(url: str) -> Optional[datetime]:
    soup = _fetch(url)
    if not soup:
        return None

    for selector in ("time", "meta[itemprop='startDate']", "meta[property='event:start_time']"):
        for tag in soup.select(selector):
            stamp = tag.get("datetime") or tag.get("content")
            dt = _parse_datetime(stamp) or _parse_datetime(tag.get_text(" ", strip=True))
            if dt:
                return dt

    text = " ".join(soup.stripped_strings)
    return _parse_datetime(text)


def _iter_cards(soup: BeautifulSoup) -> Iterable[Tag]:
    for selector in ("article", "li", "div"):
        for node in soup.select(selector):
            if node.find("a"):
                yield node


def fetch() -> list[dict]:
    seen: set[Tuple[str, str]] = set()
    events: list[dict] = []

    for url in EVENT_URLS:
        soup = _fetch(url)
        if not soup:
            continue

        for card in _iter_cards(soup):
            link = card.find("a", href=True)
            if not link:
                continue
            href = link.get("href")
            absolute_url = urljoin(url, href)
            if not absolute_url.startswith("https://www.kunsthall.no"):
                continue

            title = link.get_text(" ", strip=True)
            if not title:
                continue

            key = (title, absolute_url)
            if key in seen:
                continue
            seen.add(key)

            starts_at = _extract_datetime(card)
            if not starts_at:
                starts_at = _detail_datetime(absolute_url)

            text_block = " ".join(card.stripped_strings)
            venue = "Landmark" if "Landmark" in text_block else "Bergen Kunsthall"

            extra = {"where": venue}
            label = to_weekday_label(starts_at)
            if label:
                extra["when"] = label

            events.append(
                build_event(
                    source="Bergen Kunsthall",
                    title=title,
                    url=absolute_url,
                    starts_at=starts_at,
                    venue=venue,
                    tags=["culture"],
                    extra=extra,
                )
            )

    return events
