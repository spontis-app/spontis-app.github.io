"""TicketCo scraper for Vaskeriet Bar."""

from __future__ import annotations

from scraper.sources.ticketco import fetch_events

SLUGS = [
    "vaskeriet",
    "vaskeriet-bar",
]
DEFAULT_TAGS = ("cocktail", "dj", "bar")


def fetch() -> list[dict]:
    return fetch_events(
        SLUGS,
        source_name="Vaskeriet",
        default_venue="Vaskeriet",
        default_tags=DEFAULT_TAGS,
    )
