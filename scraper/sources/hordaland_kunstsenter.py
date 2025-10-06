"""Scraper for Hordaland Kunstsenter (https://kunstsenter.no)."""

from __future__ import annotations

from datetime import datetime
from typing import Iterable, Optional, Tuple
from urllib.parse import urljoin

import dateparser
import requests
from bs4 import BeautifulSoup, Tag

from scraper.normalize import build_event, to_weekday_label

BASE_URL = "https://kunstsenter.no"
CANDIDATE_PATHS: Iterable[str] = (
    "/program",
    "/utstillinger",
    "/arrangement",
    "/events",
    "/whatson",
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
TIMEOUT = 25


def _parse_datetime(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    return dateparser.parse(value, languages=["nb", "en"], settings=SETTINGS)


def _discover_program_page() -> Optional[Tuple[str, BeautifulSoup]]:
    for path in CANDIDATE_PATHS:
        url = urljoin(BASE_URL, path)
        try:
            response = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
            response.raise_for_status()
        except Exception:
            continue
        soup = BeautifulSoup(response.text, "html.parser")
        if soup.find("a", href=True):
            return url, soup
    try:
        response = requests.get(BASE_URL, headers=HEADERS, timeout=TIMEOUT)
        response.raise_for_status()
    except Exception:
        return None
    return BASE_URL, BeautifulSoup(response.text, "html.parser")


def _extract_datetime(node: Tag) -> Optional[datetime]:
    lineage = [node] + list(node.parents)[:4]
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
    discovered = _discover_program_page()
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

        venue = "Hordaland Kunstsenter"
        description = None
        if detail:
            for paragraph in detail.select(".event-description p, .content p, .rich-text p"):
                description = paragraph.get_text(" ", strip=True)
                if description:
                    break
            for meta in detail.select(".event-meta, .event-details, .meta"):
                text = meta.get_text(" ", strip=True)
                if text and any(word in text.lower() for word in ("kunstnersenter", "kunstcenter", "strandgaten")):
                    venue = text
                    break

        extra = {"where": venue}
        label = to_weekday_label(starts_at)
        if label:
            extra["when"] = label
        if description:
            extra["description"] = description

        events.append(
            build_event(
                source="Hordaland Kunstsenter",
                title=title,
                url=absolute_url,
                starts_at=starts_at,
                venue=venue,
                tags=["culture"],
                extra=extra,
            )
        )

    return events
