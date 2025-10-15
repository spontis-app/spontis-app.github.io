"""TicketCo scraper for Det Akademiske Kvarter."""

from __future__ import annotations

from scraper.sources.ticketco import fetch_events

SLUGS = [
    "det-akademiske-kvarter",
    "det-akademiske-kvarteret",
    "kvarteret",
]
DEFAULT_TAGS = ("student", "bar", "quiz")


def fetch() -> list[dict]:
    return fetch_events(
        SLUGS,
        source_name="Det Akademiske Kvarter",
        default_venue="Det Akademiske Kvarter",
        default_tags=DEFAULT_TAGS,
    )
