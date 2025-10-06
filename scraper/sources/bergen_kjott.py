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
_URL_ATTRS = (
    "data-item-url",
    "data-url",
    "data-ajax-url",
    "data-ajax-route",
    "data-controller-url",
    "data-lightbox-url",
    "data-record-url",
)
TICKET_KEYWORDS = (
    "ticket",
    "billet",
    "tikkio",
    "ticketco",
    "eventbrite",
    "dice.fm",
    "hoopla",
    "checkin",
    "billetto",
    "facebook.com/events",
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


def _fetch_html(url: str) -> Optional[BeautifulSoup]:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        resp.raise_for_status()
    except Exception:
        return None
    return BeautifulSoup(resp.text, "html.parser")


def _detail_info(url: str) -> tuple[Optional[BeautifulSoup], Optional[datetime]]:
    soup = _fetch_html(url)
    if not soup:
        return None, None

    for selector in ("time", "meta[itemprop='startDate']", "meta[property='event:start_time']"):
        for tag in soup.select(selector):
            stamp = tag.get("datetime") or tag.get("content")
            dt = _parse_datetime(stamp) or _parse_datetime(tag.get_text(" ", strip=True))
            if dt:
                return soup, dt

    text = " ".join(soup.stripped_strings)
    return soup, _parse_datetime(text)


def _normalize_internal_url(url: str) -> Optional[str]:
    if not url:
        return None
    absolute = urljoin(PROGRAM_URL, url)
    if absolute.rstrip("/#") in {"https://www.bergenkjott.org", PROGRAM_URL}:
        return None
    return absolute


def _resolve_link_url(link: Tag) -> Optional[str]:
    candidates = []
    href = link.get("href")
    if href:
        candidates.append(href)

    for attr in _URL_ATTRS:
        value = link.get(attr)
        if value:
            candidates.append(value)

    for candidate in candidates:
        absolute = urljoin(PROGRAM_URL, candidate)
        if absolute.startswith("http"):
            normalized = _normalize_internal_url(absolute)
            if normalized:
                return normalized
            if not absolute.startswith("https://www.bergenkjott.org"):
                return absolute
    return None


def _find_useful_link(original_url: str, soup: Optional[BeautifulSoup]) -> str:
    if not soup:
        return original_url

    for selector in ("link[rel='canonical']", "meta[property='og:url']", "meta[name='twitter:url']"):
        for tag in soup.select(selector):
            candidate = tag.get("href") or tag.get("content")
            normalized = _normalize_internal_url(candidate) if candidate else None
            if normalized and normalized != original_url:
                return normalized

    for anchor in soup.select("a[href]"):
        href = anchor.get("href")
        if not href:
            continue
        text = anchor.get_text(" ", strip=True).lower()
        lowered = href.lower()
        if any(keyword in lowered or keyword in text for keyword in TICKET_KEYWORDS):
            resolved = urljoin(original_url, href)
            if resolved:
                return resolved

    return original_url


def fetch() -> list[dict]:
    soup = _fetch_html(PROGRAM_URL)
    if not soup:
        return []

    events: list[dict] = []
    seen: set[Tuple[str, str]] = set()

    for link in soup.select("a"):
        absolute_url = _resolve_link_url(link)
        if not absolute_url:
            continue

        title = link.get_text(" ", strip=True)
        if not title:
            continue

        key = (title, absolute_url)
        if key in seen:
            continue
        seen.add(key)

        starts_at = _extract_datetime(link)
        detail_soup: Optional[BeautifulSoup] = None
        is_internal = absolute_url.startswith("https://www.bergenkjott.org")
        if is_internal:
            if not starts_at:
                detail_soup, starts_at = _detail_info(absolute_url)
            else:
                detail_soup, _ = _detail_info(absolute_url)
        elif not starts_at:
            # External links won't contain event metadata, so skip if we
            # couldn't read a time from the calendar listing itself.
            continue

        if starts_at is None:
            continue

        final_url = _find_useful_link(absolute_url, detail_soup) if is_internal else absolute_url

        extra = {"where": "Bergen Kjøtt"}
        label = to_weekday_label(starts_at)
        if label:
            extra["when"] = label

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
