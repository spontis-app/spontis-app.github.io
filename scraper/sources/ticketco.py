"""Utility helpers for TicketCo-based organisers."""

from __future__ import annotations

import logging
from collections.abc import Iterable
from datetime import datetime
from typing import Iterable as TypingIterable
from typing import Optional, Sequence
from urllib.parse import urljoin

import requests
from dateutil import parser as dateparser

from scraper.normalize import build_event

LOGGER = logging.getLogger("spontis.scraper.ticketco")

API_TEMPLATE = "https://ticketco.events/api/public/events/?organizer_slug={slug}&timespan=future"
DEFAULT_TIMEOUT = 25
HEADERS = {
    "User-Agent": "SpontisBot/0.3 (+https://spontis-app.github.io)",
    "Accept": "application/json",
}


def _extract_events(payload) -> list[dict]:
    if not payload:
        return []

    if isinstance(payload, list):
        return [event for event in payload if isinstance(event, dict)]

    if isinstance(payload, dict):
        for key in ("events", "data", "results", "items"):
            value = payload.get(key)
            if not value:
                continue
            if isinstance(value, dict):
                # Some APIs nest events under another key.
                nested = value.get("events") or value.get("items")
                if nested and isinstance(nested, list):
                    return [event for event in nested if isinstance(event, dict)]
            if isinstance(value, list):
                return [event for event in value if isinstance(event, dict)]

    return []


def _parse_datetime(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        dt = dateparser.isoparse(value)
        if not dt.tzinfo:
            dt = dt.replace(tzinfo=dateparser.tz.gettz("Europe/Oslo"))
        return dt
    except (ValueError, TypeError):
        return None


def _normalise_url(event: dict, base: str) -> Optional[str]:
    urls = event.get("urls") or {}
    for key in ("web", "url", "main"):
        candidate = urls.get(key) if isinstance(urls, dict) else None
        if candidate:
            return candidate

    direct = event.get("url") or event.get("link")
    if direct:
        return urljoin(base, direct)
    if isinstance(urls, str):
        return urljoin(base, urls)
    return None


def _collect_tags(event: dict, default_tags: Sequence[str]) -> list[str]:
    tags = list(default_tags)
    categories = event.get("category_list") or event.get("categories") or []
    if isinstance(categories, dict):
        categories = categories.values()
    for entry in categories:
        if isinstance(entry, dict):
            name = entry.get("name")
        else:
            name = str(entry)
        if not name:
            continue
        token = name.strip().lower()
        if not token:
            continue
        if token not in tags:
            tags.append(token)
    return tags


def fetch_events(
    slugs: TypingIterable[str],
    *,
    source_name: str,
    default_venue: Optional[str] = None,
    default_tags: Optional[Sequence[str]] = None,
    timeout: int = DEFAULT_TIMEOUT,
) -> list[dict]:
    """Fetch events for one or more TicketCo organisers."""

    results: list[dict] = []
    seen_urls: set[str] = set()
    default_tags = tuple(default_tags or ())

    for slug in slugs:
        slug = slug.strip()
        if not slug:
            continue

        url = API_TEMPLATE.format(slug=slug)
        try:
            response = requests.get(url, headers=HEADERS, timeout=timeout)
            response.raise_for_status()
        except Exception as exc:
            LOGGER.warning("TicketCo fetch failed for %s (%s): %s", source_name, slug, exc)
            continue

        payload = response.json()
        events = _extract_events(payload)
        if not events:
            LOGGER.info("TicketCo returned no events for %s (%s)", source_name, slug)
            continue

        base_url = f"https://{slug}.ticketco.events/"

        for raw_event in events:
            title = (raw_event.get("name") or raw_event.get("title") or "").strip()
            if not title:
                continue

            event_url = _normalise_url(raw_event, base_url)
            if event_url:
                if event_url in seen_urls:
                    continue
                seen_urls.add(event_url)

            starts_at = _parse_datetime(
                raw_event.get("start_at")
                or raw_event.get("start_time")
                or raw_event.get("start")
            )
            ends_at = _parse_datetime(
                raw_event.get("end_at")
                or raw_event.get("end_time")
                or raw_event.get("end")
            )

            venue = (
                raw_event.get("venue")
                or raw_event.get("venue_name")
                or raw_event.get("location")
                or default_venue
            )
            if isinstance(venue, dict):
                venue = venue.get("name") or venue.get("title")
            if venue:
                venue = str(venue).strip()

            description = (raw_event.get("description") or raw_event.get("summary") or "").strip()
            price = None
            if raw_event.get("min_price"):
                price = f"Fra {raw_event['min_price']} kr"

            tags = _collect_tags(raw_event, default_tags)

            extra = {}
            if description:
                extra["description"] = description
            if raw_event.get("image"):
                if isinstance(raw_event["image"], dict):
                    image_url = raw_event["image"].get("url") or raw_event["image"].get("main")
                    if image_url:
                        extra["image"] = image_url
                elif isinstance(raw_event["image"], str):
                    extra["image"] = raw_event["image"]
            if price:
                extra["price"] = price
            if venue and not extra.get("where"):
                extra["where"] = venue

            results.append(
                build_event(
                    source=source_name,
                    title=title,
                    url=event_url or "",
                    starts_at=starts_at,
                    ends_at=ends_at,
                    venue=venue or default_venue,
                    tags=tags,
                    extra=extra or None,
                )
            )

    return results
