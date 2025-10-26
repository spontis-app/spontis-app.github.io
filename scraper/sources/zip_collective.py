"""Scraper for Zip Collective (https://zipcollective.com)."""

from __future__ import annotations

from datetime import datetime
from typing import Iterable, Optional, Tuple
from urllib.parse import urljoin

import dateparser
import requests
from bs4 import BeautifulSoup, Tag

from scraper.normalize import build_event, to_weekday_label

BASE_URL = "https://zipcollective.com"
CANDIDATE_PATHS: Iterable[str] = (
    "/program",
    "/events",
    "/calendar",
    "/shows",
)
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
TIMEOUT = 20


def _parse_datetime(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    return dateparser.parse(value, languages=["nb", "en"], settings=SETTINGS)


def _discover_page() -> Optional[Tuple[str, BeautifulSoup]]:
    for path in CANDIDATE_PATHS:
        url = urljoin(BASE_URL, path)
        try:
            resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
            resp.raise_for_status()
        except Exception:
            continue
        soup = BeautifulSoup(resp.text, "html.parser")
        if soup.find("a", href=True):
            return url, soup
    return None


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


def _fetch_detail(url: str) -> Optional[BeautifulSoup]:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        resp.raise_for_status()
    except Exception:
        return None
    return BeautifulSoup(resp.text, "html.parser")


def fetch() -> list[dict]:
    discovered = _discover_page()
    if not discovered:
        return []
    base_url, soup = discovered

    events: list[dict] = []
    seen: set[Tuple[str, str]] = set()

    for card in soup.select("article, li, div"):
        link = card.find("a", href=True)
        if not link:
            continue
        href = link.get("href")
        absolute_url = urljoin(base_url, href)
        if not absolute_url.startswith(BASE_URL):
            continue

        title = link.get_text(" ", strip=True)
        if not title:
            continue

        key = (title, absolute_url)
        if key in seen:
            continue
        seen.add(key)

        detail = _fetch_detail(absolute_url)
        starts_at = _extract_datetime(card)
        if not starts_at and detail:
            starts_at = _extract_datetime(detail)

        if not starts_at:
            # Skip links that do not expose an event time (navigation, booking forms, etc.)
            continue

        venue = "Zip Collective"
        description = None
        if detail:
            for paragraph in detail.select(".event-description p, .content p, .elementor-widget-container p"):
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
        if any(keyword in teaser for keyword in ("performance", "dance", "workshop", "residency")):
            tags.append("community")

        events.append(
            build_event(
                source="Zip Collective",
                title=title,
                url=absolute_url,
                starts_at=starts_at,
                venue=venue,
                tags=tags,
                extra=extra,
            )
        )

    return events
