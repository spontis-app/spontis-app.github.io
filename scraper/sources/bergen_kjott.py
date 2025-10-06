"""Scraper for Bergen Kjøtt (https://www.bergenkjott.org/kalendar)."""

from __future__ import annotations

from datetime import datetime
from typing import Optional, Tuple
from urllib.parse import urljoin

import dateparser
import requests
from bs4 import BeautifulSoup, Tag

from scraper.normalize import build_event, to_weekday_label

PROGRAM_URL = "https://www.bergenkjott.org/kalendar"
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


def _fetch_page(url: str) -> Tuple[Optional[BeautifulSoup], Optional[int]]:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT, allow_redirects=True)
    except Exception:
        return None, None

    status = resp.status_code
    soup = BeautifulSoup(resp.text, "html.parser") if resp.text else None
    return soup, status


def _detail_datetime(url: str, soup: Optional[BeautifulSoup] = None) -> Optional[datetime]:
    if soup is None:
        soup, status = _fetch_page(url)
        if status and status >= 400:
            return None
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


def fetch() -> list[dict]:
    soup, _ = _fetch_page(PROGRAM_URL)
    if not soup:
        return []

    events: list[dict] = []
    seen: set[Tuple[str, str]] = set()

    for link in soup.select("a[href]"):
        href = link.get("href")
        if not href:
            continue
        absolute_url = urljoin(PROGRAM_URL, href)
        if not absolute_url.startswith("https://www.bergenkjott.org"):
            continue

        title = link.get_text(" ", strip=True)
        if not title:
            continue

        key = (title, absolute_url)
        if key in seen:
            continue
        seen.add(key)

        detail_soup, url_status = _fetch_page(absolute_url)

        starts_at = _extract_datetime(link)
        if not starts_at:
            starts_at = _detail_datetime(absolute_url, detail_soup)

        extra = {"where": "Bergen Kjøtt"}
        label = to_weekday_label(starts_at)
        if label:
            extra["when"] = label

        if url_status is not None:
            extra["url_status"] = url_status
        ticket_url: Optional[str] = None
        if url_status and url_status >= 400:
            # Look for TicketCo alternatives near the listing or within the detail page
            neighbours = []
            parent = link.parent if isinstance(link.parent, Tag) else None
            if parent:
                neighbours.extend(parent.select("a[href]"))
            if detail_soup:
                neighbours.extend(detail_soup.select("a[href]"))

            for candidate in neighbours:
                href = candidate.get("href")
                if not href or "ticketco" not in href.lower():
                    continue
                ticket_url = urljoin(absolute_url, href)
                break

        if ticket_url:
            extra["ticket_url"] = ticket_url
            final_url = ticket_url
        elif url_status and url_status >= 400:
            final_url = PROGRAM_URL
        else:
            final_url = absolute_url

        if url_status and url_status >= 400:
            extra["url_original"] = absolute_url

        events.append(
            build_event(
                source="Bergen Kjøtt",
                title=title,
                url=final_url,
                starts_at=starts_at,
                venue="Bergen Kjøtt",
                tags=["culture"],
                extra=extra,
            )
        )

    return events
