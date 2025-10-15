"""TicketCo scraper for Hulen."""

from __future__ import annotations

from scraper.sources.ticketco import fetch_events

SLUGS = ["hulen"]
DEFAULT_TAGS = ("live", "club")


def fetch() -> list[dict]:
    return fetch_events(
        SLUGS,
        source_name="Hulen",
        default_venue="Hulen",
        default_tags=DEFAULT_TAGS,
    )
