"""Scraper for Bergen Kunsthall / Landmark events."""

from __future__ import annotations

from datetime import datetime
from typing import Iterable, Optional, Tuple
from urllib.parse import urljoin
import re

import dateparser
from bs4 import BeautifulSoup, Tag

from scraper.normalize import build_event, to_weekday_label
from scraper.http import get as http_get

EVENT_URLS = [
    "https://www.kunsthall.no/en/events/",
    "https://www.kunsthall.no/en/whats-on/",
]
EVENT_PATH_PATTERN = re.compile(r"/events/\d{4}-")
SKIP_TITLES = (
    'become a member',
    'member',
    'cookie',
    'privacy',
    'about the café',
    'openings',
    'press',
    'newsletter',
    'shop',
    'gift card',
    'visit us',
    'video',
    'editions',
    'publications',
    'guardianship',
    'contact',
    'search',
    'more',
    'no',
    'program',
    'what’s on',
    'events',
    'exhibitions',
)
SKIP_HREF_PARTS = (
    '/cookies',
    '/cookie',
    '/privacy',
    '/press',
    '/shop',
    '/about',
    '/member',
    '/newsletter',
    '/visit-us',
    '/video',
    '/editions',
    '/publications',
    '/landmark-kafe',
    '/the-festival-exhibition',
    '/whats-on/#',
)
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


def _extract_time_hint(text: str) -> Optional[Tuple[int, int]]:
    if not text:
        return None
    match = re.search(r"\b(\d{1,2})[:.](\d{2})\b", text)
    if not match:
        return None
    hour, minute = int(match.group(1)), int(match.group(2))
    if 0 <= hour < 24 and 0 <= minute < 60:
        return hour, minute
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

            url_path = absolute_url.split('?')[0]
            if not EVENT_PATH_PATTERN.search(url_path):
                continue

            title = link.get_text(" ", strip=True)
            if not title:
                continue

            title_lower = title.strip().lower()
            if any(keyword in title_lower for keyword in SKIP_TITLES):
                continue
            if any(part in absolute_url for part in SKIP_HREF_PARTS):
                continue

            key = (title, absolute_url)
            if key in seen:
                continue
            seen.add(key)

            detail_soup: Optional[BeautifulSoup] = None
            starts_at = _extract_datetime(card)
            if not starts_at:
                detail_soup = _fetch(absolute_url)
                if detail_soup:
                    starts_at = _extract_datetime(detail_soup)
            if not starts_at:
                continue
            text_block = " ".join(card.stripped_strings)
            time_hint = _extract_time_hint(text_block)
            if starts_at and (starts_at.hour == 0 and starts_at.minute == 0):
                if not time_hint:
                    if detail_soup is None:
                        detail_soup = _fetch(absolute_url)
                    if detail_soup:
                        time_hint = _extract_time_hint(detail_soup.get_text(" ", strip=True))
                if time_hint:
                    hour, minute = time_hint
                    starts_at = starts_at.replace(hour=hour, minute=minute)

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
