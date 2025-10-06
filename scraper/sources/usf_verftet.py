"""Scraper for USF Verftet (https://usf.no/program/)."""

from __future__ import annotations

from datetime import datetime
from typing import Optional, Tuple
from urllib.parse import urljoin

import dateparser
import requests
from bs4 import BeautifulSoup, Tag

from scraper.normalize import build_event, to_weekday_label

PROGRAM_URL = "https://usf.no/program/"
HEADERS = {
    "User-Agent": "SpontisBot/0.2 (+https://spontis-app.github.io)",
    "Accept-Language": "nb,en;q=0.8",
}
PARSER_SETTINGS = {
    "TIMEZONE": "Europe/Oslo",
    "DATE_ORDER": "DMY",
    "PREFER_DATES_FROM": "future",
    "RETURN_AS_TIMEZONE_AWARE": False,
}
REQUEST_TIMEOUT = 25


def _parse_datetime(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    return dateparser.parse(value, languages=["nb", "en"], settings=PARSER_SETTINGS)


def _extract_datetime(node: Tag) -> Optional[datetime]:
    for candidate in [node] + list(node.parents)[:3]:
        if candidate is None or not isinstance(candidate, Tag):
            continue

        for time_tag in candidate.find_all("time"):
            stamp = time_tag.get("datetime") or time_tag.get("data-start")
            dt = _parse_datetime(stamp) or _parse_datetime(time_tag.get_text(" ", strip=True))
            if dt:
                return dt

        text = " ".join(candidate.stripped_strings)
        dt = _parse_datetime(text)
        if dt:
            return dt
    return None


def _fetch_detail(url: str) -> Optional[BeautifulSoup]:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
    except Exception:
        return None
    return BeautifulSoup(resp.text, "html.parser")


def _detail_datetime(url: str) -> Optional[datetime]:
    soup = _fetch_detail(url)
    if not soup:
        return None

    for selector in ("time", "[data-start]", "meta[itemprop='startDate']", "meta[property='event:start_time']"):
        for tag in soup.select(selector):
            if isinstance(tag, Tag):
                stamp = tag.get("datetime") or tag.get("content") or tag.get("data-start")
                dt = _parse_datetime(stamp) or _parse_datetime(tag.get_text(" ", strip=True))
                if dt:
                    return dt

    text = " ".join(soup.stripped_strings)
    return _parse_datetime(text)


def fetch() -> list[dict]:
    response = requests.get(PROGRAM_URL, headers=HEADERS, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    seen: set[Tuple[str, str]] = set()
    events: list[dict] = []

    for link in soup.select("a[href]"):
        href = link.get("href")
        if not href:
            continue
        absolute_url = urljoin(PROGRAM_URL, href)
        if not absolute_url.startswith("https://usf.no/"):
            continue

        title = link.get_text(" ", strip=True)
        if not title:
            continue

        key = (title, absolute_url)
        if key in seen:
            continue
        seen.add(key)

        starts_at = _extract_datetime(link)
        if not starts_at:
            starts_at = _detail_datetime(absolute_url)

        extra = {"where": "USF Verftet"}
        label = to_weekday_label(starts_at)
        if label:
            extra["when"] = label

        events.append(
            build_event(
                source="USF Verftet",
                title=title,
                url=absolute_url,
                starts_at=starts_at,
                venue="USF Verftet",
                tags=["culture"],
                extra=extra,
            )
        )

    return events
