"""TicketCo scraper for Stereo (bar/klubb)."""

from __future__ import annotations

from scraper.sources.ticketco import fetch_events

SLUGS = [
    "stereo",
    "stereo-bardisco",
]
DEFAULT_TAGS = ("club", "dj", "bar")


def fetch() -> list[dict]:
    return fetch_events(
        SLUGS,
        source_name="Stereo",
        default_venue="Stereo",
        default_tags=DEFAULT_TAGS,
    )
