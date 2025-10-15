"""TicketCo scraper for Bastant (vinylbar)."""

from __future__ import annotations

from scraper.sources.ticketco import fetch_events

SLUGS = [
    "bastant",
    "bastant-bar",
]
DEFAULT_TAGS = ("vinyl", "bar", "dj")


def fetch() -> list[dict]:
    return fetch_events(
        SLUGS,
        source_name="Bastant",
        default_venue="Bastant Bar",
        default_tags=DEFAULT_TAGS,
    )
