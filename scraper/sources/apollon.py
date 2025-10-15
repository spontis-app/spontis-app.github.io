"""TicketCo scraper for Apollon Platebar."""

from __future__ import annotations

from scraper.sources.ticketco import fetch_events

SLUGS = [
    "apollon",
    "apollon-platebar",
]
DEFAULT_TAGS = ("vinyl", "bar", "live")


def fetch() -> list[dict]:
    return fetch_events(
        SLUGS,
        source_name="Apollon Platebar",
        default_venue="Apollon Platebar",
        default_tags=DEFAULT_TAGS,
    )
