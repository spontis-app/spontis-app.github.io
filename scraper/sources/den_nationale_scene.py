"""Scraper for Den Nationale Scene (https://www.dns.no/forestillinger)."""

from __future__ import annotations

from datetime import datetime
from typing import Optional, Tuple
from urllib.parse import urljoin
import re

import dateparser
import requests
from bs4 import BeautifulSoup, Tag

from scraper.normalize import build_event, to_weekday_label

PROGRAM_URL = "https://www.dns.no/forestillinger"
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
EVENT_PATH_PATTERN = re.compile(r"/forestillinger/[^/]+/?$")
SKIP_TITLES = (
    'annet',
    'abonnement',
    'administrasjonen',
    'om dns',
    'medlem',
    'gavekort',
    'kontakt',
    'billetter',
    'informasjon',
    'presse',
)


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

    for card in soup.select("article, li, div.theatre-card"):
        link = card.find("a", href=True)
        if not link:
            continue
        href = link.get("href")
        absolute_url = urljoin(PROGRAM_URL, href)
        if not absolute_url.startswith("https://www.dns.no"):
            continue

        url_path = absolute_url.split('?')[0]
        if not EVENT_PATH_PATTERN.search(url_path):
            continue

        title = link.get_text(" ", strip=True)
        if not title:
            continue

        if any(keyword in title.strip().lower() for keyword in SKIP_TITLES):
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
            continue

        venue = "Den Nationale Scene"
        description = None
        if detail:
            for paragraph in detail.select(".performance-description p, .content p"):
                text = paragraph.get_text(" ", strip=True)
                if text:
                    description = text
                    break

        extra = {"where": venue}
        label = to_weekday_label(starts_at)
        if label:
            extra["when"] = label
        if description:
            extra["description"] = description

        tags = ["culture"]
        teaser = card.get_text(" ", strip=True).lower()
        if any(keyword in teaser for keyword in ("premiere", "urpremiere")):
            tags.append("opening")

        events.append(
            build_event(
                source="Den Nationale Scene",
                title=title,
                url=absolute_url,
                starts_at=starts_at,
                venue=venue,
                tags=tags,
                extra=extra,
            )
        )

    return events
